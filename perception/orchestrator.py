"""
Production Perception Orchestrator (perception/orchestrator.py)
Connects transport (DaemonMemoryReader), root singleton resolution (LogicBattleManager),
Gate 8 local-player identity, match hero discovery via m_dicPlayerLogic (+0x0a8),
and SnapshotEngine.
Produces the official public WorldSnapshot consumed by downstream intelligence layers.
Strictly fail-closed: if LogicBattleManager or m_RealSelfPlayer is absent, local_player remains None.
"""

import struct
from typing import List, Optional
from perception.memory_reader import MemoryReader
from perception.models import WorldSnapshot
from perception.schema import FieldRegistry
from perception.snapshot_engine import SnapshotEngine


class ProductionPerceptionOrchestrator:
    """Production coordinator that supplies runtime root addresses to SnapshotEngine."""

    def __init__(
        self,
        reader: MemoryReader,
        engine: Optional[SnapshotEngine] = None,
        registry: Optional[FieldRegistry] = None
    ):
        self.reader = reader
        self.registry = registry or FieldRegistry.load_from_file()
        self.engine = engine or SnapshotEngine(self.reader, self.registry)
        self.cached_battle_manager_addr: int = 0
        self.cached_liblogic_base: int = 0
        self.cached_hero_ptr: int = 0
        self.last_discovery_status: str = "Awaiting discovery"

    def resolve_static_battle_manager(self, liblogic_base: int) -> int:
        """
        Deterministically resolves runtime LogicBattleManager via static RVA 0x10c0774
        (LogicBattleData.get_battleManager) -> ADRP/LDR GOT decoding -> static_fields.
        """
        if liblogic_base < 0x10000000 or liblogic_base >= 0x8000000000:
            return 0

        rva_static = 0x10c0774
        addr_static = liblogic_base + rva_static
        code_raw = self.reader.read_bytes(addr_static, 64)
        if len(code_raw) < 24:
            return 0

        try:
            # Iterate through instructions to decode ADRP + LDR GOT pairs
            num_insns = len(code_raw) // 4
            insns = [struct.unpack_from("<I", code_raw, i * 4)[0] for i in range(num_insns)]

            for i in range(num_insns):
                insn_adrp = insns[i]
                if (insn_adrp & 0x9f000000) != 0x90000000:
                    continue

                rd_adrp = insn_adrp & 0x1f
                immlo = (insn_adrp >> 29) & 0x3
                immhi = (insn_adrp >> 5) & 0x7ffff
                imm = (immhi << 2) | immlo
                if imm & 0x100000:
                    imm -= 0x200000
                pc_adrp = addr_static + (i * 4)
                page_target = (pc_adrp & ~0xfff) + (imm << 12)

                # Look for matching LDR instruction in following 4 instructions
                for j in range(i + 1, min(num_insns, i + 5)):
                    insn_ldr = insns[j]
                    if (insn_ldr & 0xffc00000) != 0xf9400000:
                        continue
                    rn_ldr = (insn_ldr >> 5) & 0x1f
                    if rn_ldr != rd_adrp:
                        continue

                    imm12 = (insn_ldr >> 10) & 0xfff
                    ldr_offset = imm12 * 8
                    got_target = page_target + ldr_offset

                    got_bytes = self.reader.read_bytes(got_target, 8)
                    if len(got_bytes) != 8:
                        continue
                    klass_ptr = struct.unpack("<Q", got_bytes)[0]
                    if klass_ptr < 0x10000000 or klass_ptr >= 0x8000000000:
                        continue

                    # Read static_fields from Il2CppClass
                    klass_raw = self.reader.read_bytes(klass_ptr, 0xc0)
                    if len(klass_raw) < 0xc0:
                        continue
                    p_sf_b0 = struct.unpack_from("<Q", klass_raw, 0xb0)[0]
                    p_sf_b8 = struct.unpack_from("<Q", klass_raw, 0xb8)[0]

                    candidate_sf = [p for p in (p_sf_b0, p_sf_b8) if 0x10000000 <= p < 0x8000000000]
                    for sf in candidate_sf:
                        sf_data = self.reader.read_bytes(sf, 32)
                        if len(sf_data) >= 8:
                            for sf_off in (0x00, 0x08):
                                inst = struct.unpack_from("<Q", sf_data, sf_off)[0]
                                if 0x10000000 <= inst < 0x8000000000:
                                    mgr_raw = self.reader.read_bytes(inst + 0x180, 4)
                                    if len(mgr_raw) == 4:
                                        state = struct.unpack("<i", mgr_raw)[0]
                                        if state in (2, 6):
                                            return inst
        except Exception:
            return 0

        return 0

    def resolve_from_klass(self, klass_addr: int) -> int:
        """Resolves LogicBattleManager from Il2CppClass pointer -> static_fields + 0x00."""
        if klass_addr < 0x10000000 or klass_addr >= 0x8000000000:
            return 0
        try:
            klass_raw = self.reader.read_bytes(klass_addr, 0xc0)
            if len(klass_raw) < 0xc0:
                return 0
            for sf_off in (0xb8, 0xb0):
                sf_ptr = struct.unpack_from("<Q", klass_raw, sf_off)[0]
                if 0x10000000 <= sf_ptr < 0x8000000000:
                    sf_data = self.reader.read_bytes(sf_ptr, 16)
                    if len(sf_data) >= 8:
                        inst = struct.unpack_from("<Q", sf_data, 0)[0]
                        if 0x10000000 <= inst < 0x8000000000:
                            mgr_raw = self.reader.read_bytes(inst + 0x180, 4)
                            if len(mgr_raw) == 4:
                                state = struct.unpack("<i", mgr_raw)[0]
                                if state in (2, 6):
                                    return inst
        except Exception:
            pass
        return 0

    def discover_battle_manager(self) -> int:
        """
        Discovers runtime LogicBattleManager singleton address deterministically.
        Strictly fail-closed: returns 0 if game is not in an active match or if
        structural invariants are not completely proven.
        """
        # 1. Invalidate cache if liblogic_base changed (process restart / ASLR relocation)
        info = self.reader.get_info() if hasattr(self.reader, "get_info") else {}
        liblogic_base = info.get("liblogic_base", 0)
        if isinstance(liblogic_base, str):
            liblogic_base = int(liblogic_base, 16) if liblogic_base.startswith("0x") else int(liblogic_base)

        if liblogic_base != self.cached_liblogic_base:
            self.cached_battle_manager_addr = 0
            self.cached_liblogic_base = liblogic_base

        # 2. Check if cached manager remains valid, in-battle, with valid local player
        if self.cached_battle_manager_addr > 0:
            raw_state = self.reader.read_bytes(self.cached_battle_manager_addr + 0x180, 4)
            if len(raw_state) == 4 and struct.unpack("<i", raw_state)[0] in (2, 6):
                raw_hero = self.reader.read_bytes(self.cached_battle_manager_addr + 0x200, 8)
                if len(raw_hero) == 8:
                    p_self = struct.unpack("<Q", raw_hero)[0]
                    if p_self >= 0x10000000:
                        hero_hdr = self.reader.read_bytes(p_self + 0x5c, 1)
                        if len(hero_hdr) == 1 and hero_hdr[0] != 1:
                            self.cached_battle_manager_addr = 0
                            return 0
                return self.cached_battle_manager_addr
            self.cached_battle_manager_addr = 0

        # 3. Deterministic static resolution via liblogic_base
        if liblogic_base > 0:
            addr = self.resolve_static_battle_manager(liblogic_base)
            if addr > 0:
                raw_state = self.reader.read_bytes(addr + 0x180, 4)
                if len(raw_state) == 4 and struct.unpack("<i", raw_state)[0] in (2, 6):
                    self.cached_battle_manager_addr = addr
                    return addr

        # 3.1 Deterministic IL2CPP static class descriptor resolution (libcsharp / metadata type table)
        candidate_klasses = []
        libcsharp_base = info.get("libcsharp_base", 0)
        if isinstance(libcsharp_base, str):
            libcsharp_base = int(libcsharp_base, 16) if libcsharp_base.startswith("0x") else int(libcsharp_base)

        # Dynamic fallback: resolve libcsharp_base via DUMP_MAPS if not in info
        if libcsharp_base <= 0 and hasattr(self.reader, "_sock") and self.reader._sock:
            try:
                self.reader._sock.sendall(b"DUMP_MAPS\n")
                if hasattr(self.reader, "_file") and self.reader._file:
                    resp_line = self.reader._file.readline()
                    if resp_line:
                        import json
                        mdata = json.loads(resp_line)
                        maps_str = mdata.get("maps", "")
                        for entry in maps_str.split(";"):
                            if "libcsharp.so" in entry:
                                part = entry.strip().split("-")[0]
                                libcsharp_base = int(part, 16)
                                break
            except Exception:
                pass

        if libcsharp_base > 0:
            kbytes = self.reader.read_bytes(libcsharp_base + 0x7680928, 8)
            if len(kbytes) == 8:
                candidate_klasses.append(struct.unpack("<Q", kbytes)[0])
        
        # Static IL2CPP Class Descriptors for LogicBattleManager
        candidate_klasses.extend([0x6dd7e3a9f8, 0x778ccb9b38, 0x7761625518])
        
        for cand_klass in candidate_klasses:
            if cand_klass >= 0x10000000:
                addr = self.resolve_from_klass(cand_klass)
                if addr > 0:
                    raw_state = self.reader.read_bytes(addr + 0x180, 4)
                    if len(raw_state) == 4 and struct.unpack("<i", raw_state)[0] in (2, 6):
                        self.cached_battle_manager_addr = addr
                        return addr

        # 4. Invariant-Verified LogicBattleManager Resolution (Gate 8 Compliant)
        anchor_addr = self.cached_hero_ptr
        if anchor_addr < 0x10000000 and hasattr(self.reader, "scan_hero"):
            try:
                hres = self.reader.scan_hero()
                if isinstance(hres, dict):
                    cand = hres.get("hero_ptr", 0)
                    anchor_addr = int(cand, 16) if isinstance(cand, str) and cand.startswith("0x") else int(cand) if isinstance(cand, int) else 0
            except Exception:
                anchor_addr = 0

        if anchor_addr >= 0x10000000:
            self.cached_hero_ptr = anchor_addr
            # Read in native 4KB chunks (<1ms per chunk) around the match anchor
            chunk_size = 4096
            scan_start = anchor_addr - 0x10000
            scan_end = anchor_addr + 0x10000

            for curr in range(scan_start, scan_end, chunk_size):
                buf = self.reader.read_bytes(curr, chunk_size)
                if not buf or len(buf) < 0x220:
                    continue

                for off in range(0, len(buf) - 0x220, 8):
                    st = struct.unpack_from("<i", buf, off + 0x180)[0]
                    if st in (2, 6):
                        ft = struct.unpack_from("<I", buf, off + 0x19c)[0]
                        if ft > 0:
                            p_self = struct.unpack_from("<Q", buf, off + 0x200)[0]
                            p_dic = struct.unpack_from("<Q", buf, off + 0x0a8)[0]
                            if 0x10000000 <= p_self < 0x8000000000 and 0x10000000 <= p_dic < 0x8000000000 and p_self != p_dic:
                                hero_hdr = self.reader.read_bytes(p_self, 0x60)
                                if len(hero_hdr) >= 0x60 and hero_hdr[0x5c] == 1:
                                    mgr_cand = curr + off
                                    self.cached_battle_manager_addr = mgr_cand
                                    return mgr_cand

        return 0

    def discover_match_entities(self, mgr_addr: int) -> List[int]:
        """
        Extracts all combat entity pointers from LogicBattleManager:
        1. Players Dictionary: m_dicPlayerLogic (+0x0a8)
        2. Base Nexus Crystals: m_CampAMainTower (+0xd0) & m_CampBMainTower (+0xd8)
        3. Camp Combat Lists: m_CampAList (+0x0e0) & m_CampBList (+0x0e8) (Turrets, Minions, Players)
        4. Jungle Creeps / Bosses: m_dicMonsterLogic (+0xb0)
        5. Minion Wave List: m_SoldierList (+0x128)
        6. Active Projectiles: m_BlockBulletList (+0x130)
        """
        if mgr_addr <= 0:
            return []

        entity_addrs = []
        seen = set()

        def add_entity(ptr: int):
            if ptr < 0x10000000 or ptr in seen:
                return
            seen.add(ptr)
            entity_addrs.append(ptr)

        try:
            # Source 1: Players Dictionary m_dicPlayerLogic (+0x0a8)
            raw_dic = self.reader.read_bytes(mgr_addr + 0x0a8, 8)
            if len(raw_dic) == 8:
                dic_ptr = struct.unpack("<Q", raw_dic)[0]
                if dic_ptr >= 0x10000000:
                    raw_header = self.reader.read_bytes(dic_ptr, 0x30)
                    if len(raw_header) >= 0x24:
                        entries_ptr = struct.unpack_from("<Q", raw_header, 0x018)[0]
                        count = struct.unpack_from("<i", raw_header, 0x020)[0]
                        if entries_ptr >= 0x10000000 and 0 < count <= 30:
                            raw_entries = self.reader.read_bytes(entries_ptr, 0x20 + count * 24)
                            if len(raw_entries) >= 0x20 + count * 24:
                                for i in range(count):
                                    off = 0x20 + i * 24
                                    hc, _, _, val_ptr = struct.unpack_from("<iiQQ", raw_entries, off)
                                    if hc >= 0 and val_ptr >= 0x10000000:
                                        add_entity(val_ptr)

            # Source 2: Fountains (+0xc0, +0xc8) & Base Nexus Crystals (+0xd0, +0xd8)
            raw_structures = self.reader.read_bytes(mgr_addr + 0xc0, 32)
            if len(raw_structures) == 32:
                fa, fb, tw_a, tw_b = struct.unpack("<QQQQ", raw_structures)
                if fa >= 0x10000000: add_entity(fa)
                if fb >= 0x10000000: add_entity(fb)
                if tw_a >= 0x10000000: add_entity(tw_a)
                if tw_b >= 0x10000000: add_entity(tw_b)

            # Source 3: Camp Combat Lists m_CampAList (+0xe0) & m_CampBList (+0xe8)
            raw_camps = self.reader.read_bytes(mgr_addr + 0xe0, 16)
            if len(raw_camps) == 16:
                list_a, list_b = struct.unpack("<QQ", raw_camps)
                for clist in (list_a, list_b):
                    if clist >= 0x10000000:
                        raw_chdr = self.reader.read_bytes(clist, 0x20)
                        if len(raw_chdr) >= 0x1c:
                            items_arr = struct.unpack_from("<Q", raw_chdr, 0x10)[0]
                            size = struct.unpack_from("<i", raw_chdr, 0x18)[0]
                            if items_arr >= 0x10000000 and 0 < size <= 64:
                                raw_items = self.reader.read_bytes(items_arr, 0x20 + size * 8)
                                if len(raw_items) >= 0x20 + size * 8:
                                    for idx in range(size):
                                        t_ptr = struct.unpack_from("<Q", raw_items, 0x20 + idx * 8)[0]
                                        if t_ptr >= 0x10000000:
                                            add_entity(t_ptr)

            # Source 4: Jungle Monsters Dictionary m_dicMonsterLogic (+0x0b0)
            raw_m_dic = self.reader.read_bytes(mgr_addr + 0x0b0, 8)
            if len(raw_m_dic) == 8:
                m_dic_ptr = struct.unpack("<Q", raw_m_dic)[0]
                if m_dic_ptr >= 0x10000000:
                    raw_m_hdr = self.reader.read_bytes(m_dic_ptr, 0x30)
                    if len(raw_m_hdr) >= 0x24:
                        m_entries = struct.unpack_from("<Q", raw_m_hdr, 0x018)[0]
                        m_count = struct.unpack_from("<i", raw_m_hdr, 0x020)[0]
                        if m_entries >= 0x10000000 and 0 < m_count <= 500:
                            m_raw = self.reader.read_bytes(m_entries, 0x20 + m_count * 24)
                            if len(m_raw) >= 0x20 + m_count * 24:
                                for i in range(m_count):
                                    off = 0x20 + i * 24
                                    hc, _, _, val_p = struct.unpack_from("<iiQQ", m_raw, off)
                                    if hc >= 0 and val_p >= 0x10000000:
                                        add_entity(val_p)

            # Source 5: Minion Wave List m_SoldierList (+0x128) & Bullet List (+0x130)
            raw_soldiers = self.reader.read_bytes(mgr_addr + 0x128, 16)
            if len(raw_soldiers) >= 8:
                s_list_ptr = struct.unpack_from("<Q", raw_soldiers, 0)[0]
                if s_list_ptr >= 0x10000000:
                    s_hdr = self.reader.read_bytes(s_list_ptr, 0x20)
                    if len(s_hdr) >= 0x1c:
                        s_items_arr = struct.unpack_from("<Q", s_hdr, 0x10)[0]
                        s_size = struct.unpack_from("<i", s_hdr, 0x18)[0]
                        if s_items_arr >= 0x10000000 and 0 < s_size <= 256:
                            s_arr_data = self.reader.read_bytes(s_items_arr, 0x20 + s_size * 8)
                            if len(s_arr_data) >= 0x20 + s_size * 8:
                                for s_idx in range(s_size):
                                    s_ptr = struct.unpack_from("<Q", s_arr_data, 0x20 + s_idx * 8)[0]
                                    add_entity(s_ptr)
                if len(raw_soldiers) >= 16:
                    b_list_ptr = struct.unpack_from("<Q", raw_soldiers, 8)[0]
                    if b_list_ptr >= 0x10000000:
                        b_hdr = self.reader.read_bytes(b_list_ptr, 0x20)
                        if len(b_hdr) >= 0x1c:
                            b_items_arr = struct.unpack_from("<Q", b_hdr, 0x10)[0]
                            b_size = struct.unpack_from("<i", b_hdr, 0x18)[0]
                            if b_items_arr >= 0x10000000 and 0 < b_size <= 256:
                                b_arr_data = self.reader.read_bytes(b_items_arr, 0x20 + b_size * 8)
                                if len(b_arr_data) >= 0x20 + b_size * 8:
                                    for b_idx in range(b_size):
                                        b_ptr = struct.unpack_from("<Q", b_arr_data, 0x20 + b_idx * 8)[0]
                                        add_entity(b_ptr)
        except Exception:
            pass

        return entity_addrs

    def get_world_snapshot(
        self,
        known_entity_addrs: Optional[List[int]] = None,
        confidence_policy: str = "PROVEN"
    ) -> WorldSnapshot:
        """
        Main production entry point.
        Resolves LogicBattleManager, discovers match heroes, enforces Gate 8 local-player binding,
        and captures the full WorldSnapshot.
        Strictly fail-closed: if LogicBattleManager is absent or inactive, local_player evaluates to None.
        """
        mgr_addr = self.discover_battle_manager()

        if mgr_addr > 0:
            self.last_discovery_status = f"BattleManager resolved @ 0x{mgr_addr:x}"
            if known_entity_addrs is None:
                known_entity_addrs = self.discover_match_entities(mgr_addr)

            return self.engine.capture_snapshot(
                known_entity_addrs=known_entity_addrs,
                battle_manager_addr=mgr_addr,
                confidence_policy=confidence_policy
            )

        # Strict Gate 8 Fail-Closed Identity: If BattleManager is missing, local_player is strictly None
        self.last_discovery_status = "Awaiting active match / LogicBattleManager..."
        return self.engine.capture_snapshot(
            known_entity_addrs=known_entity_addrs,
            battle_manager_addr=0,
            local_player_ptr=None,
            confidence_policy=confidence_policy
        )

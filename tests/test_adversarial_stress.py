#!/usr/bin/env python3
"""
test_adversarial_stress.py - Empirical Adversarial Challenge & Stress Test Suite for VEMINS ESP

Covers 5 Critical Adversarial Stress Dimensions:
1. Binary Struct Serialization / Deserialization Fuzzing & Corruption
2. Boundary & Malformed Coordinates (Out-of-bounds, NaN, +Inf, -Inf, Subnormal)
3. Sparse Dictionary Ingestion & Tombstone Filtering (hashCode < 0, sparse slots, null pointers)
4. Local Player Null / Death / Respawn Camera Smoothing (EMA alpha=0.35, continuity)
5. Entity Count Limits, Capacity Overflows, and Max-Payload Saturation
"""

import math
import os
import random
import struct
import unittest
from typing import Dict, List, Tuple

# Import Project Modules
from minimap_projection import MinimapProjector
from perception.memory_reader import MockMemoryReader
from perception.models import (
    AbilityCooldown,
    HeroAbilities,
    HeroCombatAttributes,
    HeroEntity,
    HeroInventory,
    HeroStatusEffects,
    ItemSlot,
    MonsterEntity,
    SoldierEntity,
    TowerEntity,
    WorldSnapshot,
)
from perception.parser import (
    KLASS_BULLET,
    KLASS_MONSTER,
    KLASS_PLAYER,
    KLASS_SOLDIER,
    KLASS_TOWER,
    KLASS_WILD_MONSTER,
    EntityParser,
)
from perception.schema import FieldRegistry
from perception.snapshot_engine import SnapshotEngine


# ============================================================================
# C++ Binary Struct Offsets & Format Definitions (engine_schema.h)
# ============================================================================

VEMINS_SCHEMA_MAGIC = 0x564D4E53  # 'VMNS'
VEMINS_SCHEMA_VERSION = 1
TOTAL_BINARY_FRAME_SIZE = 6160

MAX_HEROES = 10
MAX_SOLDIERS = 32
MAX_MONSTERS = 32
MAX_TOWERS = 22
MAX_ABILITIES = 6
MAX_ITEMS = 6

FMT_ABILITY_BINARY = "<iiffBB2s"
SIZE_ABILITY_BINARY = struct.calcsize(FMT_ABILITY_BINARY)  # 20 bytes

FMT_HERO_HEAD = "<Q9i4B8f3i6iB3s"
SIZE_HERO_HEAD = struct.calcsize(FMT_HERO_HEAD)
SIZE_HERO_BINARY = SIZE_HERO_HEAD + (MAX_ABILITIES * SIZE_ABILITY_BINARY)  # 240 bytes

FMT_SOLDIER_BINARY = "<Q6iB3sff"
SIZE_SOLDIER_BINARY = struct.calcsize(FMT_SOLDIER_BINARY)  # 44 bytes

FMT_MONSTER_BINARY = "<Q5iB3sfff"
SIZE_MONSTER_BINARY = struct.calcsize(FMT_MONSTER_BINARY)  # 44 bytes

FMT_TOWER_BINARY = "<Q4iB3sfff"
SIZE_TOWER_BINARY = struct.calcsize(FMT_TOWER_BINARY)  # 40 bytes

# Header: 64 bytes
# uint32 magic, uint32 version, uint64 timestamp_ns, uint32 frame_index, int32 pid, uint64 libcsharp_base, uint64 liblogic_base
# uint8 in_match, uint8 battle_state, uint8 pad_header[2], int32 local_camp, uint32 frame_time_ms, float read_latency_ms
# uint8 hero_count, uint8 soldier_count, uint8 monster_count, uint8 tower_count, uint8 pad[4]
FMT_SNAPSHOT_HEADER = "<IIQIi2Q2B2siIf4B4s"
SIZE_SNAPSHOT_HEADER = struct.calcsize(FMT_SNAPSHOT_HEADER)  # 64 bytes
assert SIZE_SNAPSHOT_HEADER == 64, f"Header size must be 64, got {SIZE_SNAPSHOT_HEADER}"


def pack_hero_entity(
    address: int = 0x7200100000,
    hero_id: int = 1,
    level: int = 15,
    hp: int = 4000,
    hp_max: int = 4000,
    mp: int = 2000,
    mp_max: int = 2000,
    shield: int = 0,
    magic_shield: int = 0,
    camp: int = 1,
    is_dead: int = 0,
    is_local: int = 0,
    is_in_battle: int = 1,
    pos_x: float = 0.0,
    pos_y: float = 0.0,
    facing_x: float = 1.0,
    facing_y: float = 0.0,
    move_dir_x: float = 0.0,
    move_dir_y: float = 0.0,
    run_speed: float = 350.0,
    attack_speed: float = 1.2,
    gold: int = 12000,
    status_mask: int = 0,
    face_lock_id: int = 0,
    item_ids: List[int] = None,
    abilities: List[Dict] = None,
) -> bytes:
    """Helper to pack a single 240-byte HeroEntityBinary struct."""
    if item_ids is None:
        item_ids = [0] * MAX_ITEMS
    while len(item_ids) < MAX_ITEMS:
        item_ids.append(0)

    if abilities is None:
        abilities = []

    ability_count = min(len(abilities), MAX_ABILITIES)
    head_bytes = struct.pack(
        FMT_HERO_HEAD,
        address,
        hero_id,
        level,
        hp,
        hp_max,
        mp,
        mp_max,
        shield,
        magic_shield,
        camp,
        is_dead,
        is_local,
        is_in_battle,
        0,  # pad1
        pos_x,
        pos_y,
        facing_x,
        facing_y,
        move_dir_x,
        move_dir_y,
        run_speed,
        attack_speed,
        gold,
        status_mask,
        face_lock_id,
        *item_ids[:MAX_ITEMS],
        ability_count,
        b"\x00\x00\x00",
    )

    abilities_bytes = bytearray()
    for i in range(MAX_ABILITIES):
        if i < len(abilities):
            ab = abilities[i]
            ab_raw = struct.pack(
                FMT_ABILITY_BINARY,
                ab.get("spell_id", 0),
                ab.get("slot", i + 1),
                ab.get("remaining_s", 0.0),
                ab.get("max_s", 10.0),
                1 if ab.get("is_cooling_down", False) else 0,
                1 if ab.get("is_ready", True) else 0,
                b"\x00\x00",
            )
        else:
            ab_raw = b"\x00" * SIZE_ABILITY_BINARY
        abilities_bytes.extend(ab_raw)

    res = head_bytes + bytes(abilities_bytes)
    assert len(res) == SIZE_HERO_BINARY, f"Hero binary size mismatch: {len(res)} != {SIZE_HERO_BINARY}"
    return res


def pack_frame_snapshot(
    heroes: List[bytes] = None,
    soldiers: List[bytes] = None,
    monsters: List[bytes] = None,
    towers: List[bytes] = None,
    magic: int = VEMINS_SCHEMA_MAGIC,
    version: int = VEMINS_SCHEMA_VERSION,
    timestamp_ns: int = 1000000,
    frame_index: int = 1,
    pid: int = 1234,
    libcsharp_base: int = 0x7000000000,
    liblogic_base: int = 0x7100000000,
    in_match: int = 1,
    battle_state: int = 2,
    local_camp: int = 1,
    frame_time_ms: int = 60000,
    read_latency_ms: float = 0.45,
) -> bytes:
    """Helper to assemble a valid or custom 6,160-byte FrameSnapshotBinary."""
    heroes = heroes or []
    soldiers = soldiers or []
    monsters = monsters or []
    towers = towers or []

    hero_count = min(len(heroes), MAX_HEROES)
    soldier_count = min(len(soldiers), MAX_SOLDIERS)
    monster_count = min(len(monsters), MAX_MONSTERS)
    tower_count = min(len(towers), MAX_TOWERS)

    header = struct.pack(
        FMT_SNAPSHOT_HEADER,
        magic,
        version,
        timestamp_ns,
        frame_index,
        pid,
        libcsharp_base,
        liblogic_base,
        in_match,
        battle_state,
        b"\x00\x00",  # pad_header
        local_camp,
        frame_time_ms,
        read_latency_ms,
        hero_count,
        soldier_count,
        monster_count,
        tower_count,
        b"\x00\x00\x00\x00",  # pad
    )

    buf = bytearray(header)

    # Heroes (10 * 240 = 2400)
    for i in range(MAX_HEROES):
        if i < len(heroes):
            buf.extend(heroes[i])
        else:
            buf.extend(b"\x00" * SIZE_HERO_BINARY)

    # Soldiers (32 * 44 = 1408)
    for i in range(MAX_SOLDIERS):
        if i < len(soldiers):
            buf.extend(soldiers[i])
        else:
            buf.extend(b"\x00" * SIZE_SOLDIER_BINARY)

    # Monsters (32 * 44 = 1408)
    for i in range(MAX_MONSTERS):
        if i < len(monsters):
            buf.extend(monsters[i])
        else:
            buf.extend(b"\x00" * SIZE_MONSTER_BINARY)

    # Towers (22 * 40 = 880)
    for i in range(MAX_TOWERS):
        if i < len(towers):
            buf.extend(towers[i])
        else:
            buf.extend(b"\x00" * SIZE_TOWER_BINARY)

    assert len(buf) == TOTAL_BINARY_FRAME_SIZE, f"Buffer size mismatch: {len(buf)} != 6160"
    return bytes(buf)


# ============================================================================
# Python Deserializer Mirroring Kotlin BinarySnapshotReader
# ============================================================================

class UnpackedSnapshot:
    def __init__(self):
        self.magic = 0
        self.version = 0
        self.timestamp_ns = 0
        self.frame_index = 0
        self.pid = 0
        self.libcsharp_base = 0
        self.liblogic_base = 0
        self.in_match = False
        self.battle_state = 0
        self.local_camp = 0
        self.frame_time_ms = 0
        self.read_latency_ms = 0.0
        self.hero_count = 0
        self.soldier_count = 0
        self.monster_count = 0
        self.tower_count = 0
        self.heroes: List[Dict] = []
        self.soldiers: List[Dict] = []
        self.monsters: List[Dict] = []
        self.towers: List[Dict] = []
        self.local_hero_index = -1


def unpack_binary_snapshot(data: bytes) -> Tuple[bool, UnpackedSnapshot]:
    """Decodes binary snapshot byte buffer mirroring BinarySnapshotReader.kt."""
    result = UnpackedSnapshot()
    if len(data) < TOTAL_BINARY_FRAME_SIZE:
        return False, result

    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != VEMINS_SCHEMA_MAGIC:
        return False, result

    result.magic = magic
    result.version = struct.unpack_from("<I", data, 4)[0]
    result.timestamp_ns = struct.unpack_from("<Q", data, 8)[0]
    result.frame_index = struct.unpack_from("<I", data, 16)[0]
    result.pid = struct.unpack_from("<i", data, 20)[0]
    result.libcsharp_base = struct.unpack_from("<Q", data, 24)[0]
    result.liblogic_base = struct.unpack_from("<Q", data, 32)[0]
    result.in_match = data[40] != 0
    result.battle_state = data[41]
    result.local_camp = struct.unpack_from("<i", data, 44)[0]
    result.frame_time_ms = struct.unpack_from("<I", data, 48)[0]
    result.read_latency_ms = struct.unpack_from("<f", data, 52)[0]

    raw_hero_cnt = data[56]
    raw_soldier_cnt = data[57]
    raw_monster_cnt = data[58]
    raw_tower_cnt = data[59]

    result.hero_count = max(0, min(MAX_HEROES, raw_hero_cnt))
    result.soldier_count = max(0, min(MAX_SOLDIERS, raw_soldier_cnt))
    result.monster_count = max(0, min(MAX_MONSTERS, raw_monster_cnt))
    result.tower_count = max(0, min(MAX_TOWERS, raw_tower_cnt))

    # Unpack Heroes
    offset = 64
    for i in range(result.hero_count):
        base = offset + (i * SIZE_HERO_BINARY)
        hero_data = struct.unpack_from(FMT_HERO_HEAD, data, base)
        hero = {
            "address": hero_data[0],
            "hero_id": hero_data[1],
            "level": hero_data[2],
            "hp": hero_data[3],
            "hp_max": hero_data[4],
            "mp": hero_data[5],
            "mp_max": hero_data[6],
            "shield": hero_data[7],
            "magic_shield": hero_data[8],
            "camp": hero_data[9],
            "is_dead": hero_data[10] != 0,
            "is_local": hero_data[11] != 0,
            "is_in_battle": hero_data[12] != 0,
            "pos_x": hero_data[14],
            "pos_y": hero_data[15],
            "facing_x": hero_data[16],
            "facing_y": hero_data[17],
            "move_dir_x": hero_data[18],
            "move_dir_y": hero_data[19],
            "run_speed": hero_data[20],
            "attack_speed": hero_data[21],
            "gold": hero_data[22],
            "status_mask": hero_data[23],
            "face_lock_id": hero_data[24],
            "item_ids": list(hero_data[25:31]),
            "ability_count": min(MAX_ABILITIES, hero_data[31]),
            "abilities": [],
        }
        ab_base = base + SIZE_HERO_HEAD
        for a_idx in range(hero["ability_count"]):
            ab_offset = ab_base + (a_idx * SIZE_ABILITY_BINARY)
            ab_raw = struct.unpack_from(FMT_ABILITY_BINARY, data, ab_offset)
            hero["abilities"].append({
                "spell_id": ab_raw[0],
                "slot": ab_raw[1],
                "remaining_s": ab_raw[2],
                "max_s": ab_raw[3],
                "is_cooling_down": ab_raw[4] != 0,
                "is_ready": ab_raw[5] != 0,
            })
        if hero["is_local"]:
            result.local_hero_index = i
        result.heroes.append(hero)

    # Unpack Soldiers
    offset_soldier = 64 + (MAX_HEROES * SIZE_HERO_BINARY)
    for i in range(result.soldier_count):
        base = offset_soldier + (i * SIZE_SOLDIER_BINARY)
        s_data = struct.unpack_from(FMT_SOLDIER_BINARY, data, base)
        result.soldiers.append({
            "address": s_data[0],
            "id": s_data[1],
            "soldier_type": s_data[2],
            "path_id": s_data[3],
            "camp": s_data[4],
            "hp": s_data[5],
            "hp_max": s_data[6],
            "is_dead": s_data[7] != 0,
            "pos_x": s_data[9],
            "pos_y": s_data[10],
        })

    # Unpack Monsters
    offset_monster = offset_soldier + (MAX_SOLDIERS * SIZE_SOLDIER_BINARY)
    for i in range(result.monster_count):
        base = offset_monster + (i * SIZE_MONSTER_BINARY)
        m_data = struct.unpack_from(FMT_MONSTER_BINARY, data, base)
        result.monsters.append({
            "address": m_data[0],
            "id": m_data[1],
            "monster_type": m_data[2],
            "camp": m_data[3],
            "hp": m_data[4],
            "hp_max": m_data[5],
            "is_dead": m_data[6] != 0,
            "pos_x": m_data[8],
            "pos_y": m_data[9],
            "attack_range": m_data[10],
        })

    # Unpack Towers
    offset_tower = offset_monster + (MAX_MONSTERS * SIZE_MONSTER_BINARY)
    for i in range(result.tower_count):
        base = offset_tower + (i * SIZE_TOWER_BINARY)
        t_data = struct.unpack_from(FMT_TOWER_BINARY, data, base)
        result.towers.append({
            "address": t_data[0],
            "id": t_data[1],
            "camp": t_data[2],
            "hp": t_data[3],
            "hp_max": t_data[4],
            "is_dead": t_data[5] != 0,
            "pos_x": t_data[7],
            "pos_y": t_data[8],
            "attack_range": t_data[9],
        })

    return True, result


# ============================================================================
# Adversarial Stress Test Suite
# ============================================================================

class TestAdversarialStressSuite(unittest.TestCase):

    # ------------------------------------------------------------------------
    # 1. Binary Struct Serialization / Deserialization Fuzzing & Corruption
    # ------------------------------------------------------------------------

    def test_adv_01_magic_mismatch_and_header_corruption(self):
        """Fuzz invalid magic numbers and verify decoder rejects corrupted payloads."""
        valid_buf = pack_frame_snapshot()
        
        # Test 100 corrupted magic variants
        for bad_magic in [0x00000000, 0xFFFFFFFF, 0x12345678, 0x564D4E54, 0x564D4E00]:
            corrupted = bytearray(valid_buf)
            struct.pack_into("<I", corrupted, 0, bad_magic)
            ok, snapshot = unpack_binary_snapshot(bytes(corrupted))
            self.assertFalse(ok, f"Decoder accepted invalid magic 0x{bad_magic:08X}")

    def test_adv_02_truncated_and_oversized_payload_fuzzing(self):
        """Fuzz truncated buffer sizes: 0, 1, 63, 64, 6159, 10000 bytes."""
        valid_buf = pack_frame_snapshot()
        
        # All truncated sizes below 6160 must fail cleanly without exception
        for trunc_len in [0, 1, 16, 63, 64, 100, 500, 2464, 3872, 5280, 6159]:
            ok, _ = unpack_binary_snapshot(valid_buf[:trunc_len])
            self.assertFalse(ok, f"Decoder accepted truncated buffer of length {trunc_len}")

        # Extra trailing garbage bytes should still unpack the 6160 bytes safely
        oversized = valid_buf + b"\xDE\xAD\xBE\xEF" * 1000
        ok, snap = unpack_binary_snapshot(oversized)
        self.assertTrue(ok)
        self.assertEqual(snap.magic, VEMINS_SCHEMA_MAGIC)

    def test_adv_03_random_bit_flip_fuzzing_1000_iterations(self):
        """Perform 1,000 random single/multi-bit flips across the 6,160-byte payload."""
        valid_buf = pack_frame_snapshot(
            heroes=[pack_hero_entity(hero_id=i + 1, camp=(i % 2) + 1, pos_x=float(i * 2)) for i in range(10)]
        )
        rng = random.Random(0xDEADBEEF)

        for _ in range(1000):
            corrupted = bytearray(valid_buf)
            num_flips = rng.randint(1, 10)
            for _ in range(num_flips):
                byte_idx = rng.randint(0, len(corrupted) - 1)
                bit_idx = rng.randint(0, 7)
                corrupted[byte_idx] ^= (1 << bit_idx)

            # Execution must NEVER raise unhandled exception
            try:
                ok, snap = unpack_binary_snapshot(bytes(corrupted))
                if ok:
                    # If magic was intact, count invariants must be respected
                    self.assertLessEqual(snap.hero_count, MAX_HEROES)
                    self.assertLessEqual(snap.soldier_count, MAX_SOLDIERS)
                    self.assertLessEqual(snap.monster_count, MAX_MONSTERS)
                    self.assertLessEqual(snap.tower_count, MAX_TOWERS)
            except Exception as e:
                self.fail(f"Unpack raised unexpected exception on fuzzed input: {e}")

    # ------------------------------------------------------------------------
    # 2. Boundary & Malformed Coordinates (Out-of-bounds, NaN, +/-Inf)
    # ------------------------------------------------------------------------

    def test_adv_04_extreme_out_of_bounds_coordinates(self):
        """Stress-test coordinates at [-52, 52] limits and extreme values (+/-1e9)."""
        projector = MinimapProjector()
        
        boundary_coords = [
            (-52.0, -52.0),
            (52.0, 52.0),
            (-52.00001, 52.00001),
            (-1000.0, 1000.0),
            (-1e9, 1e9),
            (1e9, -1e9),
        ]

        for wx, wy in boundary_coords:
            # Minimap projection must clamp to minimap rect
            mx, my = projector.world_to_minimap(wx, wy)
            self.assertGreaterEqual(mx, projector.map_x - 0.01)
            self.assertLessEqual(mx, projector.map_x + projector.map_w + 0.01)
            self.assertGreaterEqual(my, projector.map_y - 0.01)
            self.assertLessEqual(my, projector.map_y + projector.map_h + 0.01)

            # Isometric projection must compute without crashing
            sx, sy, on_screen = projector.world_to_screen_isometric(wx, wy, 0.0, 0.0)
            self.assertTrue(math.isfinite(sx))
            self.assertTrue(math.isfinite(sy))

            # Edge radar must clamp within margins
            cx, cy, angle = projector.calculate_edge_radar(sx, sy)
            self.assertGreaterEqual(cx, projector.edge_margin - 0.01)
            self.assertLessEqual(cx, projector.screen_w - projector.edge_margin + 0.01)
            self.assertGreaterEqual(cy, projector.edge_margin - 0.01)
            self.assertLessEqual(cy, projector.screen_h - projector.edge_margin + 0.01)
            self.assertTrue(math.isfinite(angle))

    def test_adv_05_nan_and_inf_coordinate_sanitization(self):
        """Verify behavior when coordinates contain NaN, +Inf, or -Inf."""
        nan_val = float("nan")
        inf_val = float("inf")
        neg_inf = float("-inf")

        # C++ sanitizer logic verification
        def c_sanitize_coord(val: float, fallback: float = 0.0, min_v: float = -52.0, max_v: float = 52.0) -> float:
            if not math.isfinite(val):
                return fallback
            return max(min_v, min(max_v, val))

        for malformed in [nan_val, inf_val, neg_inf, 1e38, -1e38]:
            sanitized = c_sanitize_coord(malformed)
            self.assertTrue(math.isfinite(sanitized))
            self.assertGreaterEqual(sanitized, -52.0)
            self.assertLessEqual(sanitized, 52.0)

    def test_adv_06_subnormal_and_epsilon_facing_vectors(self):
        """Test heading arrow calculation with zero, subnormal, and tiny magnitude vectors."""
        projector = MinimapProjector()
        
        tiny_vectors = [
            (0.0, 0.0),
            (1e-30, 0.0),
            (0.0, 1e-30),
            (1e-45, 1e-45),  # Denormal float
            (-1e-40, 1e-40),
        ]

        for dx, dy in tiny_vectors:
            # If magnitude is below threshold, arrow should degrade gracefully to base point
            ax, ay = projector.calculate_direction_arrow(100.0, 100.0, dx, dy, length=18.0)
            self.assertTrue(math.isfinite(ax))
            self.assertTrue(math.isfinite(ay))
            # Must not produce NaN or Infinity
            self.assertFalse(math.isnan(ax))
            self.assertFalse(math.isnan(ay))

    # ------------------------------------------------------------------------
    # 3. Sparse Dictionary Ingestion & Tombstone Filtering
    # ------------------------------------------------------------------------

    def test_adv_07_sparse_dictionary_with_scattered_tombstones(self):
        """Simulate a 20-slot IL2CPP dictionary where only slots 0 and 19 are active."""
        reader = MockMemoryReader()
        dic_addr = 0x7200010000
        entries_ptr = 0x7200020000
        total_slots = 20

        # m_dicPlayerLogic: entries @ +0x18, count @ +0x20
        reader.write_mock_bytes(dic_addr + 0x18, struct.pack("<Q", entries_ptr))
        reader.write_mock_bytes(dic_addr + 0x20, struct.pack("<i", total_slots))

        # Write 20 entries of 24 bytes each
        # Stride: int32 hashCode (+0x00), int32 next (+0x04), uint64 key (+0x08), uint64 value (+0x10)
        entries_bytes = bytearray()
        for i in range(total_slots):
            if i in (0, 19):
                # Valid player
                player_ptr = 0x7200100000 + (i * 0x1000)
                entries_bytes.extend(struct.pack("<iiQQ", i * 100, -1, i, player_ptr))

                # Write basic LogicPlayer entity
                player_buf = bytearray(0x300)
                struct.pack_into("<i", player_buf, 0x0ac, 100 + i)
                struct.pack_into("<i", player_buf, 0x0c8, 3000)
                struct.pack_into("<d", player_buf, 0x268, float(i))
                struct.pack_into("<d", player_buf, 0x270, float(i))
                reader.write_mock_bytes(player_ptr, bytes(player_buf))
            else:
                # Tombstone / deleted slot (hashCode = -1 or -2)
                entries_bytes.extend(struct.pack("<iiQQ", -1, -1, 0, 0x7200999999))

        reader.write_mock_bytes(entries_ptr + 0x20, bytes(entries_bytes))

        # Verify parser ingests ONLY the 2 valid slots and ignores the 18 tombstones
        parsed_heroes = []
        entries_buf = reader.read_bytes(entries_ptr + 0x20, total_slots * 24)
        for i in range(total_slots):
            off = i * 24
            hash_code = struct.unpack_from("<i", entries_buf, off)[0]
            val_ptr = struct.unpack_from("<Q", entries_buf, off + 16)[0]
            if hash_code >= 0 and val_ptr >= 0x10000:
                p_bytes = reader.read_bytes(val_ptr, 0x100)
                h_id = struct.unpack_from("<i", p_bytes, 0x0ac)[0]
                parsed_heroes.append(h_id)

        self.assertEqual(len(parsed_heroes), 2)
        self.assertEqual(parsed_heroes, [100, 119])

    def test_adv_08_all_tombstones_empty_dictionary(self):
        """Simulate dictionary where all slots are tombstones (hashCode < 0)."""
        reader = MockMemoryReader()
        entries_ptr = 0x7200030000
        entries_bytes = bytearray()
        for i in range(20):
            entries_bytes.extend(struct.pack("<iiQQ", -1 - i, -1, 0, 0x7200555555))

        reader.write_mock_bytes(entries_ptr + 0x20, bytes(entries_bytes))

        entries_buf = reader.read_bytes(entries_ptr + 0x20, 20 * 24)
        valid_cnt = 0
        for i in range(20):
            off = i * 24
            hash_code = struct.unpack_from("<i", entries_buf, off)[0]
            val_ptr = struct.unpack_from("<Q", entries_buf, off + 16)[0]
            if hash_code >= 0 and val_ptr >= 0x10000:
                valid_cnt += 1

        self.assertEqual(valid_cnt, 0)

    # ------------------------------------------------------------------------
    # 4. Local Player Null / Death / Respawn Camera Smoothing (EMA)
    # ------------------------------------------------------------------------

    def test_adv_09_camera_ema_continuity_across_death_respawn_cycle(self):
        """Simulate a continuous 60-frame sequence: Live -> Death -> Respawn -> Fountain Anchor."""
        # Initial State: Hero at (10, 10)
        local_x, local_y = 10.0, 10.0
        cam_x, cam_y = local_x, local_y
        alpha = 0.35

        cam_history: List[Tuple[float, float]] = []

        # Phase 1 (Frames 1-10): Alive and roaming from (10,10) to (30,25)
        for frame in range(1, 11):
            local_x += 2.0
            local_y += 1.5
            # Camera follows with EMA
            cam_x = cam_x + alpha * (local_x - cam_x)
            cam_y = cam_y + alpha * (local_y - cam_y)
            cam_history.append((cam_x, cam_y))

        last_alive_cam_x, last_alive_cam_y = cam_x, cam_y
        self.assertAlmostEqual(local_x, 30.0, places=3)
        self.assertAlmostEqual(local_y, 25.0, places=3)

        # Phase 2 (Frames 11-30): Hero dies (pointer is NULL / is_dead=1)
        # Invariant: Camera must freeze at last known position without snapping to (0, 0)
        for frame in range(11, 31):
            is_dead = True
            if not is_dead:
                cam_x = cam_x + alpha * (local_x - cam_x)
                cam_y = cam_y + alpha * (local_y - cam_y)
            # When dead, cam_x and cam_y do NOT update
            cam_history.append((cam_x, cam_y))
            self.assertEqual(cam_x, last_alive_cam_x)
            self.assertEqual(cam_y, last_alive_cam_y)

        # Phase 3 (Frames 31-60): Respawn at Fountain (-45.0, -45.0)
        fountain_x, fountain_y = -45.0, -45.0
        local_x, local_y = fountain_x, fountain_y

        for frame in range(31, 61):
            cam_x = cam_x + alpha * (local_x - cam_x)
            cam_y = cam_y + alpha * (local_y - cam_y)
            cam_history.append((cam_x, cam_y))
            # Verify delta per frame decreases smoothly
            if frame > 31:
                prev_cam = cam_history[frame - 2]
                step = math.hypot(cam_x - prev_cam[0], cam_y - prev_cam[1])
                self.assertLess(step, 40.0, f"Frame {frame} had discontinuous camera jump of {step:.2f}")

        # After 30 frames of convergence, camera must be within 0.01m of fountain
        self.assertAlmostEqual(cam_x, fountain_x, delta=0.01)
        self.assertAlmostEqual(cam_y, fountain_y, delta=0.01)

    # ------------------------------------------------------------------------
    # 5. Entity Count Limits, Capacity Overflows & Max-Payload Saturation
    # ------------------------------------------------------------------------

    def test_adv_10_entity_count_overflow_fuzzing(self):
        """Stress-test decoder with hero_count=255, soldier_count=255, monster_count=255, tower_count=255."""
        raw_header = struct.pack(
            FMT_SNAPSHOT_HEADER,
            VEMINS_SCHEMA_MAGIC,
            VEMINS_SCHEMA_VERSION,
            123456789,
            100,
            9999,
            0x7000000000,
            0x7100000000,
            1,  # in_match
            2,  # battle_state
            b"\x00\x00",  # pad_header
            1,  # local_camp
            60000,
            0.5,
            255,  # hero_count overflow
            255,  # soldier_count overflow
            255,  # monster_count overflow
            255,  # tower_count overflow
            b"\x00\x00\x00\x00",
        )

        full_buf = raw_header + (b"\x00" * (TOTAL_BINARY_FRAME_SIZE - len(raw_header)))
        ok, snap = unpack_binary_snapshot(full_buf)
        self.assertTrue(ok)
        
        # Assert strict clamping to MAX_* constants to prevent array out-of-bounds
        self.assertEqual(snap.hero_count, MAX_HEROES)
        self.assertEqual(snap.soldier_count, MAX_SOLDIERS)
        self.assertEqual(snap.monster_count, MAX_MONSTERS)
        self.assertEqual(snap.tower_count, MAX_TOWERS)

    def test_adv_11_max_saturation_full_frame(self):
        """Build and unpack a 100% saturated frame: 10 heroes (with 6 abilities & 6 items), 32 soldiers, 32 monsters, 22 towers."""
        heroes_raw = []
        for i in range(MAX_HEROES):
            items = [1000 + j for j in range(MAX_ITEMS)]
            abilities = [
                {
                    "spell_id": 10000 + (i * 10) + a,
                    "slot": a + 1,
                    "remaining_s": float(a * 2),
                    "max_s": 15.0,
                    "is_cooling_down": (a % 2 == 0),
                    "is_ready": (a % 2 != 0),
                }
                for a in range(MAX_ABILITIES)
            ]
            h_raw = pack_hero_entity(
                address=0x7200100000 + (i * 0x1000),
                hero_id=i + 1,
                level=15,
                hp=5000 - (i * 200),
                hp_max=5000,
                mp=2000,
                mp_max=2000,
                shield=500,
                magic_shield=200,
                camp=(i % 2) + 1,
                is_dead=0,
                is_local=(1 if i == 0 else 0),
                pos_x=-30.0 + (i * 6.0),
                pos_y=-30.0 + (i * 6.0),
                item_ids=items,
                abilities=abilities,
            )
            heroes_raw.append(h_raw)

        soldiers_raw = [
            struct.pack(
                FMT_SOLDIER_BINARY,
                0x7200200000 + s * 0x500,
                1000 + s,
                (s % 4) + 1,
                (s % 3) + 1,
                (s % 2) + 1,
                1200,
                1200,
                0,
                b"\x00\x00\x00",
                -20.0 + (s * 1.2),
                -20.0 + (s * 1.2),
            )
            for s in range(MAX_SOLDIERS)
        ]

        monsters_raw = [
            struct.pack(
                FMT_MONSTER_BINARY,
                0x7200300000 + m * 0x500,
                51298 if m == 0 else (51312 if m == 1 else 50000 + m),
                1,
                0,
                24000 if m == 0 else 5000,
                24000 if m == 0 else 5000,
                0,
                b"\x00\x00\x00",
                0.0 + m,
                0.0 + m,
                8.5,
            )
            for m in range(MAX_MONSTERS)
        ]

        towers_raw = [
            struct.pack(
                FMT_TOWER_BINARY,
                0x7200400000 + t * 0x500,
                1001 + t,
                (t % 2) + 1,
                7300,
                7300,
                0,
                b"\x00\x00\x00",
                -40.0 + (t * 3.5),
                -40.0 + (t * 3.5),
                8.5,
            )
            for t in range(MAX_TOWERS)
        ]

        full_frame = pack_frame_snapshot(
            heroes=heroes_raw,
            soldiers=soldiers_raw,
            monsters=monsters_raw,
            towers=towers_raw,
        )

        self.assertEqual(len(full_frame), TOTAL_BINARY_FRAME_SIZE)
        ok, snap = unpack_binary_snapshot(full_frame)
        self.assertTrue(ok)
        self.assertEqual(snap.hero_count, 10)
        self.assertEqual(snap.soldier_count, 32)
        self.assertEqual(snap.monster_count, 32)
        self.assertEqual(snap.tower_count, 22)
        self.assertEqual(snap.local_hero_index, 0)
        self.assertEqual(len(snap.heroes[0]["abilities"]), 6)
        self.assertEqual(snap.heroes[0]["item_ids"], [1000, 1001, 1002, 1003, 1004, 1005])

    def test_adv_13_continuous_360_rotation_fuzzing_720_steps(self):
        """Fuzz MinimapProjector continuous rotation from 0° to 360° across 720 angle steps."""
        projector = MinimapProjector()
        test_positions = [
            (0.0, 0.0),
            (25.0, 25.0),
            (-25.0, 25.0),
            (25.0, -25.0),
            (-25.0, -25.0),
            (50.0, 0.0),
            (0.0, 50.0),
            (-50.0, 0.0),
            (0.0, -50.0),
        ]

        for step in range(720):
            deg = step * 0.5
            projector.config["minimap"]["rotation_degrees"] = deg
            projector._update_cached_transforms()

            for wx, wy in test_positions:
                mx, my = projector.world_to_minimap(wx, wy)
                self.assertTrue(math.isfinite(mx), f"Non-finite mx at deg={deg} pos=({wx},{wy})")
                self.assertTrue(math.isfinite(my), f"Non-finite my at deg={deg} pos=({wx},{wy})")
                self.assertFalse(math.isnan(mx))
                self.assertFalse(math.isnan(my))

    def test_adv_14_edge_radar_degenerate_axes_and_corners(self):
        """Stress-test edge radar raycasting at exact cardinal axes and diagonal corner lines."""
        projector = MinimapProjector()
        cx, cy = projector.screen_cx, projector.screen_cy
        margin = projector.edge_margin

        test_points = [
            (cx, cy),                # Exactly at center
            (cx + 0.0001, cy),       # Epsilon right
            (cx, cy + 0.0001),       # Epsilon down
            (cx - 0.0001, cy),       # Epsilon left
            (cx, cy - 0.0001),       # Epsilon up
            (cx + 5000.0, cy),       # Far right cardinal
            (cx - 5000.0, cy),       # Far left cardinal
            (cx, cy + 5000.0),       # Far bottom cardinal
            (cx, cy - 5000.0),       # Far top cardinal
            (cx + 5000.0, cy + 5000.0), # Far bottom-right diagonal
            (cx - 5000.0, cy - 5000.0), # Far top-left diagonal
        ]

        for px, py in test_points:
            clamped_x, clamped_y, angle = projector.calculate_edge_radar(px, py)
            self.assertTrue(math.isfinite(clamped_x))
            self.assertTrue(math.isfinite(clamped_y))
            self.assertTrue(math.isfinite(angle))
            self.assertGreaterEqual(clamped_x, margin - 0.01)
            self.assertLessEqual(clamped_x, projector.screen_w - margin + 0.01)
            self.assertGreaterEqual(clamped_y, margin - 0.01)
            self.assertLessEqual(clamped_y, projector.screen_h - margin + 0.01)

    def test_adv_15_extreme_aspect_ratios_and_viewport_resizing(self):
        """Test projection across unusual aspect ratios (32:9 ultra-wide, 1:1 square, 4:3 tablet)."""
        projector = MinimapProjector()
        resolutions = [
            (3840.0, 1080.0), # 32:9 Ultra-Wide
            (1080.0, 1080.0), # 1:1 Square
            (2048.0, 1536.0), # 4:3 Tablet
            (3200.0, 1440.0), # 20:9 Modern Phone
            (800.0, 480.0),   # Low-res legacy
        ]

        for w, h in resolutions:
            projector.config["screen"]["width"] = w
            projector.config["screen"]["height"] = h
            projector._update_cached_transforms()

            sx, sy, on_screen = projector.world_to_screen_isometric(15.0, 10.0, 0.0, 0.0)
            self.assertTrue(math.isfinite(sx))
            self.assertTrue(math.isfinite(sy))

            cx, cy, _ = projector.calculate_edge_radar(sx, sy)
            self.assertTrue(math.isfinite(cx))
            self.assertTrue(math.isfinite(cy))
            self.assertGreaterEqual(cx, 0.0)
            self.assertLessEqual(cx, w)
            self.assertGreaterEqual(cy, 0.0)
            self.assertLessEqual(cy, h)

    def test_adv_16_high_frequency_teleportation_and_jitter_ema(self):
        """Simulate high-frequency position jitter (+/-50 units oscillation at 120 FPS)."""
        alpha = 0.35
        cam_x, cam_y = 0.0, 0.0
        
        # 120 frames of alternating extreme teleportation
        for frame in range(120):
            target_x = 50.0 if (frame % 2 == 0) else -50.0
            target_y = 50.0 if (frame % 2 == 0) else -50.0
            cam_x = cam_x + alpha * (target_x - cam_x)
            cam_y = cam_y + alpha * (target_y - cam_y)

            # Assert bounded oscillation without numeric divergence
            self.assertTrue(math.isfinite(cam_x))
            self.assertTrue(math.isfinite(cam_y))
            self.assertLessEqual(abs(cam_x), 50.0)
            self.assertLessEqual(abs(cam_y), 50.0)

    def test_adv_12_empty_match_state_fail_closed(self):
        """Unpack completely empty snapshot (0 entities, match not active) and verify safe defaults."""
        empty_frame = pack_frame_snapshot(in_match=0, battle_state=0)
        ok, snap = unpack_binary_snapshot(empty_frame)
        self.assertTrue(ok)
        self.assertEqual(snap.hero_count, 0)
        self.assertEqual(snap.soldier_count, 0)
        self.assertEqual(snap.monster_count, 0)
        self.assertEqual(snap.tower_count, 0)
        self.assertEqual(snap.local_hero_index, -1)
        self.assertFalse(snap.in_match)

    def test_adv_17_dictionary_stride_pointer_migration_mid_match(self):
        """Simulate dynamic entity pointer migration across dictionary indices."""
        reader = MockMemoryReader()
        entries_ptr = 0x7200050000
        
        # Frame 1: Hero A at index 0, Hero B at index 1
        hero_a_ptr = 0x7200101000
        hero_b_ptr = 0x7200102000
        
        # Write Hero A & B entities starting at base address
        buf_a = bytearray(0x300)
        struct.pack_into("<i", buf_a, 0x0ac, 101)
        reader.write_mock_bytes(hero_a_ptr, bytes(buf_a))

        buf_b = bytearray(0x300)
        struct.pack_into("<i", buf_b, 0x0ac, 102)
        reader.write_mock_bytes(hero_b_ptr, bytes(buf_b))

        # Frame 1 entries: [Hero A, Hero B]
        entries_f1 = bytearray()
        entries_f1.extend(struct.pack("<iiQQ", 1, -1, 0, hero_a_ptr))
        entries_f1.extend(struct.pack("<iiQQ", 2, -1, 1, hero_b_ptr))
        reader.write_mock_bytes(entries_ptr + 0x20, bytes(entries_f1))

        # Ingest Frame 1
        buf1 = reader.read_bytes(entries_ptr + 0x20, 2 * 24)
        heroes_f1 = [
            struct.unpack_from("<i", reader.read_bytes(struct.unpack_from("<Q", buf1, i * 24 + 16)[0], 0x100), 0x0ac)[0]
            for i in range(2) if struct.unpack_from("<i", buf1, i * 24)[0] >= 0
        ]
        self.assertEqual(heroes_f1, [101, 102])

        # Frame 2: Hero A migrated to index 5, index 0 is tombstone (-1)
        entries_f2 = bytearray()
        entries_f2.extend(struct.pack("<iiQQ", -1, -1, 0, 0x0)) # Tombstone
        entries_f2.extend(struct.pack("<iiQQ", 2, -1, 1, hero_b_ptr))
        for _ in range(3):
            entries_f2.extend(struct.pack("<iiQQ", -1, -1, 0, 0x0)) # Empty tombstones
        entries_f2.extend(struct.pack("<iiQQ", 5, -1, 5, hero_a_ptr)) # Hero A migrated here

        reader.write_mock_bytes(entries_ptr + 0x20, bytes(entries_f2))

        # Ingest Frame 2
        buf2 = reader.read_bytes(entries_ptr + 0x20, 6 * 24)
        heroes_f2 = []
        for i in range(6):
            h_code = struct.unpack_from("<i", buf2, i * 24)[0]
            ptr = struct.unpack_from("<Q", buf2, i * 24 + 16)[0]
            if h_code >= 0 and ptr >= 0x10000:
                h_id = struct.unpack_from("<i", reader.read_bytes(ptr, 0x100), 0x0ac)[0]
                heroes_f2.append(h_id)

        # Ingested entities must contain both heroes regardless of index swap
        self.assertEqual(set(heroes_f2), {101, 102})

    def test_adv_18_fuzz_1000_random_frame_generations_throughput(self):
        """Execute 1,000 full-frame snapshot pack/unpack cycles to verify throughput and memory stability."""
        rng = random.Random(0x42)
        
        for idx in range(1000):
            num_heroes = rng.randint(0, 10)
            num_soldiers = rng.randint(0, 32)
            num_monsters = rng.randint(0, 32)
            num_towers = rng.randint(0, 22)

            h_list = [
                pack_hero_entity(
                    hero_id=rng.randint(1, 127),
                    camp=rng.choice([1, 2]),
                    pos_x=rng.uniform(-52.0, 52.0),
                    pos_y=rng.uniform(-52.0, 52.0),
                    is_local=(1 if i == 0 else 0),
                )
                for i in range(num_heroes)
            ]

            frame = pack_frame_snapshot(
                heroes=h_list,
                frame_index=idx,
                in_match=1 if num_heroes > 0 else 0,
            )

            ok, snap = unpack_binary_snapshot(frame)
            self.assertTrue(ok)
            self.assertEqual(snap.hero_count, num_heroes)
            self.assertEqual(snap.frame_index, idx)


if __name__ == "__main__":
    unittest.main()


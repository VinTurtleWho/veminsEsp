"""
Snapshot Engine: Coordinates memory acquisition, schema decoding, and builds immutable WorldSnapshot instances.
Uses GenericFieldReader as the authoritative decoding engine.
Strictly read-only; does not modify game memory or state.
Adheres strictly to Gate 8 (Entity Identity Resolution):
- NEVER resolves local player using hero ID, level, HP, address ordering, or naive heuristics.
- Local player identity is assigned ONLY via proven game-owned pointer reference and pointer-identity matching.
"""

import struct
import time
from typing import List, Optional, Tuple

from perception.memory_reader import DaemonMemoryReader, MemoryReader
from perception.models import (
    BulletEntity,
    HeroEntity,
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
from perception.schema import FieldRegistry, GenericFieldReader


class SnapshotEngine:
    """Read-only perception engine for capturing consistent game world snapshots."""

    def __init__(self, reader: MemoryReader, registry: Optional[FieldRegistry] = None):
        self.reader = reader
        self.registry = registry or FieldRegistry.load_from_file()
        self.generic_reader = GenericFieldReader(self.reader, self.registry)
        self._proven_local_player_ptr: int = 0
        self._cached_hero_camp: int = 1
        self._sequence_id: int = 0

    def set_proven_local_player_ptr(self, ptr: int) -> None:
        """Sets the proven game-owned local player pointer (Gate 8)."""
        self._proven_local_player_ptr = ptr

    def resolve_local_player_from_manager(self, battle_manager_addr: int) -> int:
        """
        Resolves local player pointer strictly from LogicBattleManager game-owned references (Gate 8):
        1. Reads m_RealSelfPlayer at +0x200 (LogicPlayer* pointer)
        2. Fallback: reads m_LocalPlayerLogic at +0x0a0 (LogicFighter* pointer)
        Validates target object structure via schema reader.
        """
        if battle_manager_addr <= 0:
            return 0

        # Try +0x200: m_RealSelfPlayer
        raw_self_ptr = self.reader.read_bytes(battle_manager_addr + 0x200, 8)
        if len(raw_self_ptr) == 8:
            import struct
            ptr = struct.unpack("<Q", raw_self_ptr)[0]
            if 0x10000000 <= ptr < 0x8000000000:
                hero_dict = self.generic_reader.read_entity(ptr, expected_class="Battle.LogicPlayer")
                if hero_dict:
                    return ptr

        # Try +0x0a0: m_LocalPlayerLogic
        raw_local_ptr = self.reader.read_bytes(battle_manager_addr + 0x0a0, 8)
        if len(raw_local_ptr) == 8:
            import struct
            ptr = struct.unpack("<Q", raw_local_ptr)[0]
            if 0x10000000 <= ptr < 0x8000000000:
                hero_dict = self.generic_reader.read_entity(ptr, expected_class="Battle.LogicPlayer")
                if hero_dict:
                    return ptr

        return 0

    def capture_snapshot(
        self,
        known_entity_addrs: Optional[List[int]] = None,
        local_player_ptr: Optional[int] = None,
        battle_manager_addr: Optional[int] = None,
        confidence_policy: str = "PROVEN"
    ) -> WorldSnapshot:
        """
        Captures and parses all visible game entities into an immutable WorldSnapshot.
        
        Gate 8 Identity Rules:
        - If local_player_ptr is provided (or proven), validates that exact pointer and assigns local_player.
        - If battle_manager_addr is provided, resolves local player from game-owned m_RealSelfPlayer (+0x200).
        - If no proven local player pointer is available, local_player is set to None (UNPROVEN).
        - All other entities are filtered by pointer identity (addr != local_player_ptr).
        """
        now_ns = time.time_ns()

        # Determine target local player pointer via Gate 8 game-owned reference
        target_hero_ptr = local_player_ptr or self._proven_local_player_ptr
        if target_hero_ptr <= 0 and battle_manager_addr:
            target_hero_ptr = self.resolve_local_player_from_manager(battle_manager_addr)

        # 1. Resolve Local Hero Entity via Pointer Identity (Gate 8)
        local_player: Optional[HeroEntity] = None

        if target_hero_ptr > 0:
            hero_dict = self.generic_reader.read_entity(
                target_hero_ptr,
                confidence_policy=confidence_policy,
                expected_class="Battle.LogicPlayer"
            )
            if hero_dict:
                skill_comp_ptr = hero_dict.get("skill_comp_ptr", 0)
                if skill_comp_ptr:
                    hero_dict["abilities"] = EntityParser.decode_cooldowns(self.reader, skill_comp_ptr)
                equip_comp_ptr = hero_dict.get("equip_comp_ptr", 0)
                if equip_comp_ptr:
                    hero_dict["inventory"] = EntityParser.decode_inventory(self.reader, equip_comp_ptr)
                auras_dict_ptr = hero_dict.get("auras_dict_ptr", 0)
                if auras_dict_ptr:
                    hero_dict["buffs"] = EntityParser.decode_buffs(self.reader, auras_dict_ptr)
                attr_comp_ptr = hero_dict.get("attr_comp_ptr", 0)
                if attr_comp_ptr:
                    hero_dict["combat_attributes"] = EntityParser.decode_attributes(self.reader, attr_comp_ptr)
                relive_data_ptr = hero_dict.get("relive_data_ptr", 0)
                if not relive_data_ptr and target_hero_ptr > 0:
                    raw_relive = self.reader.read_bytes(target_hero_ptr + 0x580, 8)
                    if len(raw_relive) == 8:
                        relive_data_ptr = struct.unpack("<Q", raw_relive)[0]
                if relive_data_ptr:
                    r_time, k_id = EntityParser.decode_relive_data(self.reader, relive_data_ptr)
                    hero_dict["respawn_time_ms"] = r_time
                    hero_dict["killer_id"] = k_id
                local_player = EntityParser.dict_to_hero(
                    hero_dict,
                    local_player_addr=target_hero_ptr
                )
                if local_player:
                    self._cached_hero_camp = local_player.camp

        ref_x = local_player.pos_x if local_player else 0.0
        ref_y = local_player.pos_y if local_player else 0.0

        # 2. Parse Known / Discovered Entities
        allies: List[HeroEntity] = []
        enemies: List[HeroEntity] = []
        towers: List[TowerEntity] = []
        soldiers: List[SoldierEntity] = []
        monsters: List[MonsterEntity] = []
        bullets: List[BulletEntity] = []

        if known_entity_addrs:
            for addr in known_entity_addrs:
                # Gate 8: Pointer-identity exclusion (do not duplicate local player into ally/enemy lists)
                if target_hero_ptr > 0 and addr == target_hero_ptr:
                    continue

                entity_dict = self.generic_reader.read_entity(
                    addr,
                    confidence_policy=confidence_policy
                )
                if not entity_dict:
                    continue

                cname = entity_dict.get("_class", "")
                vtable = entity_dict.get("_vtable", 0)

                if cname == "Battle.LogicPlayer" or vtable == KLASS_PLAYER:
                    skill_comp_ptr = entity_dict.get("skill_comp_ptr", 0)
                    if skill_comp_ptr:
                        entity_dict["abilities"] = EntityParser.decode_cooldowns(self.reader, skill_comp_ptr)
                    equip_comp_ptr = entity_dict.get("equip_comp_ptr", 0)
                    if equip_comp_ptr:
                        entity_dict["inventory"] = EntityParser.decode_inventory(self.reader, equip_comp_ptr)
                    auras_dict_ptr = entity_dict.get("auras_dict_ptr", 0)
                    if auras_dict_ptr:
                        entity_dict["buffs"] = EntityParser.decode_buffs(self.reader, auras_dict_ptr)
                    attr_comp_ptr = entity_dict.get("attr_comp_ptr", 0)
                    if attr_comp_ptr:
                        entity_dict["combat_attributes"] = EntityParser.decode_attributes(self.reader, attr_comp_ptr)
                    relive_data_ptr = entity_dict.get("relive_data_ptr", 0)
                    if not relive_data_ptr and addr > 0:
                        raw_relive = self.reader.read_bytes(addr + 0x580, 8)
                        if len(raw_relive) == 8:
                            relive_data_ptr = struct.unpack("<Q", raw_relive)[0]
                    if relive_data_ptr:
                        r_time, k_id = EntityParser.decode_relive_data(self.reader, relive_data_ptr)
                        entity_dict["respawn_time_ms"] = r_time
                        entity_dict["killer_id"] = k_id
                    hero = EntityParser.dict_to_hero(
                        entity_dict,
                        local_player_addr=target_hero_ptr,
                        ref_x=ref_x,
                        ref_y=ref_y
                    )
                    if hero:
                        if local_player and hero.camp == self._cached_hero_camp:
                            allies.append(hero)
                        else:
                            enemies.append(hero)

                elif cname == "Battle.LogicTower" or vtable == KLASS_TOWER:
                    tower = EntityParser.dict_to_tower(entity_dict, ref_x, ref_y)
                    if tower:
                        towers.append(tower)

                elif cname == "Battle.LogicBulletBase" or vtable == KLASS_BULLET:
                    bullet = EntityParser.dict_to_bullet(entity_dict)
                    if bullet and not bullet.is_destroy:
                        bullets.append(bullet)

                elif cname == "Battle.LogicSoldier" or vtable == KLASS_SOLDIER:
                    soldier = EntityParser.dict_to_soldier(entity_dict, ref_x, ref_y)
                    if soldier and soldier.hp > 0 and not soldier.is_dead:
                        soldiers.append(soldier)

                elif cname in ("Battle.LogicMonster", "Battle.LogicWildMonster") or vtable in (KLASS_MONSTER, KLASS_WILD_MONSTER):
                    monster = EntityParser.dict_to_monster(entity_dict, ref_x, ref_y)
                    if monster and monster.hp > 0 and not monster.is_dead:
                        monsters.append(monster)

                elif vtable == KLASS_BULLET:
                    bullet = EntityParser.dict_to_bullet(entity_dict)
                    if bullet and not bullet.is_destroy:
                        bullets.append(bullet)

        self._sequence_id += 1
        frame_time_ms = 0
        battle_state = 0
        if battle_manager_addr and battle_manager_addr >= 0x10000000:
            raw_mgr = self.reader.read_bytes(battle_manager_addr + 0x180, 0x24)
            if len(raw_mgr) >= 0x20:
                battle_state = struct.unpack_from("<i", raw_mgr, 0x00)[0]
                frame_time_ms = struct.unpack_from("<I", raw_mgr, 0x1c)[0]

        in_match = (local_player is not None) or (len(allies) + len(enemies) > 0)

        return WorldSnapshot(
            timestamp_ns=now_ns,
            in_match=in_match,
            local_player=local_player,
            allies=tuple(allies),
            enemies=tuple(enemies),
            towers=tuple(towers),
            soldiers=tuple(soldiers),
            monsters=tuple(monsters),
            bullets=tuple(bullets),
            sequence_id=self._sequence_id,
            frame_time_ms=frame_time_ms,
            battle_state=battle_state
        )

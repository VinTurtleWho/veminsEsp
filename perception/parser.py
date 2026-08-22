"""
Entity Parser: Adapts generic schema-decoded dictionaries into immutable perception dataclasses.
Uses GenericFieldReader as the authoritative source of offset decoding and validation.
"""

import math
import struct
from typing import Any, Dict, Optional, Tuple

from perception.memory_reader import MemoryReader, MockMemoryReader
from perception.models import (
    AbilityCooldown,
    ActiveBuff,
    BulletEntity,
    HeroAbilities,
    HeroBuffs,
    HeroCombatAttributes,
    HeroEntity,
    HeroInventory,
    HeroStatusEffects,
    ItemSlot,
    MonsterEntity,
    SoldierEntity,
    TowerEntity,
)
from perception.schema import FieldRegistry, GenericFieldReader

# Verified IL2CPP VTable Signatures
KLASS_PLAYER = 0x742002fdf8
KLASS_TOWER = 0x74201ccee8
KLASS_SOLDIER = 0x741ff9d098
KLASS_MONSTER = 0x741ff3bec0
KLASS_WILD_MONSTER = 0x741ff3ad80
KLASS_BULLET = 0x7421113bb0


class EntityParser:
    """Stateless binary parser and dataclass adapter for schema-decoded entities."""

    @staticmethod
    def calc_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x2 - x1, y2 - y1)

    @classmethod
    def decode_cooldowns(
        cls,
        reader: MemoryReader,
        skill_comp_ptr: int
    ) -> HeroAbilities:
        """
        Safely unpacks HeroAbilities from LogicSkillComp -> CoolDownComp -> m_DicCoolInfo.
        Preserves complete fail-closed behavior: invalid or null pointers return an empty HeroAbilities().
        """
        if not skill_comp_ptr or skill_comp_ptr < 0x10000000 or skill_comp_ptr >= 0x8000000000:
            return HeroAbilities()

        try:
            # Bulk-read SkillComp header: m_pCurSpell (+0x058, 8B) and m_CoolDownComp (+0x0a8, 8B)
            # Read 0x0b0 bytes starting at skill_comp_ptr to cover both fields
            raw_skill_comp = reader.read_bytes(skill_comp_ptr, 0x0b0)
            if len(raw_skill_comp) < 0x0b0:
                return HeroAbilities()

            active_spell_ptr = struct.unpack_from("<Q", raw_skill_comp, 0x058)[0]
            is_casting = (active_spell_ptr > 0)

            cooldown_comp_ptr = struct.unpack_from("<Q", raw_skill_comp, 0x0a8)[0]
            if not cooldown_comp_ptr or cooldown_comp_ptr < 0x10000000 or cooldown_comp_ptr >= 0x8000000000:
                return HeroAbilities(active_spell_ptr=active_spell_ptr, is_casting=is_casting)

            raw_cd_comp = reader.read_bytes(cooldown_comp_ptr + 0x018, 8)
            if len(raw_cd_comp) != 8:
                return HeroAbilities(active_spell_ptr=active_spell_ptr, is_casting=is_casting)

            dict_ptr = struct.unpack("<Q", raw_cd_comp)[0]
            if not dict_ptr or dict_ptr < 0x10000000 or dict_ptr >= 0x8000000000:
                return HeroAbilities(active_spell_ptr=active_spell_ptr, is_casting=is_casting)

            # Bulk-read dictionary header: entries_ptr (+0x018, 8B) + count (+0x020, 4B)
            raw_dict_hdr = reader.read_bytes(dict_ptr + 0x018, 12)
            if len(raw_dict_hdr) < 12:
                return HeroAbilities(active_spell_ptr=active_spell_ptr, is_casting=is_casting)

            entries_ptr = struct.unpack_from("<Q", raw_dict_hdr, 0)[0]
            count = struct.unpack_from("<i", raw_dict_hdr, 8)[0]

            if count <= 0 or count > 32 or not entries_ptr or entries_ptr < 0x10000000 or entries_ptr >= 0x8000000000:
                return HeroAbilities(active_spell_ptr=active_spell_ptr, is_casting=is_casting)

            cooldowns = []
            base_entry_addr = entries_ptr + 0x20

            for i in range(count):
                slot_addr = base_entry_addr + (i * 24)
                raw_slot = reader.read_bytes(slot_addr, 24)
                if len(raw_slot) != 24:
                    continue

                hash_code, next_idx, spell_id, _, cd_data_ptr = struct.unpack("<iiiIQ", raw_slot)
                if hash_code >= 0 and cd_data_ptr and 0x10000000 <= cd_data_ptr < 0x8000000000:
                    raw_cd = reader.read_bytes(cd_data_ptr + 0x010, 20)
                    if len(raw_cd) >= 17:
                        cd_spell_id, ui_cool_time, orig_max_cd, ui_start_time, is_cd_byte = struct.unpack("<iIII?", raw_cd[:17])
                        cooldowns.append(AbilityCooldown(
                            spell_id=cd_spell_id if cd_spell_id != 0 else spell_id,
                            remaining_cd_ms=ui_cool_time,
                            max_cd_ms=orig_max_cd,
                            start_time_ms=ui_start_time,
                            is_cooling_down=bool(is_cd_byte)
                        ))

            return HeroAbilities(
                active_spell_ptr=active_spell_ptr,
                is_casting=is_casting,
                cooldowns=tuple(cooldowns)
            )
        except Exception:
            return HeroAbilities()

    @classmethod
    def decode_inventory(
        cls,
        reader: MemoryReader,
        equip_comp_ptr: int
    ) -> HeroInventory:
        """
        Safely unpacks HeroInventory from LogicEquipComp -> EquipDictionary -> LogicEquipInfo.
        Preserves complete fail-closed behavior: invalid or null pointers return an empty HeroInventory().
        """
        if not equip_comp_ptr or equip_comp_ptr < 0x10000000 or equip_comp_ptr >= 0x8000000000:
            return HeroInventory()

        try:
            # Bulk-read EquipComp header: covers iMaxCnt (+0x010), m_EquipList (+0x028),
            # m_BuyGankShoeCount (+0x074), m_UseEquipIndex (+0x078)
            raw_equip_comp = reader.read_bytes(equip_comp_ptr, 0x07c)
            if len(raw_equip_comp) < 0x07c:
                return HeroInventory()

            max_slot_count = struct.unpack_from("<i", raw_equip_comp, 0x010)[0]
            if max_slot_count <= 0 or max_slot_count > 12:
                max_slot_count = 6

            roam_blessing = struct.unpack_from("<i", raw_equip_comp, 0x074)[0]
            active_slot_index = struct.unpack_from("<i", raw_equip_comp, 0x078)[0]

            dict_ptr = struct.unpack_from("<Q", raw_equip_comp, 0x028)[0]
            if not dict_ptr or dict_ptr < 0x10000000 or dict_ptr >= 0x8000000000:
                return HeroInventory(max_slot_count=max_slot_count, active_slot_index=active_slot_index, roam_blessing_count=roam_blessing)

            # Bulk-read dictionary header: entries_ptr (+0x018, 8B) + count (+0x020, 4B)
            raw_dict_hdr = reader.read_bytes(dict_ptr + 0x018, 12)
            if len(raw_dict_hdr) < 12:
                return HeroInventory(max_slot_count=max_slot_count, active_slot_index=active_slot_index, roam_blessing_count=roam_blessing)

            entries_ptr = struct.unpack_from("<Q", raw_dict_hdr, 0)[0]
            count = struct.unpack_from("<i", raw_dict_hdr, 8)[0]

            if count <= 0 or count > 6 or not entries_ptr or entries_ptr < 0x10000000 or entries_ptr >= 0x8000000000:
                return HeroInventory(max_slot_count=max_slot_count, active_slot_index=active_slot_index, roam_blessing_count=roam_blessing)

            items = []
            # Deterministically detect 24-byte boxed vs 16-byte unboxed EquipDictionary layout
            raw_entries = reader.read_bytes(entries_ptr + 0x20, count * 24)
            is_boxed = False
            if len(raw_entries) >= 24:
                hc0, _, s0, _, p0 = struct.unpack_from("<iiiIQ", raw_entries, 0)
                if hc0 >= 0 and 0x10000000 <= p0 < 0x8000000000:
                    is_boxed = True

            if is_boxed:
                for i in range(count):
                    off = i * 24
                    if off + 24 <= len(raw_entries):
                        hc, _, slot_idx, _, eq_ptr = struct.unpack_from("<iiiIQ", raw_entries, off)
                        if hc >= 0 and 0x10000000 <= eq_ptr < 0x8000000000:
                            # Bulk-read LogicEquipInfo: m_iEquipId (+0x010) and m_iInitPrice (+0x030)
                            raw_equip_info = reader.read_bytes(eq_ptr + 0x010, 0x24)
                            if len(raw_equip_info) >= 0x24:
                                items.append(ItemSlot(
                                    slot_index=slot_idx,
                                    item_id=struct.unpack_from("<i", raw_equip_info, 0x000)[0],  # +0x010
                                    price=struct.unpack_from("<i", raw_equip_info, 0x020)[0]      # +0x030
                                ))
            else:
                for i in range(count):
                    off = i * 16
                    if off + 16 <= len(raw_entries):
                        hc, _ = struct.unpack_from("<ii", raw_entries, off)
                        slot_idx, item_id = struct.unpack_from("<ii", raw_entries, off + 8)
                        if hc >= 0 and item_id > 0:
                            items.append(ItemSlot(
                                slot_index=slot_idx,
                                item_id=item_id,
                                price=0
                            ))

            return HeroInventory(
                max_slot_count=max_slot_count,
                active_slot_index=active_slot_index,
                roam_blessing_count=roam_blessing,
                items=tuple(items)
            )
        except Exception:
            return HeroInventory()

    @classmethod
    def decode_buffs(
        cls,
        reader: MemoryReader,
        auras_dict_ptr: int
    ) -> HeroBuffs:
        """
        Safely unpacks HeroBuffs from LogicFighter.auras -> Dictionary<int, LogicEffect*>.
        Preserves complete fail-closed behavior: invalid or null pointers return an empty HeroBuffs().
        """
        if not auras_dict_ptr or auras_dict_ptr < 0x10000000 or auras_dict_ptr >= 0x8000000000:
            return HeroBuffs()

        try:
            # 1. Bulk-read dictionary header: entries_ptr (+0x018, 8B) + count (+0x020, 4B)
            raw_dict_hdr = reader.read_bytes(auras_dict_ptr + 0x018, 12)
            if len(raw_dict_hdr) < 12:
                return HeroBuffs()

            entries_ptr = struct.unpack_from("<Q", raw_dict_hdr, 0)[0]
            count = struct.unpack_from("<i", raw_dict_hdr, 8)[0]

            if count <= 0 or count > 32 or not entries_ptr or entries_ptr < 0x10000000 or entries_ptr >= 0x8000000000:
                return HeroBuffs()

            # 2. Iterate Entry buffer (Stride = 24 bytes, base = entries_ptr + 0x20)
            buffs = []
            base_entry_addr = entries_ptr + 0x20

            for i in range(count):
                slot_addr = base_entry_addr + (i * 24)
                raw_slot = reader.read_bytes(slot_addr, 24)
                if len(raw_slot) != 24:
                    continue

                hash_code, next_idx, effect_id, _, effect_ptr = struct.unpack("<iiiIQ", raw_slot)
                if hash_code >= 0 and effect_ptr and 0x10000000 <= effect_ptr < 0x8000000000:
                    # Bulk-read entire LogicEffect struct (0x010..0x10c) in ONE IPC call
                    raw_effect = reader.read_bytes(effect_ptr + 0x010, 0x100)
                    if len(raw_effect) < 0x100:
                        continue

                    is_finished = bool(raw_effect[0x070])  # +0x080 - 0x010 = 0x070
                    if not is_finished:
                        guid = struct.unpack_from("<I", raw_effect, 0x000)[0]          # +0x010
                        owner_id = struct.unpack_from("<I", raw_effect, 0x010)[0]      # +0x020
                        src_spell_id = struct.unpack_from("<i", raw_effect, 0x074)[0]  # +0x084
                        stack_count = struct.unpack_from("<I", raw_effect, 0x080)[0]   # +0x090
                        val = struct.unpack_from("<i", raw_effect, 0x0e0)[0]           # +0x0f0
                        last_update = struct.unpack_from("<I", raw_effect, 0x0f8)[0]   # +0x108

                        buffs.append(ActiveBuff(
                            effect_id=effect_id,
                            guid=guid,
                            owner_id=owner_id,
                            source_spell_id=src_spell_id,
                            stack_count=max(1, stack_count),
                            value=val,
                            is_finished=is_finished,
                            last_update_time=last_update
                        ))

            return HeroBuffs(buffs=tuple(buffs))
        except Exception:
            return HeroBuffs()

    @classmethod
    def decode_attributes(
        cls,
        reader: MemoryReader,
        attr_comp_ptr: int
    ) -> HeroCombatAttributes:
        """
        Safely unpacks HeroCombatAttributes from LogicFighter.m_AttrComp (+0x4d8) -> AttrData.m_dictIncreaseAttrs (+0x38).
        Preserves complete fail-closed behavior: invalid or null pointers return default HeroCombatAttributes().
        """
        if not attr_comp_ptr or attr_comp_ptr < 0x10000000 or attr_comp_ptr >= 0x8000000000:
            return HeroCombatAttributes()

        try:
            # 1. Read m_dictIncreaseAttrs pointer (+0x38 on AttrData)
            raw_dict_ptr = reader.read_bytes(attr_comp_ptr + 0x038, 8)
            if len(raw_dict_ptr) != 8:
                return HeroCombatAttributes()

            dict_ptr = struct.unpack("<Q", raw_dict_ptr)[0]
            if not dict_ptr or dict_ptr < 0x10000000 or dict_ptr >= 0x8000000000:
                return HeroCombatAttributes()

            # 2. Bulk-read dictionary header: entries_ptr (+0x18, 8B) + count (+0x20, 4B)
            raw_dict_hdr = reader.read_bytes(dict_ptr + 0x018, 12)
            if len(raw_dict_hdr) < 12:
                return HeroCombatAttributes()

            entries_ptr = struct.unpack_from("<Q", raw_dict_hdr, 0)[0]
            count = struct.unpack_from("<i", raw_dict_hdr, 8)[0]

            if count <= 0 or count > 64 or not entries_ptr or entries_ptr < 0x10000000 or entries_ptr >= 0x8000000000:
                return HeroCombatAttributes()

            # 3. Iterate Entry buffer (exact 44-byte unboxed struct stride)
            # Entry: hashCode (4B), next (4B), key (4B), AttrIncrease: id (4B), base (4B), base_per (4B), add (4B), all_per (4B), level (4B), result (4B), current (4B)
            attr_dict: Dict[int, int] = {}
            base_entry_addr = entries_ptr + 0x20
            entry_stride = 44
            raw_entries = reader.read_bytes(base_entry_addr, count * entry_stride)

            if len(raw_entries) >= entry_stride:
                for i in range(count):
                    off = i * entry_stride
                    if off + entry_stride <= len(raw_entries):
                        hc, next_idx, key = struct.unpack_from("<iii", raw_entries, off)
                        if hc >= 0:
                            # RESULT is at off + 0x0c (AttrIncrease header) + 0x18 (index 5 * 4) = off + 36
                            result_val = struct.unpack_from("<i", raw_entries, off + 36)[0]
                            attr_dict[key] = result_val

            return HeroCombatAttributes(
                physical_attack=attr_dict.get(102, 0),
                magic_power=attr_dict.get(103, 0),
                physical_defense=attr_dict.get(106, 0),
                magic_defense=attr_dict.get(107, 0),
                movement_speed=float(attr_dict.get(105, 0)),
                attack_speed=float(attr_dict.get(104, 0)) / 10000.0 if attr_dict.get(104, 0) > 1000 else float(attr_dict.get(104, 0)),
                cooldown_reduction=float(attr_dict.get(36, 0)) / 100.0,
                crit_rate=float(attr_dict.get(30, 0)) / 100.0,
                phys_penetration_flat=attr_dict.get(41, 0),
                phys_penetration_percent=float(attr_dict.get(12, 0)) / 100.0,
                mag_penetration_flat=attr_dict.get(42, 0),
                mag_penetration_percent=float(attr_dict.get(13, 0)) / 100.0,
                physical_lifesteal=float(attr_dict.get(39, 0)) / 100.0,
                spell_vamp=float(attr_dict.get(40, 0)) / 100.0,
                hp_regen=float(attr_dict.get(108, 0)),
                mana_regen=float(attr_dict.get(109, 0)),
            )
        except Exception:
            return HeroCombatAttributes()

    @classmethod
    def decode_relive_data(cls, reader: Any, relive_data_ptr: int) -> Tuple[int, int]:
        """
        Decodes ReliveData (+0x580 on LogicFighter):
        +0x20: uint32 iReliveTime (remaining ms until respawn)
        +0x30: uint32 iKillerId (killer GUID)
        """
        if not relive_data_ptr or relive_data_ptr < 0x10000000:
            return 0, 0
        raw = reader.read_bytes(relive_data_ptr, 0x38)
        if len(raw) < 0x34:
            return 0, 0
        try:
            relive_time_ms = struct.unpack_from("<I", raw, 0x20)[0]
            killer_id = struct.unpack_from("<I", raw, 0x30)[0]
            return relive_time_ms, killer_id
        except Exception:
            return 0, 0

    @classmethod
    def dict_to_hero(
        cls,
        d: Dict[str, Any],
        local_player_addr: int = 0,
        ref_x: float = 0.0,
        ref_y: float = 0.0
    ) -> Optional[HeroEntity]:
        """Converts a schema-decoded dictionary into a HeroEntity dataclass."""
        try:
            address = d["address"]
            hero_id = d["hero_id"]
            level = d["level"]
            hp = d["hp"]
            hp_max = d["hp_max"]
            is_dead = bool(d.get("is_dead", False))
            camp = d["camp"]
            pos_x = float(d["pos_x"])
            pos_y = float(d["pos_y"])
            gold = int(d.get("gold", 0))
            is_bot = bool(d.get("is_bot", False))

            is_local = (local_player_addr > 0 and address == local_player_addr)
            dist = 0.0 if is_local else cls.calc_distance(ref_x, ref_y, pos_x, pos_y)

            raw_status = int(d.get("status", 0))
            status_effects = HeroStatusEffects.from_mask(raw_status)

            abilities = d.get("abilities")
            if not isinstance(abilities, HeroAbilities):
                abilities = HeroAbilities()

            inventory = d.get("inventory")
            if not isinstance(inventory, HeroInventory):
                inventory = HeroInventory()

            buffs = d.get("buffs")
            if not isinstance(buffs, HeroBuffs):
                buffs = HeroBuffs()

            combat_attributes = d.get("combat_attributes")
            if not isinstance(combat_attributes, HeroCombatAttributes):
                combat_attributes = HeroCombatAttributes(
                    physical_attack=int(d.get("physical_attack", 0)),
                    magic_power=int(d.get("magic_power", 0)),
                    physical_defense=int(d.get("physical_defense", 0)),
                    magic_defense=int(d.get("magic_defense", 0)),
                    movement_speed=float(d.get("run_speed", 0.0)),
                    attack_speed=float(d.get("attack_speed", 0.0)),
                    cooldown_reduction=float(d.get("cooldown_reduction", 0.0)),
                    crit_rate=float(d.get("crit_rate", 0.0)),
                    phys_penetration_flat=int(d.get("phys_penetration_flat", 0)),
                    phys_penetration_percent=float(d.get("phys_penetration_percent", 0.0)),
                    mag_penetration_flat=int(d.get("mag_penetration_flat", 0)),
                    mag_penetration_percent=float(d.get("mag_penetration_percent", 0.0)),
                    physical_lifesteal=float(d.get("physical_lifesteal", 0.0)),
                    spell_vamp=float(d.get("spell_vamp", 0.0)),
                    hp_regen=float(d.get("hp_regen", 0.0)),
                    mana_regen=float(d.get("mana_regen", 0.0))
                )

            return HeroEntity(
                address=address,
                hero_id=hero_id,
                level=level,
                hp=hp,
                hp_max=hp_max,
                is_dead=is_dead,
                camp=camp,
                pos_x=pos_x,
                pos_y=pos_y,
                gold=gold,
                is_bot=is_bot,
                is_local_player=is_local,
                distance_to_me=dist,
                # Vitals & Resources (P1-3)
                mp=int(d.get("mp", 0)),
                mp_max=int(d.get("mp_max", 0)),
                # Active Live Shields (P1-3)
                shield=int(d.get("shield", 0)),
                shield_max=int(d.get("shield_max", 0)),
                magic_shield=int(d.get("magic_shield", 0)),
                magic_shield_max=int(d.get("magic_shield_max", 0)),
                mech_armor_hp=int(d.get("mech_armor_hp", 0)),
                # Invulnerability & Combat State (P1-3)
                is_invulnerable=bool(d.get("is_invulnerable", False)),
                kill_bounty=int(d.get("kill_bounty", 0)),
                # Combat Attributes (P1-4)
                combat_attributes=combat_attributes,
                # Active Buffs & Temporary Effects (P1-3)
                buffs=buffs,
                # Abilities & Cooldowns (P1-1)
                abilities=abilities,
                # Equipment & Inventory (P1-2)
                inventory=inventory,
                # Kinematics & Orientation (P0-4)
                facing_x=float(d.get("facing_x", 0.0)),
                facing_y=float(d.get("facing_y", 0.0)),
                move_dir_x=float(d.get("move_dir_x", 0.0)),
                move_dir_y=float(d.get("move_dir_y", 0.0)),
                movement_dest_x=float(d.get("movement_dest_x", 0.0)),
                movement_dest_y=float(d.get("movement_dest_y", 0.0)),
                run_speed=float(d.get("run_speed", 0.0)),
                attack_speed=float(d.get("attack_speed", 0.0)),
                # Visibility (HYPOTHESIS)
                is_visible=bool(d.get("is_visible", True)),
                status_mask=raw_status,
                status_effects=status_effects,
                status=raw_status,
                in_battle=bool(d.get("in_battle", False)),
                born_pos_x=float(d.get("born_pos_x", 0.0)),
                born_pos_y=float(d.get("born_pos_y", 0.0)),
                # Target Graph Fields (P0-3)
                face_lock_target_id=int(d.get("face_lock_target_id", 0)),
                attacker_id=int(d.get("attacker_id", 0)),
                attacker_ptr=int(d.get("attacker_ptr", 0)),
                be_attack_timestamp=int(d.get("be_attack_timestamp", 0)),
                attack_timestamp=int(d.get("attack_timestamp", 0)),
                target_enemy_ptr=int(d.get("target_enemy_ptr", 0)),
                real_enemy_ptr=int(d.get("real_enemy_ptr", 0)),
                hate_enemy_ptr=int(d.get("hate_enemy_ptr", 0)),
                stare_target_guid=int(d.get("stare_target_guid", 0)),
                assigned_lane=int(d.get("assigned_lane", 0)),
                battle_spell_id=int(d.get("battle_spell_id", 0)),
                emblem_id=int(d.get("emblem_id", 0)),
                emblem_level=int(d.get("emblem_level", 0)),
                player_name=str(d.get("player_name", "")),
                rank_level=int(d.get("rank_level", 0)),
                rank_stars=int(d.get("rank_stars", 0)),
                mythic_points=int(d.get("mythic_points", 0)),
                elo_rating=int(d.get("elo_rating", 0)),
                respawn_time_ms=int(d.get("respawn_time_ms", 0)),
                killer_id=int(d.get("killer_id", 0)),
                hurt_total_value=float(d.get("hurt_total_value", 0.0)),
                hurt_hero_value=float(d.get("hurt_hero_value", 0.0)),
                hurt_tower_value=float(d.get("hurt_tower_value", 0.0)),
                injured_shield=int(d.get("injured_shield", 0)),
                injured_value=float(d.get("injured_value", 0.0)),
                cure_teammate=float(d.get("cure_teammate", 0.0)),
                kill_tower_times=int(d.get("kill_tower_times", 0)),
                last_hit_creep=int(d.get("last_hit_creep", 0)),
                kill_dragon_times=int(d.get("kill_dragon_times", 0)),
                kill_outer_tower=int(d.get("kill_outer_tower", 0)),
                kill_inner_tower=int(d.get("kill_inner_tower", 0)),
                kill_inhibitor_tower=int(d.get("kill_inhibitor_tower", 0))
            )
        except (KeyError, ValueError, TypeError):
            return None

    @classmethod
    def dict_to_tower(
        cls,
        d: Dict[str, Any],
        ref_x: float = 0.0,
        ref_y: float = 0.0
    ) -> Optional[TowerEntity]:
        """Converts a schema-decoded dictionary into a TowerEntity dataclass."""
        try:
            address = d["address"]
            tower_id = d["tower_id"]
            tower_type = int(d.get("tower_type", 0))
            hp = d["hp"]
            hp_max = d["hp_max"]
            is_dead = bool(d.get("is_dead", False))
            camp = d["camp"]
            pos_x = float(d["pos_x"])
            pos_y = float(d["pos_y"])
            tower_index = int(d.get("tower_index", 0))
            senior_pos_id = int(d.get("senior_pos_id", 0))
            guard_id = int(d.get("guard_id", 0))
            eye_range = float(d.get("eye_range", 0.0))
            attack_range = float(d.get("attack_range", 0.0))

            dist = cls.calc_distance(ref_x, ref_y, pos_x, pos_y)

            return TowerEntity(
                address=address,
                tower_id=tower_id,
                tower_type=tower_type,
                hp=hp,
                hp_max=hp_max,
                is_dead=is_dead,
                camp=camp,
                pos_x=pos_x,
                pos_y=pos_y,
                tower_index=tower_index,
                senior_pos_id=senior_pos_id,
                guard_id=guard_id,
                eye_range=eye_range,
                attack_range=attack_range,
                distance_to_me=dist
            )
        except (KeyError, ValueError, TypeError):
            return None

    @classmethod
    def dict_to_soldier(
        cls,
        d: Dict[str, Any],
        ref_x: float = 0.0,
        ref_y: float = 0.0
    ) -> Optional[SoldierEntity]:
        """Converts a schema-decoded dictionary into a SoldierEntity dataclass."""
        try:
            address = d["address"]
            soldier_id = d["soldier_id"]
            soldier_type = int(d.get("soldier_type", 0))
            lane = int(d.get("lane", 0))
            point_index = int(d.get("point_index", 0))
            hp = d["hp"]
            hp_max = d["hp_max"]
            is_dead = bool(d.get("is_dead", False))
            camp = d["camp"]
            pos_x = float(d["pos_x"])
            pos_y = float(d["pos_y"])
            stake_soldier = bool(d.get("stake_soldier", False))

            dist = cls.calc_distance(ref_x, ref_y, pos_x, pos_y)

            return SoldierEntity(
                address=address,
                soldier_id=soldier_id,
                soldier_type=soldier_type,
                lane=lane,
                point_index=point_index,
                hp=hp,
                hp_max=hp_max,
                is_dead=is_dead,
                camp=camp,
                pos_x=pos_x,
                pos_y=pos_y,
                stake_soldier=stake_soldier,
                distance_to_me=dist
            )
        except (KeyError, ValueError, TypeError):
            return None

    @classmethod
    def dict_to_monster(
        cls,
        d: Dict[str, Any],
        ref_x: float = 0.0,
        ref_y: float = 0.0
    ) -> Optional[MonsterEntity]:
        """Converts a schema-decoded dictionary into a MonsterEntity dataclass."""
        try:
            address = d["address"]
            monster_id = d["monster_id"]
            hp = d["hp"]
            hp_max = d["hp_max"]
            is_dead = bool(d.get("is_dead", False))
            camp = int(d.get("camp", 0))
            pos_x = float(d["pos_x"])
            pos_y = float(d["pos_y"])
            monster_type = int(d.get("monster_type", 0))
            is_wild = (d.get("_vtable") == KLASS_WILD_MONSTER)
            base_money = float(d.get("base_money", 0.0))
            money = float(d.get("money", 0.0))
            base_exp = int(d.get("base_exp", 0))
            exp = int(d.get("exp", 0))

            dist = cls.calc_distance(ref_x, ref_y, pos_x, pos_y)

            return MonsterEntity(
                address=address,
                monster_id=monster_id,
                monster_type=monster_type,
                hp=hp,
                hp_max=hp_max,
                is_dead=is_dead,
                camp=camp,
                pos_x=pos_x,
                pos_y=pos_y,
                is_wild=is_wild,
                base_money=base_money,
                money=money,
                base_exp=base_exp,
                exp=exp,
                distance_to_me=dist
            )
        except (KeyError, ValueError, TypeError):
            return None

    @classmethod
    def dict_to_bullet(cls, d: Dict[str, Any]) -> Optional[BulletEntity]:
        """Converts a schema-decoded dictionary into a BulletEntity dataclass."""
        try:
            address = d["address"]
            bullet_id = d["bullet_id"]
            is_destroy = bool(d.get("is_destroy", False))
            fly_distance = float(d.get("fly_distance", 0.0))
            radius = float(d.get("radius", 0.0))
            owner_ptr = int(d.get("owner_ptr", 0))
            target_ptr = int(d.get("target_ptr", 0))

            return BulletEntity(
                address=address,
                bullet_id=bullet_id,
                is_destroy=is_destroy,
                fly_distance=fly_distance,
                radius=radius,
                owner_ptr=owner_ptr,
                pos_x=float(d.get("pos_x", 0.0)),
                pos_y=float(d.get("pos_y", 0.0)),
                dir_x=float(d.get("dir_x", 0.0)),
                dir_y=float(d.get("dir_y", 0.0)),
                speed=float(d.get("speed", 0.0))
            )
        except (KeyError, ValueError, TypeError):
            return None

    # Backward-compatible direct buffer parsing methods routed through schema
    @classmethod
    def parse_hero(
        cls,
        address: int,
        raw: bytes = b"",
        local_player_addr: int = 0,
        ref_x: float = 0.0,
        ref_y: float = 0.0,
        reader: Optional[MemoryReader] = None
    ) -> Optional[HeroEntity]:
        mock_reader = reader or MockMemoryReader()
        if raw and not reader:
            mock_reader.write_mock_bytes(address, raw)
        buf_size = len(raw) if raw else 0x1000
        greader = GenericFieldReader(mock_reader)
        d = greader.read_entity(address, confidence_policy="VALIDATED", buffer_size=buf_size)
        if not d:
            return None

        skill_comp_ptr = d.get("skill_comp_ptr", 0)
        if skill_comp_ptr:
            d["abilities"] = cls.decode_cooldowns(mock_reader, skill_comp_ptr)

        equip_comp_ptr = d.get("equip_comp_ptr", 0)
        if equip_comp_ptr:
            d["inventory"] = cls.decode_inventory(mock_reader, equip_comp_ptr)

        auras_dict_ptr = d.get("auras_dict_ptr", 0)
        if auras_dict_ptr:
            d["buffs"] = cls.decode_buffs(mock_reader, auras_dict_ptr)

        attr_comp_ptr = d.get("attr_comp_ptr", 0)
        if attr_comp_ptr:
            d["combat_attributes"] = cls.decode_attributes(mock_reader, attr_comp_ptr)

        return cls.dict_to_hero(d, local_player_addr, ref_x, ref_y)

    @classmethod
    def parse_tower(cls, address: int, raw: bytes, ref_x: float = 0.0, ref_y: float = 0.0) -> Optional[TowerEntity]:
        mock_reader = MockMemoryReader()
        mock_reader.write_mock_bytes(address, raw)
        greader = GenericFieldReader(mock_reader)
        d = greader.read_entity(address, confidence_policy="VALIDATED", buffer_size=len(raw))
        return cls.dict_to_tower(d, ref_x, ref_y) if d else None

    @classmethod
    def parse_soldier(cls, address: int, raw: bytes, ref_x: float = 0.0, ref_y: float = 0.0) -> Optional[SoldierEntity]:
        mock_reader = MockMemoryReader()
        mock_reader.write_mock_bytes(address, raw)
        greader = GenericFieldReader(mock_reader)
        d = greader.read_entity(address, confidence_policy="VALIDATED", buffer_size=len(raw))
        return cls.dict_to_soldier(d, ref_x, ref_y) if d else None

    @classmethod
    def parse_monster(cls, address: int, raw: bytes, ref_x: float = 0.0, ref_y: float = 0.0) -> Optional[MonsterEntity]:
        mock_reader = MockMemoryReader()
        mock_reader.write_mock_bytes(address, raw)
        greader = GenericFieldReader(mock_reader)
        d = greader.read_entity(address, confidence_policy="PROVEN", buffer_size=len(raw))
        return cls.dict_to_monster(d, ref_x, ref_y) if d else None

    @classmethod
    def parse_bullet(cls, address: int, raw: bytes) -> Optional[BulletEntity]:
        mock_reader = MockMemoryReader()
        mock_reader.write_mock_bytes(address, raw)
        greader = GenericFieldReader(mock_reader)
        d = greader.read_entity(address, confidence_policy="VALIDATED", buffer_size=len(raw))
        return cls.dict_to_bullet(d) if d else None

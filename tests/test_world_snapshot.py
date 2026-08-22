"""
Comprehensive Unit Test Suite for MLBB WorldSnapshot Perception Layer.
Uses MockMemoryReader with simulated memory byte buffers to test all edge cases.
Includes Gate 8 regression tests for deterministic pointer-identity resolution.
Includes P0-2 tests for Crowd Control and Status bitmask decoding.
Includes P0-3 tests for Target Graph pointers and combat interaction telemetry.
Includes P0-4 tests for Active Projectiles and Kinematics.
Includes P1-1 tests for Hero Abilities and Cooldown Perception.
Includes P1-2 tests for Hero Equipment and Inventory Perception.
Includes P1-3 tests for Hero Buffs, Shields, Mana, and Live Combat Modifiers.
"""

import math
import struct
import unittest

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
    WorldSnapshot,
)
from perception.memory_reader import MockMemoryReader
from perception.parser import (
    KLASS_BULLET,
    KLASS_MONSTER,
    KLASS_PLAYER,
    KLASS_SOLDIER,
    KLASS_TOWER,
    KLASS_WILD_MONSTER,
    EntityParser,
)
from perception.snapshot_engine import SnapshotEngine


def build_mock_hero_buffer(
    hero_id: int = 18,
    level: int = 10,
    hp: int = 3500,
    hp_max: int = 3500,
    mp: int = 1200,
    mp_max: int = 1500,
    shield: int = 0,
    shield_max: int = 0,
    magic_shield: int = 0,
    magic_shield_max: int = 0,
    mech_armor_hp: int = 0,
    is_dead: bool = False,
    camp: int = 1,
    pos_x: float = 15.5,
    pos_y: float = -20.5,
    gold: int = 4500,
    is_bot: bool = False,
    status: int = 0,
    face_lock_target_id: int = 0,
    attacker_id: int = 0,
    attacker_ptr: int = 0,
    be_attack_timestamp: int = 0,
    attack_timestamp: int = 0,
    target_enemy_ptr: int = 0,
    real_enemy_ptr: int = 0,
    hate_enemy_ptr: int = 0,
    stare_target_guid: int = 0,
    facing_x: float = 1.0,
    facing_y: float = 0.0,
    move_dir_x: float = 0.0,
    move_dir_y: float = 1.0,
    run_speed: float = 340.0,
    attack_speed: float = 1.25,
    skill_comp_ptr: int = 0,
    equip_comp_ptr: int = 0,
    auras_dict_ptr: int = 0,
    is_invulnerable: bool = False,
    kill_bounty: int = 200,
    injured_shield: int = 0
) -> bytes:
    """Builds a realistic 0xd50-byte buffer representing a Battle.LogicPlayer entity."""
    buf = bytearray(0xd50)
    # +0x000: Il2CppClass*
    struct.pack_into("<Q", buf, 0x000, KLASS_PLAYER)
    # +0x05c: IsPlayer
    buf[0x05c] = 1
    # +0x0ac: m_ID
    struct.pack_into("<i", buf, 0x0ac, hero_id)
    # +0x0b4: m_Level
    struct.pack_into("<i", buf, 0x0b4, level)
    # +0x0c8: m_Hp
    struct.pack_into("<i", buf, 0x0c8, hp)
    # +0x0cc: m_HpMax
    struct.pack_into("<i", buf, 0x0cc, hp_max)
    # +0x0d8: m_MechArmorHp
    struct.pack_into("<i", buf, 0x0d8, mech_armor_hp)
    # +0x0e4: m_AdditionHp1 (Live Shield)
    struct.pack_into("<i", buf, 0x0e4, shield)
    # +0x0e8: m_AdditionHp1Max
    struct.pack_into("<i", buf, 0x0e8, shield_max)
    # +0x0f0: m_AdditionHp2 (Magic Shield)
    struct.pack_into("<i", buf, 0x0f0, magic_shield)
    # +0x0f4: m_AdditionHp2Max
    struct.pack_into("<i", buf, 0x0f4, magic_shield_max)
    # +0x108: m_Mp
    struct.pack_into("<i", buf, 0x108, mp)
    # +0x10c: _MpMax
    struct.pack_into("<i", buf, 0x10c, mp_max)
    # +0x1d0: m_bDeath
    buf[0x1d0] = 1 if is_dead else 0
    # +0x1dc: m_EntityCampType
    struct.pack_into("<i", buf, 0x1dc, camp)
    # +0x1e4: m_iStatus (Crowd Control & Status Bitmask)
    struct.pack_into("<i", buf, 0x1e4, status)
    # +0x268: m_dRealPosX
    struct.pack_into("<d", buf, 0x268, pos_x)
    # +0x270: m_dRealPosY
    struct.pack_into("<d", buf, 0x270, pos_y)
    # +0x288 / +0x290: _v2MoveDir (x, y)
    struct.pack_into("<d", buf, 0x288, move_dir_x)
    struct.pack_into("<d", buf, 0x290, move_dir_y)
    # +0x298 / +0x2a0: m_v2FaceDir (x, y)
    struct.pack_into("<d", buf, 0x298, facing_x)
    struct.pack_into("<d", buf, 0x2a0, facing_y)
    # +0x370: m_uFaceLockTargetID
    struct.pack_into("<I", buf, 0x370, face_lock_target_id)
    # +0x4c0: auras
    struct.pack_into("<Q", buf, 0x4c0, auras_dict_ptr)
    # +0x4e0: m_SkillComp
    struct.pack_into("<Q", buf, 0x4e0, skill_comp_ptr)
    # +0x4f8: m_EquipComp
    struct.pack_into("<Q", buf, 0x4f8, equip_comp_ptr)
    # +0x560: m_uAttackerId
    struct.pack_into("<I", buf, 0x560, attacker_id)
    # +0x588: m_Attacker
    struct.pack_into("<Q", buf, 0x588, attacker_ptr)
    # +0x590: m_uBeAttackTimestamp
    struct.pack_into("<I", buf, 0x590, be_attack_timestamp)
    # +0x594: m_uAttackTimestamp
    struct.pack_into("<I", buf, 0x594, attack_timestamp)
    # +0x5a8: m_pEnemy
    struct.pack_into("<Q", buf, 0x5a8, target_enemy_ptr)
    # +0x5b0: m_pRealEnemy
    struct.pack_into("<Q", buf, 0x5b0, real_enemy_ptr)
    # +0x5b8: m_HateEnemy
    struct.pack_into("<Q", buf, 0x5b8, hate_enemy_ptr)
    # +0x5c0: m_uStareTargetGUID
    struct.pack_into("<I", buf, 0x5c0, stare_target_guid)
    # +0x720: m_bCantBeHurt
    buf[0x720] = 1 if is_invulnerable else 0
    # +0x750: m_dCurrentRunSpeed
    struct.pack_into("<d", buf, 0x750, run_speed)
    # +0x758: m_dCurrentAtkSpeed
    struct.pack_into("<d", buf, 0x758, attack_speed)
    # +0x858: _totalGold
    struct.pack_into("<i", buf, 0x858, gold)
    # +0x8c8: m_iInjuredShield (Historical Metric)
    struct.pack_into("<i", buf, 0x8c8, injured_shield)
    # +0xb9a: m_IsRobotPlayer
    buf[0xb9a] = 1 if is_bot else 0
    # +0xcf0: m_KillBounty
    struct.pack_into("<i", buf, 0xcf0, kill_bounty)
    return bytes(buf)


def build_mock_skill_comp_buffer(
    cur_spell_ptr: int = 0,
    cooldown_comp_ptr: int = 0x7243001000
) -> bytes:
    """Builds a realistic buffer for LogicSkillComp."""
    buf = bytearray(0xb0)
    struct.pack_into("<Q", buf, 0x058, cur_spell_ptr)
    struct.pack_into("<Q", buf, 0x0a8, cooldown_comp_ptr)
    return bytes(buf)


def build_mock_cooldown_comp_buffer(
    dict_ptr: int = 0x7243002000
) -> bytes:
    """Builds a realistic buffer for CoolDownComp."""
    buf = bytearray(0x50)
    struct.pack_into("<Q", buf, 0x018, dict_ptr)
    return bytes(buf)


def build_mock_cooldown_dict_buffer(
    entries_ptr: int = 0x7243003000,
    count: int = 0
) -> bytes:
    """Builds a realistic buffer for Il2CppDictionary<int, CoolDownData>."""
    buf = bytearray(0x30)
    struct.pack_into("<Q", buf, 0x018, entries_ptr)
    struct.pack_into("<i", buf, 0x020, count)
    return bytes(buf)


def build_mock_cooldown_entries_buffer(
    entries: list
) -> bytes:
    """Builds an entry array buffer for Dictionary entries."""
    count = len(entries)
    buf = bytearray(0x20 + count * 24)
    struct.pack_into("<i", buf, 0x018, count)
    for i, (spell_id, cd_data_ptr) in enumerate(entries):
        offset = 0x20 + i * 24
        struct.pack_into("<i", buf, offset + 0x00, i + 1)  # hashCode >= 0
        struct.pack_into("<i", buf, offset + 0x04, -1)     # next
        struct.pack_into("<i", buf, offset + 0x08, spell_id) # key
        struct.pack_into("<I", buf, offset + 0x0c, 0)      # padding
        struct.pack_into("<Q", buf, offset + 0x10, cd_data_ptr) # value
    return bytes(buf)


def build_mock_cooldown_data_buffer(
    spell_id: int = 10810,
    remaining_cd_ms: int = 0,
    max_cd_ms: int = 8000,
    start_time_ms: int = 12000,
    is_cooling_down: bool = False
) -> bytes:
    """Builds a realistic buffer for CoolDownData."""
    buf = bytearray(0x30)
    struct.pack_into("<i", buf, 0x010, spell_id)
    struct.pack_into("<I", buf, 0x014, remaining_cd_ms)
    struct.pack_into("<I", buf, 0x018, max_cd_ms)
    struct.pack_into("<I", buf, 0x01c, start_time_ms)
    buf[0x020] = 1 if is_cooling_down else 0
    return bytes(buf)


def build_mock_equip_comp_buffer(
    max_cnt: int = 6,
    dict_ptr: int = 0x7243006000,
    roam_blessing: int = 0,
    use_index: int = -1
) -> bytes:
    """Builds a realistic buffer for LogicEquipComp."""
    buf = bytearray(0x90)
    struct.pack_into("<i", buf, 0x010, max_cnt)
    struct.pack_into("<Q", buf, 0x028, dict_ptr)
    struct.pack_into("<i", buf, 0x074, roam_blessing)
    struct.pack_into("<i", buf, 0x078, use_index)
    return bytes(buf)


def build_mock_equip_dict_buffer(
    entries_ptr: int = 0x7243007000,
    count: int = 0
) -> bytes:
    """Builds a realistic buffer for EquipDictionary."""
    buf = bytearray(0x30)
    struct.pack_into("<Q", buf, 0x018, entries_ptr)
    struct.pack_into("<i", buf, 0x020, count)
    return bytes(buf)


def build_mock_equip_entries_buffer(
    entries: list
) -> bytes:
    """Builds an entry array buffer for EquipDictionary entries."""
    count = len(entries)
    buf = bytearray(0x20 + count * 24)
    struct.pack_into("<i", buf, 0x018, count)
    for i, (slot_index, equip_info_ptr) in enumerate(entries):
        offset = 0x20 + i * 24
        struct.pack_into("<i", buf, offset + 0x00, i + 1)  # hashCode >= 0
        struct.pack_into("<i", buf, offset + 0x04, -1)     # next
        struct.pack_into("<i", buf, offset + 0x08, slot_index) # key (slot_index)
        struct.pack_into("<I", buf, offset + 0x0c, 0)      # padding
        struct.pack_into("<Q", buf, offset + 0x10, equip_info_ptr) # value (LogicEquipInfo*)
    return bytes(buf)


def build_mock_equip_info_buffer(
    item_id: int = 2011,
    price: int = 2100
) -> bytes:
    """Builds a realistic buffer for LogicEquipInfo."""
    buf = bytearray(0x40)
    struct.pack_into("<i", buf, 0x010, item_id)
    struct.pack_into("<i", buf, 0x030, price)
    return bytes(buf)


def build_mock_auras_dict_buffer(
    entries_ptr: int = 0x7243009000,
    count: int = 0
) -> bytes:
    """Builds a realistic buffer for LogicFighter.auras Dictionary."""
    buf = bytearray(0x30)
    struct.pack_into("<Q", buf, 0x018, entries_ptr)
    struct.pack_into("<i", buf, 0x020, count)
    return bytes(buf)


def build_mock_auras_entries_buffer(
    entries: list  # list of (effect_id, effect_ptr)
) -> bytes:
    """Builds an entry array buffer for auras dictionary entries."""
    count = len(entries)
    buf = bytearray(0x20 + count * 24)
    struct.pack_into("<i", buf, 0x018, count)
    for i, (effect_id, effect_ptr) in enumerate(entries):
        offset = 0x20 + i * 24
        struct.pack_into("<i", buf, offset + 0x00, i + 1)  # hashCode >= 0
        struct.pack_into("<i", buf, offset + 0x04, -1)     # next
        struct.pack_into("<i", buf, offset + 0x08, effect_id) # key (effect_id)
        struct.pack_into("<I", buf, offset + 0x0c, 0)      # padding
        struct.pack_into("<Q", buf, offset + 0x10, effect_ptr) # value (LogicEffect*)
    return bytes(buf)


def build_mock_logic_effect_buffer(
    effect_id: int = 5001,
    guid: int = 12345,
    owner_id: int = 18,
    is_finished: bool = False,
    source_spell_id: int = 10810,
    stack_count: int = 1,
    value: int = 25,
    last_update_time: int = 45000
) -> bytes:
    """Builds a realistic buffer for LogicEffect."""
    buf = bytearray(0x110)
    struct.pack_into("<I", buf, 0x010, guid)
    struct.pack_into("<i", buf, 0x014, effect_id)
    struct.pack_into("<I", buf, 0x020, owner_id)
    buf[0x080] = 1 if is_finished else 0
    struct.pack_into("<i", buf, 0x084, source_spell_id)
    struct.pack_into("<I", buf, 0x090, stack_count)
    struct.pack_into("<i", buf, 0x0f0, value)
    struct.pack_into("<I", buf, 0x108, last_update_time)
    return bytes(buf)


def build_mock_tower_buffer(
    tower_id: int = 1,
    tower_type: int = 2,
    hp: int = 5000,
    hp_max: int = 5000,
    is_dead: bool = False,
    camp: int = 1,
    pos_x: float = 0.0,
    pos_y: float = 0.0,
    tower_index: int = 3,
    senior_pos_id: int = 101,
    attack_range: float = 8.5
) -> bytes:
    """Builds a realistic 0x940-byte buffer representing a Battle.LogicTower entity."""
    buf = bytearray(0x940)
    struct.pack_into("<Q", buf, 0x000, KLASS_TOWER)
    struct.pack_into("<i", buf, 0x0ac, tower_id)
    struct.pack_into("<i", buf, 0x0c8, hp)
    struct.pack_into("<i", buf, 0x0cc, hp_max)
    buf[0x1d0] = 1 if is_dead else 0
    struct.pack_into("<i", buf, 0x1dc, camp)
    struct.pack_into("<d", buf, 0x268, pos_x)
    struct.pack_into("<d", buf, 0x270, pos_y)
    struct.pack_into("<i", buf, 0x850, tower_type)
    struct.pack_into("<i", buf, 0x8f0, tower_index)
    struct.pack_into("<i", buf, 0x8f4, senior_pos_id)
    struct.pack_into("<d", buf, 0x930, attack_range)
    return bytes(buf)


def build_mock_soldier_buffer(
    soldier_id: int = 10,
    soldier_type: int = 1,
    lane: int = 2,
    point_index: int = 5,
    hp: int = 800,
    hp_max: int = 800,
    is_dead: bool = False,
    camp: int = 2,
    pos_x: float = 5.0,
    pos_y: float = -5.0
) -> bytes:
    """Builds a realistic 0x910-byte buffer representing a Battle.LogicSoldier entity."""
    buf = bytearray(0x910)
    struct.pack_into("<Q", buf, 0x000, KLASS_SOLDIER)
    struct.pack_into("<i", buf, 0x0ac, soldier_id)
    struct.pack_into("<i", buf, 0x0c8, hp)
    struct.pack_into("<i", buf, 0x0cc, hp_max)
    buf[0x1d0] = 1 if is_dead else 0
    struct.pack_into("<i", buf, 0x1dc, camp)
    struct.pack_into("<d", buf, 0x268, pos_x)
    struct.pack_into("<d", buf, 0x270, pos_y)
    struct.pack_into("<i", buf, 0x8f0, soldier_type)
    struct.pack_into("<i", buf, 0x900, lane)
    struct.pack_into("<i", buf, 0x904, point_index)
    return bytes(buf)


def build_mock_monster_buffer(
    monster_id: int = 201,
    monster_type: int = 1,
    hp: int = 2500,
    hp_max: int = 2500,
    is_dead: bool = False,
    camp: int = 0,
    pos_x: float = -12.0,
    pos_y: float = 8.0,
    is_wild: bool = False
) -> bytes:
    """Builds a realistic 0x860-byte buffer representing a Battle.LogicMonster entity."""
    buf = bytearray(0x860)
    k = KLASS_WILD_MONSTER if is_wild else KLASS_MONSTER
    struct.pack_into("<Q", buf, 0x000, k)
    struct.pack_into("<i", buf, 0x0ac, monster_id)
    struct.pack_into("<i", buf, 0x0c8, hp)
    struct.pack_into("<i", buf, 0x0cc, hp_max)
    buf[0x1d0] = 1 if is_dead else 0
    struct.pack_into("<i", buf, 0x1dc, camp)
    struct.pack_into("<d", buf, 0x268, pos_x)
    struct.pack_into("<d", buf, 0x270, pos_y)
    struct.pack_into("<i", buf, 0x850, monster_type)
    return bytes(buf)


def build_mock_bullet_buffer(
    bullet_id: int = 501,
    is_destroy: bool = False,
    fly_distance: float = 12.4,
    radius: float = 1.2,
    owner_ptr: int = 0x724265f000,
    pos_x: float = 10.0,
    pos_y: float = -15.0,
    dir_x: float = 1.0,
    dir_y: float = 0.0,
    speed: float = 14.5
) -> bytes:
    """Builds a realistic 0x140-byte buffer representing a Battle.LogicDirBullet entity."""
    buf = bytearray(0x140)
    struct.pack_into("<Q", buf, 0x000, KLASS_BULLET)
    buf[0x018] = 1 if is_destroy else 0
    struct.pack_into("<i", buf, 0x020, bullet_id)
    struct.pack_into("<d", buf, 0x048, fly_distance)
    struct.pack_into("<d", buf, 0x058, radius)
    struct.pack_into("<d", buf, 0x0c8, speed)
    struct.pack_into("<d", buf, 0x100, pos_x)
    struct.pack_into("<d", buf, 0x108, pos_y)
    struct.pack_into("<d", buf, 0x110, dir_x)
    struct.pack_into("<d", buf, 0x118, dir_y)
    struct.pack_into("<Q", buf, 0x138, owner_ptr)
    return bytes(buf)


def build_mock_battle_manager_buffer(
    real_self_player_ptr: int = 0x724265f000,
    local_player_logic_ptr: int = 0x724265f000,
    frame_time_ms: int = 45200
) -> bytes:
    """Builds a realistic buffer for LogicBattleManager."""
    buf = bytearray(0x270)
    struct.pack_into("<Q", buf, 0x0a0, local_player_logic_ptr)
    struct.pack_into("<I", buf, 0x19c, frame_time_ms)
    struct.pack_into("<Q", buf, 0x200, real_self_player_ptr)
    return bytes(buf)


class TestWorldSnapshotPerception(unittest.TestCase):

    def test_parse_valid_hero(self):
        """Tests parsing a complete, valid Battle.LogicPlayer buffer."""
        raw = build_mock_hero_buffer(hero_id=18, level=10, hp=3000, hp_max=3500, camp=1, pos_x=10.0, pos_y=20.0, gold=5200, is_bot=False)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw, local_player_addr=0x1000)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.address, 0x1000)
        self.assertEqual(hero.hero_id, 18)
        self.assertEqual(hero.level, 10)
        self.assertEqual(hero.hp, 3000)
        self.assertEqual(hero.hp_max, 3500)
        self.assertFalse(hero.is_dead)
        self.assertEqual(hero.camp, 1)
        self.assertAlmostEqual(hero.pos_x, 10.0)
        self.assertAlmostEqual(hero.pos_y, 20.0)
        self.assertEqual(hero.gold, 5200)
        self.assertFalse(hero.is_bot)
        self.assertTrue(hero.is_local_player)
        self.assertAlmostEqual(hero.distance_to_me, 0.0)

    def test_vtable_discrimination(self):
        """Tests that buffers with incorrect VTable signatures are rejected."""
        raw = bytearray(build_mock_hero_buffer())
        struct.pack_into("<Q", raw, 0x000, 0x12345678)
        hero = EntityParser.parse_hero(address=0x1000, raw=bytes(raw))
        self.assertIsNone(hero)

    def test_truncated_buffer_handling(self):
        """Tests that truncated buffers underflow gracefully without throwing unhandled exceptions."""
        raw = build_mock_hero_buffer()[:100]
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)
        self.assertIsNone(hero)

    def test_invalid_vitals_validation(self):
        """Tests that objects with corrupted bounds (level 0, negative hp_max) are rejected."""
        raw = build_mock_hero_buffer(level=0, hp_max=-10)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)
        self.assertIsNone(hero)

    def test_parse_tower(self):
        """Tests parsing a valid Battle.LogicTower structure."""
        raw = build_mock_tower_buffer(tower_id=2, tower_type=1, hp=4500, hp_max=5000, camp=1, pos_x=30.0, pos_y=-40.0, attack_range=8.5)
        tower = EntityParser.parse_tower(address=0x2000, raw=raw, ref_x=0.0, ref_y=0.0)
        self.assertIsNotNone(tower)
        self.assertEqual(tower.address, 0x2000)
        self.assertEqual(tower.tower_id, 2)
        self.assertEqual(tower.tower_type, 1)
        self.assertEqual(tower.hp, 4500)
        self.assertEqual(tower.hp_max, 5000)
        self.assertFalse(tower.is_dead)
        self.assertEqual(tower.camp, 1)
        self.assertAlmostEqual(tower.attack_range, 8.5)
        self.assertAlmostEqual(tower.distance_to_me, 50.0)

    def test_parse_soldier(self):
        """Tests parsing a valid Battle.LogicSoldier structure."""
        raw = build_mock_soldier_buffer(soldier_id=5, soldier_type=2, lane=3, point_index=12, hp=600, hp_max=600, camp=2)
        soldier = EntityParser.parse_soldier(address=0x3000, raw=raw)
        self.assertIsNotNone(soldier)
        self.assertEqual(soldier.soldier_id, 5)
        self.assertEqual(soldier.soldier_type, 2)
        self.assertEqual(soldier.lane, 3)
        self.assertEqual(soldier.point_index, 12)
        self.assertEqual(soldier.camp, 2)

    def test_parse_monster(self):
        """Tests parsing regular and wild monsters."""
        raw_reg = build_mock_monster_buffer(monster_id=101, hp=2000, is_wild=False)
        m_reg = EntityParser.parse_monster(address=0x4000, raw=raw_reg)
        self.assertIsNotNone(m_reg)
        self.assertFalse(m_reg.is_wild)

        raw_wild = build_mock_monster_buffer(monster_id=102, hp=1500, is_wild=True)
        m_wild = EntityParser.parse_monster(address=0x4010, raw=raw_wild)
        self.assertIsNotNone(m_wild)
        self.assertTrue(m_wild.is_wild)

    def test_parse_bullet(self):
        """Tests parsing a Battle.LogicBulletBase structure."""
        raw = build_mock_bullet_buffer(bullet_id=77, is_destroy=False, fly_distance=15.0, radius=0.8, owner_ptr=0x1000)
        bullet = EntityParser.parse_bullet(address=0x5000, raw=raw)
        self.assertIsNotNone(bullet)
        self.assertEqual(bullet.bullet_id, 77)
        self.assertFalse(bullet.is_destroy)
        self.assertAlmostEqual(bullet.fly_distance, 15.0)
        self.assertAlmostEqual(bullet.radius, 0.8)
        self.assertEqual(bullet.owner_ptr, 0x1000)

    # =========================================================================
    # P0-2: CROWD CONTROL & STATUS BITMASK TESTS
    # =========================================================================

    def test_status_mask_zero_clean(self):
        """P0-2: When status mask is 0, all status effect flags evaluate to False."""
        effects = HeroStatusEffects.from_mask(0)
        self.assertEqual(effects.raw_mask, 0)
        self.assertFalse(effects.is_dizzy)
        self.assertFalse(effects.is_freeze)
        self.assertFalse(effects.is_up)
        self.assertFalse(effects.is_controlled)
        self.assertFalse(effects.is_silent)
        self.assertFalse(effects.is_bind)
        self.assertFalse(effects.is_feared)
        self.assertFalse(effects.is_taunted)
        self.assertFalse(effects.is_charmed)
        self.assertFalse(effects.is_suppressed)
        self.assertFalse(effects.is_petrified)
        self.assertFalse(effects.is_stealthed)
        self.assertFalse(effects.is_cc_immune)

    def test_status_mask_single_dizzy_stun(self):
        """P0-2: Bit 1 (DIZZY) sets is_dizzy=True and is preserved in raw mask."""
        mask = 1 << 1  # 2
        raw = build_mock_hero_buffer(status=mask)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.status_mask, mask)
        self.assertEqual(hero.status, mask)
        self.assertTrue(hero.status_effects.is_dizzy)
        self.assertFalse(hero.status_effects.is_silent)
        self.assertFalse(hero.status_effects.is_stealthed)

    def test_status_mask_multiple_simultaneous_statuses(self):
        """P0-2: Simultaneous stun (bit 1), silence (bit 5), and stealth (bit 16) are decoded cleanly."""
        mask = (1 << 1) | (1 << 5) | (1 << 16)
        raw = build_mock_hero_buffer(status=mask)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.status_mask, mask)
        self.assertTrue(hero.status_effects.is_dizzy)
        self.assertTrue(hero.status_effects.is_silent)
        self.assertTrue(hero.status_effects.is_stealthed)
        self.assertFalse(hero.status_effects.is_bind)
        self.assertFalse(hero.status_effects.is_suppressed)

    def test_status_mask_unknown_bits_preservation(self):
        """P0-2: Unknown or high bit positions (e.g. 1 << 28) do not corrupt standard flags and remain in raw_mask."""
        mask = (1 << 6) | (1 << 28)
        raw = build_mock_hero_buffer(status=mask)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.status_mask, mask)
        self.assertTrue(hero.status_effects.is_bind)
        self.assertFalse(hero.status_effects.is_dizzy)

    # =========================================================================
    # P0-3: TARGET GRAPH & COMBAT INTERACTION TESTS
    # =========================================================================

    def test_target_graph_null_pointers(self):
        """P0-3: When combat target pointers are 0 (idle), entity references cleanly default to 0."""
        raw = build_mock_hero_buffer(target_enemy_ptr=0, attacker_ptr=0, real_enemy_ptr=0, hate_enemy_ptr=0)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.target_enemy_ptr, 0)
        self.assertEqual(hero.attacker_ptr, 0)
        self.assertEqual(hero.real_enemy_ptr, 0)
        self.assertEqual(hero.hate_enemy_ptr, 0)
        self.assertEqual(hero.attacker_id, 0)
        self.assertEqual(hero.face_lock_target_id, 0)

    def test_target_graph_valid_references(self):
        """P0-3: Valid target and attacker pointers are parsed accurately from memory."""
        ADDR_ENEMY = 0x7242670000
        ADDR_ATTACKER = 0x7242680000
        raw = build_mock_hero_buffer(
            target_enemy_ptr=ADDR_ENEMY,
            attacker_ptr=ADDR_ATTACKER,
            attacker_id=99,
            face_lock_target_id=102,
            be_attack_timestamp=54200,
            attack_timestamp=54100
        )
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.target_enemy_ptr, ADDR_ENEMY)
        self.assertEqual(hero.attacker_ptr, ADDR_ATTACKER)
        self.assertEqual(hero.attacker_id, 99)
        self.assertEqual(hero.face_lock_target_id, 102)
        self.assertEqual(hero.be_attack_timestamp, 54200)
        self.assertEqual(hero.attack_timestamp, 54100)

    def test_target_graph_distinct_semantics(self):
        """P0-3: Distinct target roles (target, real enemy, attacker, hate enemy) coexist independently."""
        ADDR_TARGET = 0x7242001000
        ADDR_REAL = 0x7242002000
        ADDR_ATTACKER = 0x7242003000
        ADDR_HATE = 0x7242004000
        raw = build_mock_hero_buffer(
            target_enemy_ptr=ADDR_TARGET,
            real_enemy_ptr=ADDR_REAL,
            attacker_ptr=ADDR_ATTACKER,
            hate_enemy_ptr=ADDR_HATE,
            stare_target_guid=888
        )
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.target_enemy_ptr, ADDR_TARGET)
        self.assertEqual(hero.real_enemy_ptr, ADDR_REAL)
        self.assertEqual(hero.attacker_ptr, ADDR_ATTACKER)
        self.assertEqual(hero.hate_enemy_ptr, ADDR_HATE)
        self.assertEqual(hero.stare_target_guid, 888)

    def test_target_graph_switching(self):
        """P0-3: Target pointer switching from Enemy A to Enemy B is reflected immediately."""
        ADDR_A = 0x7242001000
        ADDR_B = 0x7242002000

        # Tick 1: Targeting A
        raw_tick1 = build_mock_hero_buffer(target_enemy_ptr=ADDR_A)
        hero1 = EntityParser.parse_hero(address=0x1000, raw=raw_tick1)
        self.assertEqual(hero1.target_enemy_ptr, ADDR_A)

        # Tick 2: Target switched to B
        raw_tick2 = build_mock_hero_buffer(target_enemy_ptr=ADDR_B)
        hero2 = EntityParser.parse_hero(address=0x1000, raw=raw_tick2)
        self.assertEqual(hero2.target_enemy_ptr, ADDR_B)

    # =========================================================================
    # P0-4: ACTIVE PROJECTILES & KINEMATICS TESTS
    # =========================================================================

    def test_hero_kinematics_facing_and_speed(self):
        """P0-4: Tests that hero facing vector, movement heading, and speed telemetry are parsed accurately."""
        raw = build_mock_hero_buffer(
            facing_x=0.707,
            facing_y=-0.707,
            move_dir_x=0.0,
            move_dir_y=1.0,
            run_speed=365.0,
            attack_speed=1.45
        )
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertAlmostEqual(hero.facing_x, 0.707)
        self.assertAlmostEqual(hero.facing_y, -0.707)
        self.assertAlmostEqual(hero.move_dir_x, 0.0)
        self.assertAlmostEqual(hero.move_dir_y, 1.0)
        self.assertAlmostEqual(hero.run_speed, 365.0)
        self.assertAlmostEqual(hero.attack_speed, 1.45)

    def test_projectile_kinematics_and_trajectory(self):
        """P0-4: Tests that LogicDirBullet position, direction, speed, and radius are decoded cleanly."""
        ADDR_BULLET = 0x7245001000
        ADDR_OWNER = 0x724265f000
        raw = build_mock_bullet_buffer(
            bullet_id=108,
            is_destroy=False,
            fly_distance=8.5,
            radius=1.5,
            owner_ptr=ADDR_OWNER,
            pos_x=12.5,
            pos_y=-30.0,
            dir_x=0.6,
            dir_y=0.8,
            speed=18.0
        )
        bullet = EntityParser.parse_bullet(address=ADDR_BULLET, raw=raw)

        self.assertIsNotNone(bullet)
        self.assertEqual(bullet.address, ADDR_BULLET)
        self.assertEqual(bullet.bullet_id, 108)
        self.assertFalse(bullet.is_destroy)
        self.assertAlmostEqual(bullet.fly_distance, 8.5)
        self.assertAlmostEqual(bullet.radius, 1.5)
        self.assertEqual(bullet.owner_ptr, ADDR_OWNER)
        self.assertAlmostEqual(bullet.pos_x, 12.5)
        self.assertAlmostEqual(bullet.pos_y, -30.0)
        self.assertAlmostEqual(bullet.dir_x, 0.6)
        self.assertAlmostEqual(bullet.dir_y, 0.8)
        self.assertAlmostEqual(bullet.speed, 18.0)

    def test_projectile_lifecycle_state_destroyed(self):
        """P0-4: Tests that destroyed/recycled projectile state (m_IsDestory = 1) is accurately observed."""
        raw = build_mock_bullet_buffer(bullet_id=108, is_destroy=True)
        bullet = EntityParser.parse_bullet(address=0x7245001000, raw=raw)

        self.assertIsNotNone(bullet)
        self.assertTrue(bullet.is_destroy)

    # =========================================================================
    # P1-1: HERO ABILITIES & COOLDOWN TESTS
    # =========================================================================

    def test_cooldown_null_skill_comp(self):
        """P1-1: When m_SkillComp is 0, abilities evaluate to an empty HeroAbilities()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)
        self.assertFalse(hero.abilities.is_casting)
        self.assertEqual(hero.abilities.active_spell_ptr, 0)

    def test_cooldown_null_cooldown_comp(self):
        """P1-1: When m_CoolDownComp is 0, returns empty HeroAbilities()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)

    def test_cooldown_null_dict_ptr(self):
        """P1-1: When m_DicCoolInfo is 0, returns empty HeroAbilities()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)

    def test_cooldown_empty_dict(self):
        """P1-1: When cooldown dictionary count is 0, returns empty HeroAbilities()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_DICT = 0x7243002000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_cooldown_dict_buffer(count=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)

    def test_cooldown_valid_single_entry(self):
        """P1-1: Decodes a single valid cooldown entry cleanly."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_DICT = 0x7243002000
        ADDR_ENTRIES = 0x7243003000
        ADDR_DATA_1 = 0x7243004000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_cooldown_dict_buffer(entries_ptr=ADDR_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_cooldown_entries_buffer([(10810, ADDR_DATA_1)]))
        reader.write_mock_bytes(ADDR_DATA_1, build_mock_cooldown_data_buffer(
            spell_id=10810, remaining_cd_ms=2500, max_cd_ms=6000, start_time_ms=50000, is_cooling_down=True
        ))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 1)

        cd = hero.abilities.cooldowns[0]
        self.assertEqual(cd.spell_id, 10810)
        self.assertEqual(cd.remaining_cd_ms, 2500)
        self.assertEqual(cd.max_cd_ms, 6000)
        self.assertEqual(cd.start_time_ms, 50000)
        self.assertTrue(cd.is_cooling_down)
        self.assertFalse(cd.is_ready)

    def test_cooldown_multiple_entries_and_lookup(self):
        """P1-1: Decodes multiple spell cooldowns (S1, S2, Ult, Battle Spell) and verifies get_by_spell_id."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_DICT = 0x7243002000
        ADDR_ENTRIES = 0x7243003000
        ADDR_D1 = 0x7243004000
        ADDR_D2 = 0x7243004100
        ADDR_D3 = 0x7243004200
        ADDR_D4 = 0x7243004300

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_cooldown_dict_buffer(entries_ptr=ADDR_ENTRIES, count=4))
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_cooldown_entries_buffer([
            (10810, ADDR_D1),
            (10820, ADDR_D2),
            (10830, ADDR_D3),
            (20010, ADDR_D4)
        ]))

        # S1: Ready (0 ms remaining)
        reader.write_mock_bytes(ADDR_D1, build_mock_cooldown_data_buffer(spell_id=10810, remaining_cd_ms=0, max_cd_ms=5000, is_cooling_down=False))
        # S2: Active CD (3200 ms)
        reader.write_mock_bytes(ADDR_D2, build_mock_cooldown_data_buffer(spell_id=10820, remaining_cd_ms=3200, max_cd_ms=8000, is_cooling_down=True))
        # Ult: Active CD (18500 ms)
        reader.write_mock_bytes(ADDR_D3, build_mock_cooldown_data_buffer(spell_id=10830, remaining_cd_ms=18500, max_cd_ms=35000, is_cooling_down=True))
        # Battle Spell (Flicker): Ready
        reader.write_mock_bytes(ADDR_D4, build_mock_cooldown_data_buffer(spell_id=20010, remaining_cd_ms=0, max_cd_ms=120000, is_cooling_down=False))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 4)

        s1 = hero.abilities.get_by_spell_id(10810)
        self.assertIsNotNone(s1)
        self.assertTrue(s1.is_ready)
        self.assertEqual(s1.remaining_cd_ms, 0)

        s2 = hero.abilities.get_by_spell_id(10820)
        self.assertIsNotNone(s2)
        self.assertFalse(s2.is_ready)
        self.assertEqual(s2.remaining_cd_ms, 3200)

        flicker = hero.abilities.get_by_spell_id(20010)
        self.assertIsNotNone(flicker)
        self.assertTrue(flicker.is_ready)

        unknown = hero.abilities.get_by_spell_id(99999)
        self.assertIsNone(unknown)

    def test_cooldown_active_spell_casting(self):
        """P1-1: When m_pCurSpell is set, is_casting evaluates to True."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_SPELL_CAST = 0x7243999000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cur_spell_ptr=ADDR_SPELL_CAST, cooldown_comp_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertTrue(hero.abilities.is_casting)
        self.assertEqual(hero.abilities.active_spell_ptr, ADDR_SPELL_CAST)

    def test_cooldown_invalid_pointers_fail_closed(self):
        """P1-1: Corrupted or unmapped heap pointers fail closed without throwing exceptions."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_DICT = 0x7243002000
        ADDR_ENTRIES = 0x7243003000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_cooldown_dict_buffer(entries_ptr=ADDR_ENTRIES, count=1))
        # Entry points to invalid out-of-range address
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_cooldown_entries_buffer([(10810, 0x1234)]))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)

    def test_cooldown_excessive_count_rejected(self):
        """P1-1: Unreasonable dictionary count (> 32) is rejected fail-closed."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_DICT = 0x7243002000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(skill_comp_ptr=ADDR_SKILL_COMP))
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_cooldown_dict_buffer(entries_ptr=0x7243003000, count=500))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(len(hero.abilities.cooldowns), 0)

    # =========================================================================
    # P1-2: HERO EQUIPMENT & INVENTORY TESTS
    # =========================================================================

    def test_inventory_null_equip_comp(self):
        """P1-2: When m_EquipComp is 0, inventory evaluates to an empty HeroInventory()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 0)
        self.assertEqual(len(hero.inventory.items), 0)
        self.assertEqual(hero.inventory.active_slot_index, -1)
        self.assertFalse(hero.inventory.has_roam_blessing)

    def test_inventory_null_equip_list(self):
        """P1-2: When m_EquipList is 0, returns empty HeroInventory()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 0)

    def test_inventory_empty_dict(self):
        """P1-2: When EquipDictionary count is 0, returns empty HeroInventory()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(count=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 0)

    def test_inventory_valid_single_slot(self):
        """P1-2: Decodes a single valid equipment item slot cleanly."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000
        ADDR_ENTRIES = 0x7243007000
        ADDR_ITEM_1 = 0x7243008000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(entries_ptr=ADDR_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_equip_entries_buffer([(0, ADDR_ITEM_1)]))
        reader.write_mock_bytes(ADDR_ITEM_1, build_mock_equip_info_buffer(item_id=2011, price=2200))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 1)
        self.assertEqual(hero.inventory.item_ids, (2011,))
        self.assertTrue(hero.inventory.has_item(2011))
        self.assertFalse(hero.inventory.has_item(9999))

        slot0 = hero.inventory.get_slot(0)
        self.assertIsNotNone(slot0)
        self.assertEqual(slot0.slot_index, 0)
        self.assertEqual(slot0.item_id, 2011)
        self.assertEqual(slot0.price, 2200)

    def test_inventory_six_slots_full(self):
        """P1-2: Decodes a complete 6-item inventory build and validates all helper properties."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000
        ADDR_ENTRIES = 0x7243007000

        items_spec = [
            (0, 0x7243008000, 2011, 2200),  # Slot 0: Berserker's Fury
            (1, 0x7243008100, 2012, 1870),  # Slot 1: Windtalker
            (2, 0x7243008200, 2013, 3010),  # Slot 2: Blade of Despair
            (3, 0x7243008300, 2014, 2060),  # Slot 3: Malefic Roar
            (4, 0x7243008400, 2015, 2300),  # Slot 4: Wind of Nature (Active Item)
            (5, 0x7243008500, 2016, 710),   # Slot 5: Swift Boots
        ]

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT, roam_blessing=1, use_index=4))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(entries_ptr=ADDR_ENTRIES, count=6))

        entries_list = [(slot, addr) for slot, addr, _, _ in items_spec]
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_equip_entries_buffer(entries_list))

        for _, addr, item_id, price in items_spec:
            reader.write_mock_bytes(addr, build_mock_equip_info_buffer(item_id=item_id, price=price))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 6)
        self.assertEqual(hero.inventory.active_slot_index, 4)
        self.assertTrue(hero.inventory.has_roam_blessing)
        self.assertEqual(hero.inventory.roam_blessing_count, 1)

        # Check item presence
        self.assertTrue(hero.inventory.has_item(2011))
        self.assertTrue(hero.inventory.has_item(2015))
        self.assertEqual(hero.inventory.get_slot(4).item_id, 2015)
        self.assertEqual(hero.inventory.get_slot(5).price, 710)

    def test_inventory_invalid_pointers_fail_closed(self):
        """P1-2: Corrupted or unmapped heap pointers fail closed without throwing exceptions."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000
        ADDR_ENTRIES = 0x7243007000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(entries_ptr=ADDR_ENTRIES, count=1))
        # Entry points to invalid address 0x1234
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_equip_entries_buffer([(0, 0x1234)]))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 0)

    def test_inventory_excessive_count_rejected(self):
        """P1-2: Unreasonable dictionary count (> 6) is rejected fail-closed."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(entries_ptr=0x7243007000, count=50))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 0)

    def test_inventory_slot_vs_item_id_distinction(self):
        """P1-2: Proves that slot index (key 0..5) and item archetype ID (m_iEquipId) are strictly decoupled."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_DICT = 0x7243006000
        ADDR_ENTRIES = 0x7243007000
        ADDR_ITEM = 0x7243008000

        # Item placed in slot 3 (not 0) with item ID 1055
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(equip_comp_ptr=ADDR_EQUIP_COMP))
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_DICT))
        reader.write_mock_bytes(ADDR_DICT, build_mock_equip_dict_buffer(entries_ptr=ADDR_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_ENTRIES, build_mock_equip_entries_buffer([(3, ADDR_ITEM)]))
        reader.write_mock_bytes(ADDR_ITEM, build_mock_equip_info_buffer(item_id=1055, price=1500))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.inventory.item_count, 1)

        # Slot 0 must be empty; Slot 3 must contain Item 1055
        self.assertIsNone(hero.inventory.get_slot(0))
        slot3 = hero.inventory.get_slot(3)
        self.assertIsNotNone(slot3)
        self.assertEqual(slot3.slot_index, 3)
        self.assertEqual(slot3.item_id, 1055)

    # =========================================================================
    # P1-3: BUFFS, SHIELDS, MANA & COMBAT MODIFIERS TESTS
    # =========================================================================

    def test_shield_zero_shields(self):
        """P1-3: When no shield is active, shield values evaluate cleanly to 0."""
        raw = build_mock_hero_buffer(shield=0, shield_max=0, magic_shield=0, magic_shield_max=0, mech_armor_hp=0)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.shield, 0)
        self.assertEqual(hero.shield_max, 0)
        self.assertEqual(hero.magic_shield, 0)
        self.assertEqual(hero.magic_shield_max, 0)
        self.assertEqual(hero.mech_armor_hp, 0)

    def test_shield_active_primary_and_magic_shields(self):
        """P1-3: Primary shield (AdditionHp1), magic shield (AdditionHp2), and mech armor are parsed accurately."""
        raw = build_mock_hero_buffer(
            shield=850,
            shield_max=1000,
            magic_shield=450,
            magic_shield_max=500,
            mech_armor_hp=1200
        )
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.shield, 850)
        self.assertEqual(hero.shield_max, 1000)
        self.assertEqual(hero.magic_shield, 450)
        self.assertEqual(hero.magic_shield_max, 500)
        self.assertEqual(hero.mech_armor_hp, 1200)

    def test_mana_current_and_max(self):
        """P1-3: Current and maximum Mana/Energy are decoded accurately."""
        raw = build_mock_hero_buffer(mp=720, mp_max=1400)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.mp, 720)
        self.assertEqual(hero.mp_max, 1400)

    def test_invulnerability_flag(self):
        """P1-3: m_bCantBeHurt flag sets is_invulnerable=True."""
        raw = build_mock_hero_buffer(is_invulnerable=True)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertTrue(hero.is_invulnerable)

    def test_injured_shield_is_not_live_shield(self):
        """P1-3: Proves m_iInjuredShield is parsed as match metric, but live shield remains 0."""
        raw = build_mock_hero_buffer(shield=0, injured_shield=4500)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.injured_shield, 4500)
        self.assertEqual(hero.shield, 0)

    def test_buffs_null_and_empty_dict(self):
        """P1-3: Null or empty auras dictionary returns empty HeroBuffs()."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(auras_dict_ptr=0))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.buffs.count, 0)
        self.assertEqual(len(hero.buffs.buffs), 0)

    def test_buffs_valid_single_aura(self):
        """P1-3: Decodes a single active buff (e.g. Red Buff) cleanly."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_AURAS_DICT = 0x7243009000
        ADDR_AURAS_ENTRIES = 0x724300a000
        ADDR_EFFECT_1 = 0x724300b000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(auras_dict_ptr=ADDR_AURAS_DICT))
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_AURAS_ENTRIES, build_mock_auras_entries_buffer([(5001, ADDR_EFFECT_1)]))
        reader.write_mock_bytes(ADDR_EFFECT_1, build_mock_logic_effect_buffer(
            effect_id=5001, guid=991, owner_id=18, source_spell_id=10810, stack_count=2, value=40, last_update_time=12000
        ))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.buffs.count, 1)
        self.assertTrue(hero.buffs.has_effect(5001))
        self.assertFalse(hero.buffs.has_effect(9999))

        b1 = hero.buffs.get_by_effect_id(5001)
        self.assertIsNotNone(b1)
        self.assertEqual(b1.effect_id, 5001)
        self.assertEqual(b1.guid, 991)
        self.assertEqual(b1.owner_id, 18)
        self.assertEqual(b1.source_spell_id, 10810)
        self.assertEqual(b1.stack_count, 2)
        self.assertEqual(b1.value, 40)
        self.assertEqual(b1.last_update_time, 12000)

    def test_buffs_multiple_entries_and_lookups(self):
        """P1-3: Decodes multiple active buffs with stack counts and lookup helpers."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_AURAS_DICT = 0x7243009000
        ADDR_AURAS_ENTRIES = 0x724300a000
        ADDR_EFF_1 = 0x724300b000
        ADDR_EFF_2 = 0x724300b100
        ADDR_EFF_3 = 0x724300b200

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(auras_dict_ptr=ADDR_AURAS_DICT))
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=3))
        reader.write_mock_bytes(ADDR_AURAS_ENTRIES, build_mock_auras_entries_buffer([
            (5001, ADDR_EFF_1),
            (5002, ADDR_EFF_2),
            (5003, ADDR_EFF_3)
        ]))
        reader.write_mock_bytes(ADDR_EFF_1, build_mock_logic_effect_buffer(effect_id=5001, stack_count=4, source_spell_id=2001))
        reader.write_mock_bytes(ADDR_EFF_2, build_mock_logic_effect_buffer(effect_id=5002, stack_count=1, source_spell_id=2002))
        reader.write_mock_bytes(ADDR_EFF_3, build_mock_logic_effect_buffer(effect_id=5003, stack_count=1, source_spell_id=2003))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.buffs.count, 3)

        b_stack = hero.buffs.get_by_effect_id(5001)
        self.assertEqual(b_stack.stack_count, 4)

        b_spell = hero.buffs.get_by_spell_id(2002)
        self.assertIsNotNone(b_spell)
        self.assertEqual(b_spell.effect_id, 5002)

    def test_buffs_finished_effect_skipped(self):
        """P1-3: Finished/expired effect (m_bFinish == 1) is not included in active buffs."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_AURAS_DICT = 0x7243009000
        ADDR_AURAS_ENTRIES = 0x724300a000
        ADDR_EFF = 0x724300b000

        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(auras_dict_ptr=ADDR_AURAS_DICT))
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_AURAS_ENTRIES, build_mock_auras_entries_buffer([(5001, ADDR_EFF)]))
        reader.write_mock_bytes(ADDR_EFF, build_mock_logic_effect_buffer(effect_id=5001, is_finished=True))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.buffs.count, 0)

    def test_buffs_invalid_pointer_and_excessive_count_fail_closed(self):
        """P1-3: Invalid LogicEffect pointer and unreasonable count (> 32) fail closed cleanly."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x724265f000
        ADDR_AURAS_DICT = 0x7243009000
        ADDR_AURAS_ENTRIES = 0x724300a000

        # Corrupted entry pointer
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(auras_dict_ptr=ADDR_AURAS_DICT))
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_AURAS_ENTRIES, build_mock_auras_entries_buffer([(5001, 0x1234)]))

        hero = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.buffs.count, 0)

        # Excessive count
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=100))
        hero_excess = EntityParser.parse_hero(address=ADDR_HERO, raw=b"", reader=reader)
        self.assertIsNotNone(hero_excess)
        self.assertEqual(hero_excess.buffs.count, 0)

    def test_kill_bounty_value(self):
        """P1-3: Shutdown kill gold bounty is decoded accurately."""
        raw = build_mock_hero_buffer(kill_bounty=450)
        hero = EntityParser.parse_hero(address=0x1000, raw=raw)

        self.assertIsNotNone(hero)
        self.assertEqual(hero.kill_bounty, 450)

    def test_snapshot_engine_with_mock_reader(self):
        """Tests end-to-end SnapshotEngine snapshot generation with mocked memory entities."""
        reader = MockMemoryReader()

        ADDR_LOCAL = 0x724265f000
        ADDR_ALLY = 0x7242660000
        ADDR_ENEMY = 0x7242670000
        ADDR_TOWER = 0x7242680000
        ADDR_SOLDIER = 0x7242690000
        ADDR_MONSTER = 0x72426a0000
        ADDR_BULLET = 0x7245001000

        # Setup Local Player with active SkillComp, EquipComp, and Auras
        ADDR_SKILL_COMP = 0x7243000000
        ADDR_CD_COMP = 0x7243001000
        ADDR_CD_DICT = 0x7243002000
        ADDR_CD_ENTRIES = 0x7243003000
        ADDR_CD_D1 = 0x7243004000

        ADDR_EQUIP_COMP = 0x7243005000
        ADDR_EQ_DICT = 0x7243006000
        ADDR_EQ_ENTRIES = 0x7243007000
        ADDR_EQ_ITEM1 = 0x7243008000

        ADDR_AURAS_DICT = 0x7243009000
        ADDR_AURAS_ENTRIES = 0x724300a000
        ADDR_EFFECT_1 = 0x724300b000

        reader.write_mock_bytes(
            ADDR_LOCAL,
            build_mock_hero_buffer(
                hero_id=18,
                camp=1,
                pos_x=0.0,
                pos_y=0.0,
                mp=800,
                mp_max=1200,
                shield=500,
                shield_max=600,
                magic_shield=200,
                magic_shield_max=200,
                is_invulnerable=True,
                status=(1 << 16),
                target_enemy_ptr=ADDR_ENEMY,
                attacker_ptr=ADDR_ENEMY,
                facing_x=1.0,
                facing_y=0.0,
                run_speed=350.0,
                skill_comp_ptr=ADDR_SKILL_COMP,
                equip_comp_ptr=ADDR_EQUIP_COMP,
                auras_dict_ptr=ADDR_AURAS_DICT,
                kill_bounty=300
            )
        )
        # Cooldown mocks
        reader.write_mock_bytes(ADDR_SKILL_COMP, build_mock_skill_comp_buffer(cooldown_comp_ptr=ADDR_CD_COMP))
        reader.write_mock_bytes(ADDR_CD_COMP, build_mock_cooldown_comp_buffer(dict_ptr=ADDR_CD_DICT))
        reader.write_mock_bytes(ADDR_CD_DICT, build_mock_cooldown_dict_buffer(entries_ptr=ADDR_CD_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_CD_ENTRIES, build_mock_cooldown_entries_buffer([(10810, ADDR_CD_D1)]))
        reader.write_mock_bytes(ADDR_CD_D1, build_mock_cooldown_data_buffer(spell_id=10810, remaining_cd_ms=0, max_cd_ms=5000, is_cooling_down=False))

        # Equipment mocks
        reader.write_mock_bytes(ADDR_EQUIP_COMP, build_mock_equip_comp_buffer(dict_ptr=ADDR_EQ_DICT, roam_blessing=1, use_index=0))
        reader.write_mock_bytes(ADDR_EQ_DICT, build_mock_equip_dict_buffer(entries_ptr=ADDR_EQ_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_EQ_ENTRIES, build_mock_equip_entries_buffer([(0, ADDR_EQ_ITEM1)]))
        reader.write_mock_bytes(ADDR_EQ_ITEM1, build_mock_equip_info_buffer(item_id=2011, price=2200))

        # Auras mocks
        reader.write_mock_bytes(ADDR_AURAS_DICT, build_mock_auras_dict_buffer(entries_ptr=ADDR_AURAS_ENTRIES, count=1))
        reader.write_mock_bytes(ADDR_AURAS_ENTRIES, build_mock_auras_entries_buffer([(5001, ADDR_EFFECT_1)]))
        reader.write_mock_bytes(ADDR_EFFECT_1, build_mock_logic_effect_buffer(effect_id=5001, stack_count=3))

        reader.write_mock_bytes(ADDR_ALLY, build_mock_hero_buffer(hero_id=33, camp=1, pos_x=10.0, pos_y=0.0))
        reader.write_mock_bytes(
            ADDR_ENEMY,
            build_mock_hero_buffer(
                hero_id=113,
                camp=2,
                pos_x=-30.0,
                pos_y=40.0,
                status=(1 << 1),
                target_enemy_ptr=ADDR_LOCAL
            )
        )
        reader.write_mock_bytes(ADDR_TOWER, build_mock_tower_buffer(tower_id=1, camp=1, pos_x=0.0, pos_y=-10.0))
        reader.write_mock_bytes(ADDR_SOLDIER, build_mock_soldier_buffer(soldier_id=10, camp=2, pos_x=5.0, pos_y=5.0))
        reader.write_mock_bytes(ADDR_MONSTER, build_mock_monster_buffer(monster_id=200, pos_x=-20.0, pos_y=0.0))
        reader.write_mock_bytes(
            ADDR_BULLET,
            build_mock_bullet_buffer(
                bullet_id=55,
                owner_ptr=ADDR_LOCAL,
                pos_x=5.0,
                pos_y=0.0,
                dir_x=1.0,
                dir_y=0.0,
                speed=20.0
            )
        )

        engine = SnapshotEngine(reader)
        engine.set_proven_local_player_ptr(ADDR_LOCAL)

        known_addrs = [ADDR_LOCAL, ADDR_ALLY, ADDR_ENEMY, ADDR_TOWER, ADDR_SOLDIER, ADDR_MONSTER, ADDR_BULLET]
        snapshot = engine.capture_snapshot(known_entity_addrs=known_addrs)

        self.assertTrue(snapshot.in_match)
        self.assertIsNotNone(snapshot.local_player)
        self.assertEqual(snapshot.local_player.hero_id, 18)
        self.assertTrue(snapshot.local_player.is_local_player)
        self.assertTrue(snapshot.local_player.status_effects.is_stealthed)
        self.assertEqual(snapshot.local_player.target_enemy_ptr, ADDR_ENEMY)
        self.assertEqual(snapshot.local_player.attacker_ptr, ADDR_ENEMY)
        self.assertAlmostEqual(snapshot.local_player.facing_x, 1.0)
        self.assertAlmostEqual(snapshot.local_player.run_speed, 350.0)

        # P1-3 Shields, Mana, Invulnerability, Buffs, Bounty on Local Player
        self.assertEqual(snapshot.local_player.shield, 500)
        self.assertEqual(snapshot.local_player.shield_max, 600)
        self.assertEqual(snapshot.local_player.magic_shield, 200)
        self.assertEqual(snapshot.local_player.magic_shield_max, 200)
        self.assertEqual(snapshot.local_player.mp, 800)
        self.assertEqual(snapshot.local_player.mp_max, 1200)
        self.assertTrue(snapshot.local_player.is_invulnerable)
        self.assertEqual(snapshot.local_player.kill_bounty, 300)
        self.assertEqual(snapshot.local_player.buffs.count, 1)
        self.assertEqual(snapshot.local_player.buffs.buffs[0].stack_count, 3)

        # Cooldowns on Local Player
        self.assertEqual(len(snapshot.local_player.abilities.cooldowns), 1)
        self.assertEqual(snapshot.local_player.abilities.cooldowns[0].spell_id, 10810)
        self.assertTrue(snapshot.local_player.abilities.cooldowns[0].is_ready)

        # Equipment on Local Player
        self.assertEqual(snapshot.local_player.inventory.item_count, 1)
        self.assertEqual(snapshot.local_player.inventory.item_ids, (2011,))
        self.assertTrue(snapshot.local_player.inventory.has_roam_blessing)
        self.assertEqual(snapshot.local_player.inventory.active_slot_index, 0)

        # Allies vs Enemies
        self.assertEqual(len(snapshot.allies), 1)
        self.assertEqual(snapshot.allies[0].hero_id, 33)
        self.assertAlmostEqual(snapshot.allies[0].distance_to_me, 10.0)

        self.assertEqual(len(snapshot.enemies), 1)
        self.assertEqual(snapshot.enemies[0].hero_id, 113)
        self.assertTrue(snapshot.enemies[0].status_effects.is_dizzy)
        self.assertEqual(snapshot.enemies[0].target_enemy_ptr, ADDR_LOCAL)
        self.assertAlmostEqual(snapshot.enemies[0].distance_to_me, 50.0)

        # Towers, Soldiers, Monsters, Bullets
        self.assertEqual(len(snapshot.towers), 1)
        self.assertEqual(snapshot.towers[0].tower_id, 1)

        self.assertEqual(len(snapshot.soldiers), 1)
        self.assertEqual(snapshot.soldiers[0].soldier_id, 10)

        self.assertEqual(len(snapshot.monsters), 1)
        self.assertEqual(snapshot.monsters[0].monster_id, 200)

        self.assertEqual(len(snapshot.bullets), 1)
        self.assertEqual(snapshot.bullets[0].bullet_id, 55)
        self.assertEqual(snapshot.bullets[0].owner_ptr, ADDR_LOCAL)
        self.assertAlmostEqual(snapshot.bullets[0].pos_x, 5.0)
        self.assertAlmostEqual(snapshot.bullets[0].speed, 20.0)

    # =========================================================================
    # GATE 8: ENTITY IDENTITY RESOLUTION REGRESSION TESTS
    # =========================================================================

    def test_gate8_resolve_from_battle_manager(self):
        """Gate 8: Tests resolving local player pointer directly from LogicBattleManager.m_RealSelfPlayer."""
        reader = MockMemoryReader()
        ADDR_MGR = 0x7241000000
        ADDR_HERO = 0x724265f000
        ADDR_ENEMY = 0x724266f000

        reader.write_mock_bytes(ADDR_MGR, build_mock_battle_manager_buffer(real_self_player_ptr=ADDR_HERO))
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(hero_id=18, camp=1))
        reader.write_mock_bytes(ADDR_ENEMY, build_mock_hero_buffer(hero_id=70, camp=2))

        engine = SnapshotEngine(reader)
        snap = engine.capture_snapshot(
            known_entity_addrs=[ADDR_HERO, ADDR_ENEMY],
            battle_manager_addr=ADDR_MGR
        )

        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.address, ADDR_HERO)
        self.assertEqual(snap.local_player.hero_id, 18)
        self.assertTrue(snap.local_player.is_local_player)
        self.assertEqual(snap.sequence_id, 1)
        self.assertEqual(snap.frame_time_ms, 45200)
        self.assertEqual(len(snap.enemies), 1)
        self.assertEqual(snap.enemies[0].address, ADDR_ENEMY)

    def test_gate8_changing_hero_id_does_not_change_resolver_logic(self):
        """Gate 8: Proves that changing the hero ID does not change the resolver logic."""
        reader = MockMemoryReader()
        ADDR_HERO = 0x7242888000

        # User is playing Hero 102 (Fighter), not Layla (18)
        reader.write_mock_bytes(ADDR_HERO, build_mock_hero_buffer(hero_id=102, level=5, camp=2))

        engine = SnapshotEngine(reader)
        engine.set_proven_local_player_ptr(ADDR_HERO)

        snap = engine.capture_snapshot(known_entity_addrs=[ADDR_HERO])
        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.hero_id, 102)
        self.assertEqual(snap.local_player.address, ADDR_HERO)
        self.assertTrue(snap.local_player.is_local_player)

    def test_gate8_address_ordering_cannot_affect_local_player_selection(self):
        """Gate 8: Proves that memory address ordering (low vs high) cannot affect selection."""
        reader = MockMemoryReader()
        ADDR_LOW = 0x7242001000
        ADDR_MID = 0x7242005000
        ADDR_HIGH = 0x7242009000

        # Low address is enemy Hero 70, Mid is teammate Hero 33, High is local player Hero 18
        reader.write_mock_bytes(ADDR_LOW, build_mock_hero_buffer(hero_id=70, camp=1))
        reader.write_mock_bytes(ADDR_MID, build_mock_hero_buffer(hero_id=33, camp=2))
        reader.write_mock_bytes(ADDR_HIGH, build_mock_hero_buffer(hero_id=18, camp=2))

        engine = SnapshotEngine(reader)
        # Proven pointer points to the HIGHEST address in memory
        engine.set_proven_local_player_ptr(ADDR_HIGH)

        snap = engine.capture_snapshot(known_entity_addrs=[ADDR_LOW, ADDR_MID, ADDR_HIGH])
        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.address, ADDR_HIGH)
        self.assertEqual(snap.local_player.hero_id, 18)

        # Ensure low address is NOT selected as local player, but categorized as enemy
        self.assertEqual(len(snap.enemies), 1)
        self.assertEqual(snap.enemies[0].address, ADDR_LOW)

        # Ensure mid address is categorized as ally
        self.assertEqual(len(snap.allies), 1)
        self.assertEqual(snap.allies[0].address, ADDR_MID)

    def test_gate8_identical_hero_not_mistaken_for_local_player(self):
        """Gate 8: In a mirror match with identical heroes, only exact pointer matches."""
        reader = MockMemoryReader()
        ADDR_LOCAL_LAYLA = 0x7242001000
        ADDR_ENEMY_LAYLA = 0x7242002000

        # Both entities are Layla (ID 18) at Level 4 with identical max HP
        reader.write_mock_bytes(ADDR_LOCAL_LAYLA, build_mock_hero_buffer(hero_id=18, level=4, hp=2500, hp_max=2500, camp=1))
        reader.write_mock_bytes(ADDR_ENEMY_LAYLA, build_mock_hero_buffer(hero_id=18, level=4, hp=2500, hp_max=2500, camp=2))

        engine = SnapshotEngine(reader)
        engine.set_proven_local_player_ptr(ADDR_LOCAL_LAYLA)

        snap = engine.capture_snapshot(known_entity_addrs=[ADDR_LOCAL_LAYLA, ADDR_ENEMY_LAYLA])
        self.assertEqual(snap.local_player.address, ADDR_LOCAL_LAYLA)
        self.assertEqual(len(snap.enemies), 1)
        self.assertEqual(snap.enemies[0].address, ADDR_ENEMY_LAYLA)
        self.assertFalse(snap.enemies[0].is_local_player)

    def test_gate8_unproven_reference_yields_none(self):
        """Gate 8: When no game reference is proven, local_player is strictly None (UNPROVEN)."""
        reader = MockMemoryReader()
        ADDR_1 = 0x7242001000
        ADDR_2 = 0x7242002000

        reader.write_mock_bytes(ADDR_1, build_mock_hero_buffer(hero_id=70, camp=1))
        reader.write_mock_bytes(ADDR_2, build_mock_hero_buffer(hero_id=18, camp=2))

        engine = SnapshotEngine(reader)
        # No proven pointer provided
        snap = engine.capture_snapshot(known_entity_addrs=[ADDR_1, ADDR_2])

        self.assertIsNone(snap.local_player)
        # Without a local player camp, remaining combatants are not erroneously categorized as allies
        self.assertEqual(len(snap.allies), 0)
        self.assertEqual(len(snap.enemies), 2)

    def test_hero_metadata_fields(self):
        """Tests that HeroEntity initializes and holds player metadata fields cleanly."""
        hero = HeroEntity(
            address=0x7242001000,
            hero_id=18,
            level=10,
            hp=3500,
            hp_max=3500,
            is_dead=False,
            camp=1,
            pos_x=15.5,
            pos_y=-20.5,
            gold=4500,
            is_bot=False,
            is_local_player=True,
            assigned_lane=1,          # Gold Lane
            battle_spell_id=20100,    # Flicker
            emblem_id=6,              # Marksman Emblem
            player_name="Antigravity",
            rank_level=5              # Mythic
        )
        self.assertEqual(hero.assigned_lane, 1)
        self.assertEqual(hero.battle_spell_id, 20100)
        self.assertEqual(hero.emblem_id, 6)
        self.assertEqual(hero.player_name, "Antigravity")
        self.assertEqual(hero.rank_level, 5)

    def test_hero_combat_attributes_defaults_and_properties(self):
        """Tests that HeroCombatAttributes defaults cleanly and properties map correctly on HeroEntity."""
        # 1. Default creation
        hero_default = HeroEntity(
            address=0x7242001000,
            hero_id=18,
            level=1,
            hp=2500,
            hp_max=2500,
            is_dead=False,
            camp=1,
            pos_x=0.0,
            pos_y=0.0,
            gold=300,
            is_bot=False,
            is_local_player=True
        )
        self.assertEqual(hero_default.physical_defense, 0)
        self.assertEqual(hero_default.magic_defense, 0)
        self.assertEqual(hero_default.physical_attack, 0)
        self.assertEqual(hero_default.magic_power, 0)
        self.assertEqual(hero_default.cooldown_reduction, 0.0)
        self.assertEqual(hero_default.crit_rate, 0.0)

        # 2. Custom combat attributes
        custom_attrs = HeroCombatAttributes(
            physical_attack=320,
            magic_power=0,
            physical_defense=115,
            magic_defense=45,
            movement_speed=370.0,
            attack_speed=1.45,
            attack_range=6.5,
            cooldown_reduction=0.10,
            crit_rate=0.25,
            phys_penetration_flat=15,
            phys_penetration_percent=0.20,
            physical_lifesteal=0.10
        )
        hero_custom = HeroEntity(
            address=0x7242001000,
            hero_id=18,
            level=10,
            hp=3500,
            hp_max=3500,
            is_dead=False,
            camp=1,
            pos_x=0.0,
            pos_y=0.0,
            gold=4500,
            is_bot=False,
            is_local_player=True,
            combat_attributes=custom_attrs
        )
        self.assertEqual(hero_custom.physical_defense, 115)
        self.assertEqual(hero_custom.magic_defense, 45)
        self.assertEqual(hero_custom.physical_attack, 320)
        self.assertEqual(hero_custom.magic_power, 0)
        self.assertEqual(hero_custom.cooldown_reduction, 0.10)
        self.assertEqual(hero_custom.crit_rate, 0.25)
        self.assertEqual(hero_custom.combat_attributes.phys_penetration_flat, 15)
        self.assertEqual(hero_custom.combat_attributes.phys_penetration_percent, 0.20)
        self.assertEqual(hero_custom.combat_attributes.physical_lifesteal, 0.10)

    def test_decode_attributes_fail_closed(self):
        """Tests that EntityParser.decode_attributes fails closed on null or invalid pointers."""
        mock_reader = MockMemoryReader()
        attrs_null = EntityParser.decode_attributes(mock_reader, 0x0)
        self.assertEqual(attrs_null.physical_defense, 0)
        self.assertEqual(attrs_null.magic_defense, 0)

        attrs_invalid = EntityParser.decode_attributes(mock_reader, 0x999999999999)
        self.assertEqual(attrs_invalid.physical_defense, 0)

    def test_decode_attributes_valid_unpacking(self):
        """Tests that EntityParser.decode_attributes cleanly unpacks dictionary entries for PhyDef and MagDef."""
        mock_reader = MockMemoryReader()
        attr_comp_addr = 0x7242100000
        dict_addr = 0x7242101000
        entries_addr = 0x7242102000

        # AttrComp: +0x38 = dict_addr
        mock_reader.write_mock_bytes(attr_comp_addr + 0x038, struct.pack("<Q", dict_addr))

        # Dictionary: +0x18 = entries_addr, +0x20 = count (2)
        dict_buf = bytearray(0x30)
        struct.pack_into("<Q", dict_buf, 0x018, entries_addr)
        struct.pack_into("<i", dict_buf, 0x020, 2)
        mock_reader.write_mock_bytes(dict_addr, bytes(dict_buf))

        # Entries buffer: Stride = 44 bytes per entry
        # Entry 0: Key = 106 (ATTR_KIND_PHY_SHIELD), RESULT (at +36) = 142
        entry0_bytes = bytearray(44)
        struct.pack_into("<iii", entry0_bytes, 0, 1, -1, 106)  # hc=1, next=-1, key=106
        struct.pack_into("<i", entry0_bytes, 12, 106)          # AttrIncrease.id = 106
        struct.pack_into("<i", entry0_bytes, 36, 142)          # AttrIncrease.RESULT = 142

        # Entry 1: Key = 107 (ATTR_KIND_MAG_SHIELD), RESULT (at +36) = 68
        entry1_bytes = bytearray(44)
        struct.pack_into("<iii", entry1_bytes, 0, 2, -1, 107)  # hc=2, next=-1, key=107
        struct.pack_into("<i", entry1_bytes, 12, 107)          # AttrIncrease.id = 107
        struct.pack_into("<i", entry1_bytes, 36, 68)           # AttrIncrease.RESULT = 68

        mock_reader.write_mock_bytes(entries_addr + 0x20, bytes(entry0_bytes + entry1_bytes))

        decoded = EntityParser.decode_attributes(mock_reader, attr_comp_addr)
        self.assertEqual(decoded.physical_defense, 142)
        self.assertEqual(decoded.magic_defense, 68)


if __name__ == "__main__":
    unittest.main()

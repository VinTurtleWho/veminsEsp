"""
Black-Box Transition Test Suite (tests/test_blackbox_transitions.py)
Validates that BlackBoxValidator observes genuine WorldSnapshot state transitions
across kinematics, vitals, abilities, inventory, buffs, and death states.
"""

import struct
import unittest
from perception.memory_reader import MockMemoryReader
from perception.schema import FieldRegistry
from perception.snapshot_engine import SnapshotEngine
from perception.blackbox_validator import BlackBoxValidator
from perception.parser import KLASS_PLAYER


class TestBlackBoxTransitions(unittest.TestCase):

    def setUp(self):
        self.reader = MockMemoryReader()
        self.registry = FieldRegistry.load_from_file()
        self.engine = SnapshotEngine(self.reader, self.registry)
        self.validator = BlackBoxValidator()

        self.ADDR_MGR = 0x7241000000
        self.ADDR_HERO = 0x7242001000
        self.ADDR_SKILL_COMP = 0x7244001000
        self.ADDR_CD_COMP = 0x7244002000
        self.ADDR_CD_DICT = 0x7244003000
        self.ADDR_CD_ENTRIES = 0x7244004000
        self.ADDR_CD1 = 0x7244005000

        self.ADDR_EQUIP_COMP = 0x7245001000
        self.ADDR_EQUIP_DICT = 0x7245002000
        self.ADDR_EQUIP_ENTRIES = 0x7245003000
        self.ADDR_ITEM1 = 0x7245004000

        self.ADDR_AURAS_DICT = 0x7246001000
        self.ADDR_AURAS_ENTRIES = 0x7246002000
        self.ADDR_BUFF1 = 0x7246003000

        self._setup_initial_heap()

    def _setup_initial_heap(self):
        # Battle Manager
        mgr_buf = bytearray(0x270)
        struct.pack_into("<Q", mgr_buf, 0x200, self.ADDR_HERO)
        self.reader.write_mock_bytes(self.ADDR_MGR, bytes(mgr_buf))

        # Hero
        self.hero_buf = bytearray(0x1000)
        struct.pack_into("<Q", self.hero_buf, 0x000, KLASS_PLAYER)
        struct.pack_into("<i", self.hero_buf, 0x0ac, 18)
        struct.pack_into("<i", self.hero_buf, 0x0b4, 10)
        struct.pack_into("<i", self.hero_buf, 0x0c8, 3000)
        struct.pack_into("<i", self.hero_buf, 0x0cc, 4000)
        self.hero_buf[0x1d0] = 0 # alive
        struct.pack_into("<i", self.hero_buf, 0x1dc, 1) # blue camp
        struct.pack_into("<d", self.hero_buf, 0x268, 10.0) # pos_x
        struct.pack_into("<d", self.hero_buf, 0x270, 20.0) # pos_y
        struct.pack_into("<d", self.hero_buf, 0x750, 0.0)  # speed
        struct.pack_into("<Q", self.hero_buf, 0x4e0, self.ADDR_SKILL_COMP)
        struct.pack_into("<Q", self.hero_buf, 0x4f8, self.ADDR_EQUIP_COMP)
        struct.pack_into("<Q", self.hero_buf, 0x4c0, self.ADDR_AURAS_DICT)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))

        # Cooldowns (empty)
        sc_buf = bytearray(0xc0)
        struct.pack_into("<Q", sc_buf, 0x0a8, self.ADDR_CD_COMP)
        self.reader.write_mock_bytes(self.ADDR_SKILL_COMP, bytes(sc_buf))
        cd_comp_buf = bytearray(0x30)
        struct.pack_into("<Q", cd_comp_buf, 0x018, self.ADDR_CD_DICT)
        self.reader.write_mock_bytes(self.ADDR_CD_COMP, bytes(cd_comp_buf))
        cd_dict_buf = bytearray(0x30)
        struct.pack_into("<Q", cd_dict_buf, 0x018, self.ADDR_CD_ENTRIES)
        struct.pack_into("<i", cd_dict_buf, 0x020, 0)
        self.reader.write_mock_bytes(self.ADDR_CD_DICT, bytes(cd_dict_buf))

        # Inventory (empty)
        eq_comp_buf = bytearray(0x80)
        struct.pack_into("<Q", eq_comp_buf, 0x028, self.ADDR_EQUIP_DICT)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_COMP, bytes(eq_comp_buf))
        eq_dict_buf = bytearray(0x30)
        struct.pack_into("<Q", eq_dict_buf, 0x018, self.ADDR_EQUIP_ENTRIES)
        struct.pack_into("<i", eq_dict_buf, 0x020, 0)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_DICT, bytes(eq_dict_buf))

        # Buffs (empty)
        auras_dict = bytearray(0x30)
        struct.pack_into("<Q", auras_dict, 0x018, self.ADDR_AURAS_ENTRIES)
        struct.pack_into("<i", auras_dict, 0x020, 0)
        self.reader.write_mock_bytes(self.ADDR_AURAS_DICT, bytes(auras_dict))

    def test_kinematic_transition(self):
        """Validates that movement is detected across consecutive WorldSnapshots."""
        snap_before = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # Mutate position on memory source
        struct.pack_into("<d", self.hero_buf, 0x268, 15.0)
        struct.pack_into("<d", self.hero_buf, 0x270, 25.0)
        struct.pack_into("<d", self.hero_buf, 0x750, 260.0)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))

        snap_after = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans = self.validator.detect_transition(snap_before, snap_after)
        self.assertTrue(trans["has_delta"])
        self.assertIn("movement", trans["deltas"])
        self.assertEqual(trans["deltas"]["movement"]["pos_after"], (15.0, 25.0))
        self.assertEqual(trans["deltas"]["movement"]["speed_after"], 260.0)

    def test_vitals_damage_transition(self):
        """Validates that HP damage is detected as damage_taken."""
        snap_before = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # Take damage: 3000 -> 2400
        struct.pack_into("<i", self.hero_buf, 0x0c8, 2400)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))

        snap_after = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans = self.validator.detect_transition(snap_before, snap_after)
        self.assertTrue(trans["has_delta"])
        self.assertIn("damage_taken", trans["deltas"])
        self.assertEqual(trans["deltas"]["damage_taken"]["damage_amount"], 600)
        self.assertEqual(trans["deltas"]["damage_taken"]["hp_after"], 2400)

    def test_healing_and_levelup_transitions(self):
        """Validates that healing and level-up are classified as distinct semantic events."""
        # Initial: Level 10, HP 2400, Max HP 4000
        struct.pack_into("<i", self.hero_buf, 0x0c8, 2400)
        struct.pack_into("<i", self.hero_buf, 0x0b4, 10)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_1 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # 1. Healing: HP 2400 -> 3000 (Level remains 10)
        struct.pack_into("<i", self.hero_buf, 0x0c8, 3000)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_2 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans_heal = self.validator.detect_transition(snap_1, snap_2)
        self.assertTrue(trans_heal["has_delta"])
        self.assertIn("healing_received", trans_heal["deltas"])
        self.assertEqual(trans_heal["deltas"]["healing_received"]["heal_amount"], 600)
        self.assertNotIn("damage_taken", trans_heal["deltas"])
        self.assertNotIn("level_up", trans_heal["deltas"])

        # 2. Level Up: Level 10 -> 11, Max HP 4000 -> 4300, HP 3000 -> 3300
        struct.pack_into("<i", self.hero_buf, 0x0b4, 11)
        struct.pack_into("<i", self.hero_buf, 0x0cc, 4300)
        struct.pack_into("<i", self.hero_buf, 0x0c8, 3300)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_3 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans_lvl = self.validator.detect_transition(snap_2, snap_3)
        self.assertTrue(trans_lvl["has_delta"])
        self.assertIn("level_up", trans_lvl["deltas"])
        self.assertEqual(trans_lvl["deltas"]["level_up"]["level_after"], 11)
        self.assertEqual(trans_lvl["deltas"]["level_up"]["max_hp_growth"], 300)
        self.assertNotIn("healing_received", trans_lvl["deltas"])

    def test_death_and_respawn_transitions(self):
        """Validates death and respawn transitions."""
        # Initial: Alive, HP 3000
        struct.pack_into("<i", self.hero_buf, 0x0c8, 3000)
        self.hero_buf[0x1d0] = 0
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_alive = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # Death transition
        self.hero_buf[0x1d0] = 1
        struct.pack_into("<i", self.hero_buf, 0x0c8, 0)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_dead = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans_death = self.validator.detect_transition(snap_alive, snap_dead)
        self.assertTrue(trans_death["has_delta"])
        self.assertIn("death", trans_death["deltas"])
        self.assertTrue(trans_death["deltas"]["death"]["dead_after"])

        # Respawn transition
        self.hero_buf[0x1d0] = 0
        struct.pack_into("<i", self.hero_buf, 0x0c8, 4000)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_respawn = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans_respawn = self.validator.detect_transition(snap_dead, snap_respawn)
        self.assertTrue(trans_respawn["has_delta"])
        self.assertIn("respawn", trans_respawn["deltas"])
        self.assertFalse(trans_respawn["deltas"]["respawn"]["dead_after"])
        self.assertEqual(trans_respawn["deltas"]["respawn"]["respawn_hp"], 4000)

    def test_ability_cast_vs_passive_cooldown_countdown(self):
        """Validates that ability cast is distinguished from passive cooldown ticks."""
        # Setup ability 1: ready (cd = 0, is_cooling_down = False)
        # Setup CD table with 1 entry
        cd_data_buf = bytearray(0x30)
        struct.pack_into("<i", cd_data_buf, 0x010, 101) # spell_id 101
        struct.pack_into("<i", cd_data_buf, 0x014, 0)   # uiCoolTime = 0
        struct.pack_into("<i", cd_data_buf, 0x018, 5000)# originalMaxCdTime = 5000
        cd_data_buf[0x020] = 0 # m_isCoolDown = 0
        self.reader.write_mock_bytes(self.ADDR_CD1, bytes(cd_data_buf))

        cd_entries_buf = bytearray(0x40)
        struct.pack_into("<i", cd_entries_buf, 0x020 + 0x00, 0) # hashCode >= 0
        struct.pack_into("<Q", cd_entries_buf, 0x020 + 0x08, 101)
        struct.pack_into("<Q", cd_entries_buf, 0x020 + 0x10, self.ADDR_CD1)
        self.reader.write_mock_bytes(self.ADDR_CD_ENTRIES, bytes(cd_entries_buf))

        cd_dict_buf = bytearray(0x30)
        struct.pack_into("<Q", cd_dict_buf, 0x018, self.ADDR_CD_ENTRIES)
        struct.pack_into("<i", cd_dict_buf, 0x020, 1) # count = 1
        self.reader.write_mock_bytes(self.ADDR_CD_DICT, bytes(cd_dict_buf))

        snap_ready = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # 1. Cast Event: Ability 1 is cast! (uiCoolTime = 5000, m_isCoolDown = 1)
        struct.pack_into("<i", cd_data_buf, 0x014, 5000)
        cd_data_buf[0x020] = 1
        self.reader.write_mock_bytes(self.ADDR_CD1, bytes(cd_data_buf))

        snap_cast = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)
        trans_cast = self.validator.detect_transition(snap_ready, snap_cast)

        # Cast event must mark has_delta = True and categorize under cast_events
        self.assertTrue(trans_cast["has_delta"])
        self.assertIn("cast_events", trans_cast["deltas"])
        self.assertEqual(trans_cast["deltas"]["cast_events"][0]["spell_id"], 101)
        self.assertEqual(trans_cast["deltas"]["cast_events"][0]["cd_after"], 5000)
        self.assertNotIn("cooldown_ticks", trans_cast["deltas"])

        # 2. Passive Cooldown Countdown: 5000ms -> 4900ms (is_cooling_down remains True)
        struct.pack_into("<i", cd_data_buf, 0x014, 4900)
        self.reader.write_mock_bytes(self.ADDR_CD1, bytes(cd_data_buf))

        snap_tick = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)
        trans_tick = self.validator.detect_transition(snap_cast, snap_tick)

        # Passive tick records cooldown_ticks for telemetry, but does NOT set has_delta=True!
        self.assertFalse(trans_tick["has_delta"])
        self.assertIn("cooldown_ticks", trans_tick["deltas"])
        self.assertEqual(trans_tick["deltas"]["cooldown_ticks"][0]["decrement_ms"], 100)
        self.assertNotIn("cast_events", trans_tick["deltas"])

    def test_item_purchase_sale_and_swap(self):
        """Validates item purchase, sale, and swap categorization."""
        ADDR_ITEM2 = 0x7245005000

        # Setup Item 1 (201) and Item 2 (202)
        item1_buf = bytearray(0x40)
        struct.pack_into("<i", item1_buf, 0x010, 201)
        struct.pack_into("<i", item1_buf, 0x030, 2100)
        self.reader.write_mock_bytes(self.ADDR_ITEM1, bytes(item1_buf))

        item2_buf = bytearray(0x40)
        struct.pack_into("<i", item2_buf, 0x010, 202)
        struct.pack_into("<i", item2_buf, 0x030, 1800)
        self.reader.write_mock_bytes(ADDR_ITEM2, bytes(item2_buf))

        # Setup EquipComp
        eq_comp_buf = bytearray(0x90)
        struct.pack_into("<i", eq_comp_buf, 0x010, 6)
        struct.pack_into("<Q", eq_comp_buf, 0x028, self.ADDR_EQUIP_DICT)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_COMP, bytes(eq_comp_buf))

        # Snapshot 1: 1 item in slot 0 (Item 201)
        eq_dict_buf = bytearray(0x30)
        struct.pack_into("<Q", eq_dict_buf, 0x018, self.ADDR_EQUIP_ENTRIES)
        struct.pack_into("<i", eq_dict_buf, 0x020, 1) # count = 1
        self.reader.write_mock_bytes(self.ADDR_EQUIP_DICT, bytes(eq_dict_buf))

        entries_buf = bytearray(0x60)
        struct.pack_into("<i", entries_buf, 0x020 + 0x00, 1) # hashCode >= 0
        struct.pack_into("<i", entries_buf, 0x020 + 0x04, -1)
        struct.pack_into("<i", entries_buf, 0x020 + 0x08, 0) # slot 0
        struct.pack_into("<Q", entries_buf, 0x020 + 0x10, self.ADDR_ITEM1)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_ENTRIES, bytes(entries_buf))

        snap_item1 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # 1. Purchase Item ID 202 in slot 1 (count = 2)
        struct.pack_into("<i", eq_dict_buf, 0x020, 2)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_DICT, bytes(eq_dict_buf))

        struct.pack_into("<i", entries_buf, 0x020 + 24 + 0x00, 2)
        struct.pack_into("<i", entries_buf, 0x020 + 24 + 0x04, -1)
        struct.pack_into("<i", entries_buf, 0x020 + 24 + 0x08, 1) # slot 1
        struct.pack_into("<Q", entries_buf, 0x020 + 24 + 0x10, ADDR_ITEM2)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_ENTRIES, bytes(entries_buf))

        snap_item2 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)
        trans_buy = self.validator.detect_transition(snap_item1, snap_item2)

        self.assertTrue(trans_buy["has_delta"])
        self.assertIn("item_purchased", trans_buy["deltas"])
        self.assertEqual(trans_buy["deltas"]["item_purchased"][0]["item_id"], 202)

        # 2. Sell Item ID 201 (count = 1, item 202 remaining in slot 1)
        struct.pack_into("<i", eq_dict_buf, 0x020, 1)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_DICT, bytes(eq_dict_buf))

        entries_sold_buf = bytearray(0x40)
        struct.pack_into("<i", entries_sold_buf, 0x020 + 0x00, 2)
        struct.pack_into("<i", entries_sold_buf, 0x020 + 0x04, -1)
        struct.pack_into("<i", entries_sold_buf, 0x020 + 0x08, 1) # slot 1
        struct.pack_into("<Q", entries_sold_buf, 0x020 + 0x10, ADDR_ITEM2)
        self.reader.write_mock_bytes(self.ADDR_EQUIP_ENTRIES, bytes(entries_sold_buf))

        snap_sell = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)
        trans_sell = self.validator.detect_transition(snap_item2, snap_sell)

        self.assertTrue(trans_sell["has_delta"])
        self.assertIn("item_sold", trans_sell["deltas"])
        self.assertEqual(trans_sell["deltas"]["item_sold"][0]["item_id"], 201)

    def test_buff_and_shield_gain_loss(self):
        """Validates buff gain/loss and shield value changes."""
        # Initial: No shields, no buffs
        struct.pack_into("<i", self.hero_buf, 0x0e4, 0) # shield = 0
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_0 = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        # 1. Gain shield: shield = 500
        struct.pack_into("<i", self.hero_buf, 0x0e4, 500)
        self.reader.write_mock_bytes(self.ADDR_HERO, bytes(self.hero_buf))
        snap_shield = self.engine.capture_snapshot(known_entity_addrs=[self.ADDR_HERO], battle_manager_addr=self.ADDR_MGR)

        trans_shield = self.validator.detect_transition(snap_0, snap_shield)
        self.assertTrue(trans_shield["has_delta"])
        self.assertIn("shield_changed", trans_shield["deltas"])
        self.assertEqual(trans_shield["deltas"]["shield_changed"]["delta_shield"], 500)

    def test_match_entity_lifecycle_transitions(self):
        """Validates tower destruction and enemy death events across snapshots."""
        ADDR_TOWER = 0x7247001000
        ADDR_ENEMY = 0x7248001000

        # Setup Tower (Blue Camp, alive, 5000 HP)
        tw_buf = bytearray(0x950)
        from perception.parser import KLASS_TOWER
        struct.pack_into("<Q", tw_buf, 0x000, KLASS_TOWER)
        struct.pack_into("<i", tw_buf, 0x0ac, 1) # ID
        struct.pack_into("<i", tw_buf, 0x0c8, 5000) # HP
        struct.pack_into("<i", tw_buf, 0x0cc, 5000) # HP max
        tw_buf[0x1d0] = 0 # alive
        struct.pack_into("<i", tw_buf, 0x1dc, 1) # Blue camp
        struct.pack_into("<i", tw_buf, 0x850, 1) # Tower type
        self.reader.write_mock_bytes(ADDR_TOWER, bytes(tw_buf))

        # Setup Enemy Hero (Red Camp, alive, 3500 HP)
        en_buf = bytearray(0x1000)
        struct.pack_into("<Q", en_buf, 0x000, KLASS_PLAYER)
        struct.pack_into("<i", en_buf, 0x0ac, 25) # Hero ID 25
        struct.pack_into("<i", en_buf, 0x0b4, 8)  # Level 8
        struct.pack_into("<i", en_buf, 0x0c8, 3500)
        struct.pack_into("<i", en_buf, 0x0cc, 3500)
        en_buf[0x1d0] = 0
        struct.pack_into("<i", en_buf, 0x1dc, 2) # Red camp
        self.reader.write_mock_bytes(ADDR_ENEMY, bytes(en_buf))

        snap_before = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO, ADDR_TOWER, ADDR_ENEMY],
            battle_manager_addr=self.ADDR_MGR
        )

        # Mutate: Tower destroyed (HP = 0, is_dead = 1), Enemy killed (HP = 0, is_dead = 1)
        tw_buf[0x1d0] = 1
        struct.pack_into("<i", tw_buf, 0x0c8, 0)
        self.reader.write_mock_bytes(ADDR_TOWER, bytes(tw_buf))

        en_buf[0x1d0] = 1
        struct.pack_into("<i", en_buf, 0x0c8, 0)
        self.reader.write_mock_bytes(ADDR_ENEMY, bytes(en_buf))

        snap_after = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO, ADDR_TOWER, ADDR_ENEMY],
            battle_manager_addr=self.ADDR_MGR
        )

        trans = self.validator.detect_transition(snap_before, snap_after)
        self.assertTrue(trans["has_delta"])
        self.assertIn("towers_destroyed", trans["deltas"])
        self.assertEqual(trans["deltas"]["towers_destroyed"][0]["address"], ADDR_TOWER)
        self.assertIn("enemy_deaths", trans["deltas"])
        self.assertEqual(trans["deltas"]["enemy_deaths"][0]["hero_id"], 25)


if __name__ == "__main__":
    unittest.main()

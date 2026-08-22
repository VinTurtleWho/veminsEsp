"""
Gate 8 Multi-Hero Identity & Black-Box Validation Test Suite (tests/test_identity_gate.py)
Proves that SnapshotEngine strictly binds local_player from LogicBattleManager.m_RealSelfPlayer (+0x200),
never falls back to heuristic hero scanning, and correctly partitions allies and enemies.
"""

import struct
import unittest
from perception.memory_reader import MockMemoryReader
from perception.schema import FieldRegistry
from perception.snapshot_engine import SnapshotEngine
from perception.blackbox_validator import BlackBoxValidator
from perception.parser import KLASS_PLAYER


class TestIdentityGate(unittest.TestCase):

    def setUp(self):
        self.reader = MockMemoryReader()
        self.registry = FieldRegistry.load_from_file()
        self.engine = SnapshotEngine(self.reader, self.registry)
        self.validator = BlackBoxValidator()

        self.ADDR_MGR = 0x7241000000
        self.ADDR_HERO_A = 0x7242001000 # Layla (Camp 1, Ally)
        self.ADDR_HERO_B = 0x7242002000 # Tigreal (Camp 1, Ally)
        self.ADDR_HERO_C = 0x7242003000 # Chou (Camp 2, Enemy)

        # Setup 3 Heroes
        for addr, hid, camp in [(self.ADDR_HERO_A, 18, 1), (self.ADDR_HERO_B, 6, 1), (self.ADDR_HERO_C, 26, 2)]:
            buf = bytearray(0x1000)
            struct.pack_into("<Q", buf, 0x000, KLASS_PLAYER)
            struct.pack_into("<i", buf, 0x0ac, hid)
            struct.pack_into("<i", buf, 0x0b4, 10)
            struct.pack_into("<i", buf, 0x0c8, 3000)
            struct.pack_into("<i", buf, 0x0cc, 4000)
            struct.pack_into("<i", buf, 0x1dc, camp)
            struct.pack_into("<d", buf, 0x268, 10.0)
            struct.pack_into("<d", buf, 0x270, 20.0)
            self.reader.write_mock_bytes(addr, bytes(buf))

        # Setup Battle Manager with m_RealSelfPlayer = Hero A
        mgr_buf = bytearray(0x270)
        struct.pack_into("<Q", mgr_buf, 0x200, self.ADDR_HERO_A)
        self.reader.write_mock_bytes(self.ADDR_MGR, bytes(mgr_buf))

    def test_gate8_authoritative_resolution(self):
        """Proves local_player binds strictly to Hero A when +0x200 points to Hero A."""
        snap = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO_A, self.ADDR_HERO_B, self.ADDR_HERO_C],
            battle_manager_addr=self.ADDR_MGR
        )

        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.address, self.ADDR_HERO_A)
        self.assertEqual(snap.local_player.hero_id, 18)
        self.assertTrue(snap.local_player.is_local_player)

        # Allies should contain Hero B only
        self.assertEqual(len(snap.allies), 1)
        self.assertEqual(snap.allies[0].address, self.ADDR_HERO_B)
        self.assertFalse(snap.allies[0].is_local_player)

        # Enemies should contain Hero C only
        self.assertEqual(len(snap.enemies), 1)
        self.assertEqual(snap.enemies[0].address, self.ADDR_HERO_C)
        self.assertFalse(snap.enemies[0].is_local_player)

        # Black-Box Validator verification
        val_res = self.validator.validate_snapshot(snap)
        self.assertTrue(val_res["valid"], f"Validation errors: {val_res.get('errors')}")

    def test_gate8_pointer_switch(self):
        """Proves local_player dynamically switches to Hero B when +0x200 is updated."""
        mgr_buf = bytearray(0x270)
        struct.pack_into("<Q", mgr_buf, 0x200, self.ADDR_HERO_B) # Switch to Hero B
        self.reader.write_mock_bytes(self.ADDR_MGR, bytes(mgr_buf))

        snap = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO_A, self.ADDR_HERO_B, self.ADDR_HERO_C],
            battle_manager_addr=self.ADDR_MGR
        )

        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.address, self.ADDR_HERO_B)
        self.assertEqual(snap.local_player.hero_id, 6) # Tigreal
        self.assertTrue(snap.local_player.is_local_player)

        # Allies should now contain Hero A
        self.assertEqual(len(snap.allies), 1)
        self.assertEqual(snap.allies[0].address, self.ADDR_HERO_A)

        # Enemies still Hero C
        self.assertEqual(len(snap.enemies), 1)
        self.assertEqual(snap.enemies[0].address, self.ADDR_HERO_C)

        val_res = self.validator.validate_snapshot(snap)
        self.assertTrue(val_res["valid"])

    def test_gate8_fallback_to_local_player_logic(self):
        """Proves fallback to m_LocalPlayerLogic (+0x0a0) when +0x200 is NULL."""
        mgr_buf = bytearray(0x270)
        struct.pack_into("<Q", mgr_buf, 0x200, 0) # +0x200 is NULL
        struct.pack_into("<Q", mgr_buf, 0x0a0, self.ADDR_HERO_A) # +0x0a0 is Hero A
        self.reader.write_mock_bytes(self.ADDR_MGR, bytes(mgr_buf))

        snap = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO_A, self.ADDR_HERO_B, self.ADDR_HERO_C],
            battle_manager_addr=self.ADDR_MGR
        )

        self.assertIsNotNone(snap.local_player)
        self.assertEqual(snap.local_player.address, self.ADDR_HERO_A)
        self.assertEqual(snap.local_player.hero_id, 18)
        self.assertTrue(snap.local_player.is_local_player)

    def test_gate8_orchestrator_fails_closed_when_manager_not_found(self):
        """Proves ProductionPerceptionOrchestrator returns local_player=None and in_match=False when manager is absent."""
        from perception.orchestrator import ProductionPerceptionOrchestrator

        empty_reader = MockMemoryReader()
        orchestrator = ProductionPerceptionOrchestrator(empty_reader)
        snap = orchestrator.get_world_snapshot()

        self.assertIsNone(snap.local_player)
        self.assertFalse(snap.in_match)
        self.assertEqual(len(snap.allies), 0)
        self.assertEqual(len(snap.enemies), 0)

    def test_gate8_corrupted_self_pointer_fails_closed(self):
        """Proves that invalid self pointers (e.g. non-player entity or zero) fail closed to None."""
        mgr_buf = bytearray(0x270)
        struct.pack_into("<Q", mgr_buf, 0x200, 0xdeadbeef) # Corrupted pointer
        struct.pack_into("<Q", mgr_buf, 0x0a0, 0)
        self.reader.write_mock_bytes(self.ADDR_MGR, bytes(mgr_buf))

        snap = self.engine.capture_snapshot(
            known_entity_addrs=[self.ADDR_HERO_B, self.ADDR_HERO_C],
            battle_manager_addr=self.ADDR_MGR
        )

        self.assertIsNone(snap.local_player)


if __name__ == "__main__":
    unittest.main()

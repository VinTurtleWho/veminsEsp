"""
Unit Test Suite for Schema, GenericFieldReader, and ProofEngine.
Tests binary decoding, owning-class validation, confidence filtering, and malformed reads.
"""

import struct
import unittest

from perception.memory_reader import MockMemoryReader
from perception.proofing.proof_engine import ProofEngine
from perception.schema import ClassSchema, FieldDefinition, FieldRegistry, GenericFieldReader


class TestSchemaAndGenericReader(unittest.TestCase):

    def setUp(self):
        self.registry = FieldRegistry.load_from_file()

    def test_schema_loaded(self):
        """Tests that field_schema.json is loaded with all 6 core classes."""
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicPlayer"))
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicTower"))
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicSoldier"))
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicMonster"))
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicWildMonster"))
        self.assertIsNotNone(self.registry.get_by_name("Battle.LogicBulletBase"))

        # VTable lookups
        self.assertIsNotNone(self.registry.get_by_vtable(0x742002fdf8))
        self.assertIsNotNone(self.registry.get_by_vtable(0x74201ccee8))
        self.assertIsNotNone(self.registry.get_by_vtable(0x741ff9d098))
        self.assertIsNotNone(self.registry.get_by_vtable(0x741ff3bec0))
        self.assertIsNotNone(self.registry.get_by_vtable(0x741ff3ad80))
        self.assertIsNotNone(self.registry.get_by_vtable(0x7421113bb0))

    def test_generic_field_reader_proven_policy(self):
        """Tests reading a mock Hero buffer with GenericFieldReader under PROVEN policy."""
        reader = MockMemoryReader()
        addr = 0x724265f000
        
        # Build mock hero buffer
        buf = bytearray(0xba0)
        struct.pack_into("<Q", buf, 0x000, 0x742002fdf8) # VTable
        buf[0x05c] = 1 # IsPlayer
        struct.pack_into("<i", buf, 0x0ac, 18) # Hero ID
        struct.pack_into("<i", buf, 0x0b4, 8) # Level
        struct.pack_into("<i", buf, 0x0c8, 2800) # HP
        struct.pack_into("<i", buf, 0x0cc, 3200) # HP Max
        buf[0x1d0] = 0 # IsDead
        struct.pack_into("<i", buf, 0x1dc, 1) # Camp
        struct.pack_into("<d", buf, 0x268, -15.5) # PosX
        struct.pack_into("<d", buf, 0x270, 22.0) # PosY
        struct.pack_into("<i", buf, 0x858, 3600) # Gold
        buf[0xb9a] = 0 # IsBot

        reader.write_mock_bytes(addr, bytes(buf))

        generic_reader = GenericFieldReader(reader, self.registry)
        entity = generic_reader.read_entity(addr, confidence_policy="PROVEN")

        self.assertIsNotNone(entity)
        self.assertEqual(entity["address"], addr)
        self.assertEqual(entity["_class"], "Battle.LogicPlayer")
        self.assertEqual(entity["hero_id"], 18)
        self.assertEqual(entity["level"], 8)
        self.assertEqual(entity["hp"], 2800)
        self.assertEqual(entity["hp_max"], 3200)
        self.assertFalse(entity["is_dead"])
        self.assertEqual(entity["camp"], 1)
        self.assertAlmostEqual(entity["pos_x"], -15.5)
        self.assertAlmostEqual(entity["pos_y"], 22.0)
        self.assertEqual(entity["gold"], 3600)
        self.assertFalse(entity["is_bot"])

    def test_generic_field_reader_validated_policy_decodes_extended_fields(self):
        """Tests that VALIDATED confidence policy successfully decodes extended fields."""
        reader = MockMemoryReader()
        addr = 0x724265f000
        
        buf = bytearray(0xba0)
        struct.pack_into("<Q", buf, 0x000, 0x742002fdf8) # VTable
        buf[0x05c] = 1 # IsPlayer
        struct.pack_into("<i", buf, 0x0ac, 18)
        struct.pack_into("<i", buf, 0x0b4, 10)
        struct.pack_into("<i", buf, 0x0c8, 3500)
        struct.pack_into("<i", buf, 0x0cc, 3500)
        buf[0x1d0] = 0
        struct.pack_into("<i", buf, 0x1dc, 2)
        struct.pack_into("<i", buf, 0x1e4, 5) # status
        buf[0x21c] = 1 # in_battle
        struct.pack_into("<d", buf, 0x268, 12.0)
        struct.pack_into("<d", buf, 0x270, -18.0)
        struct.pack_into("<d", buf, 0x340, 25.0) # born_pos_x
        struct.pack_into("<d", buf, 0x348, 10.0) # born_pos_y
        struct.pack_into("<d", buf, 0x868, 15400.0) # hurt_total_value
        struct.pack_into("<i", buf, 0x8c8, 500) # injured_shield
        struct.pack_into("<i", buf, 0x998, 3) # kill_tower_times

        reader.write_mock_bytes(addr, bytes(buf))

        generic_reader = GenericFieldReader(reader, self.registry)
        
        # 1. Under PROVEN policy: status is included (proven in P0-2), while in_battle and hurt_total_value are excluded
        proven_entity = generic_reader.read_entity(addr, confidence_policy="PROVEN")
        self.assertIn("status", proven_entity)
        self.assertNotIn("in_battle", proven_entity)
        self.assertNotIn("hurt_total_value", proven_entity)

        # 2. Under VALIDATED policy: extended fields are included
        val_entity = generic_reader.read_entity(addr, confidence_policy="VALIDATED")
        self.assertIn("status", val_entity)
        self.assertEqual(val_entity["status"], 5)
        self.assertTrue(val_entity["in_battle"])
        self.assertAlmostEqual(val_entity["born_pos_x"], 25.0)
        self.assertAlmostEqual(val_entity["born_pos_y"], 10.0)
        self.assertAlmostEqual(val_entity["hurt_total_value"], 15400.0)
        self.assertEqual(val_entity["injured_shield"], 500)
        self.assertEqual(val_entity["kill_tower_times"], 3)

    def test_generic_field_reader_rejects_corrupted_vtable(self):
        """Tests that unknown VTable signatures return None."""
        reader = MockMemoryReader()
        addr = 0x10000000
        buf = bytearray(0x100)
        struct.pack_into("<Q", buf, 0x000, 0xdeadbeef)
        reader.write_mock_bytes(addr, bytes(buf))

        generic_reader = GenericFieldReader(reader, self.registry)
        entity = generic_reader.read_entity(addr)
        self.assertIsNone(entity)

    def test_dynamic_vtable_registration_with_valid_il2cpp_descriptor(self):
        """Tests that unmapped runtime VTables are accepted only after verifying IL2CPP class descriptor."""
        reader = MockMemoryReader()
        vtable_addr = 0x7890001000
        p_name = 0x7890002000
        p_ns = 0x7890002020
        entity_addr = 0x7890005000

        # 1. Setup C-strings in mock memory
        reader.write_mock_bytes(p_name, b"LogicPlayer\x00")
        reader.write_mock_bytes(p_ns, b"Battle\x00")

        # 2. Setup Il2CppClass descriptor at vtable_addr
        desc_buf = bytearray(0x40)
        struct.pack_into("<QQ", desc_buf, 0x10, p_name, p_ns)
        reader.write_mock_bytes(vtable_addr, bytes(desc_buf))

        # 3. Setup entity instance buffer
        entity_buf = bytearray(0xba0)
        struct.pack_into("<Q", entity_buf, 0x000, vtable_addr)
        entity_buf[0x05c] = 1 # IsPlayer
        struct.pack_into("<i", entity_buf, 0x0ac, 77) # Hero ID
        struct.pack_into("<i", entity_buf, 0x0b4, 12) # Level
        struct.pack_into("<i", entity_buf, 0x0c8, 4500) # HP
        struct.pack_into("<i", entity_buf, 0x0cc, 4500) # HP Max
        struct.pack_into("<i", entity_buf, 0x1dc, 1) # Camp
        reader.write_mock_bytes(entity_addr, bytes(entity_buf))

        # 4. Read entity using a fresh registry without pre-cached vtable_addr
        fresh_registry = FieldRegistry.load_from_file()
        self.assertIsNone(fresh_registry.get_by_vtable(vtable_addr))

        generic_reader = GenericFieldReader(reader, fresh_registry)
        entity = generic_reader.read_entity(entity_addr)

        # 5. Verify successful descriptor verification & dynamic registration
        self.assertIsNotNone(entity)
        self.assertEqual(entity["_class"], "Battle.LogicPlayer")
        self.assertEqual(entity["hero_id"], 77)
        self.assertEqual(entity["level"], 12)
        self.assertIsNotNone(fresh_registry.get_by_vtable(vtable_addr))

    def test_dynamic_vtable_registration_rejects_unverified_garbage(self):
        """Tests that arbitrary unverified memory pointers are rejected and not registered as VTables."""
        reader = MockMemoryReader()
        fake_vtable = 0x7890099000
        entity_addr = 0x7890095000

        # Entity points to fake_vtable where no valid descriptor exists (all zeros/unmapped)
        entity_buf = bytearray(0x100)
        struct.pack_into("<Q", entity_buf, 0x000, fake_vtable)
        reader.write_mock_bytes(entity_addr, bytes(entity_buf))

        fresh_registry = FieldRegistry.load_from_file()
        generic_reader = GenericFieldReader(reader, fresh_registry)

        # Should fail closed
        entity = generic_reader.read_entity(entity_addr, expected_class="Battle.LogicPlayer")
        self.assertIsNone(entity)
        self.assertIsNone(fresh_registry.get_by_vtable(fake_vtable))

    def test_orchestrator_static_rva_resolution_and_lifecycle(self):
        """Tests deterministic static RVA 0x10c0774 resolution and state invalidation in Orchestrator."""
        from perception.orchestrator import ProductionPerceptionOrchestrator

        reader = MockMemoryReader()
        liblogic_base = 0x737158e000
        rva_static = 0x10c0774
        addr_static = liblogic_base + rva_static
        got_target = 0x7372001000
        klass_ptr = 0x7373001000
        sf_ptr = 0x7374001000
        mgr_addr = 0x7375001000

        # 1. Encode ADRP + LDR instructions at addr_static
        # Target: got_target (0x7372001000)
        # PC at ADRP: addr_static + 0x10 = 0x737264e784
        pc_adrp = addr_static + 0x10
        page_pc = pc_adrp & ~0xfff
        page_target = got_target & ~0xfff
        page_offset = (page_target - page_pc) >> 12
        immlo = page_offset & 0x3
        immhi = (page_offset >> 2) & 0x7ffff
        insn_adrp = 0x90000008 | (immlo << 29) | (immhi << 5)

        ldr_offset = got_target & 0xfff
        imm12 = ldr_offset // 8
        insn_ldr = 0xf9400100 | (imm12 << 10) # LDR X0, [X8, #ldr_offset]

        code_buf = bytearray(0x20)
        struct.pack_into("<II", code_buf, 0x10, insn_adrp, insn_ldr)
        reader.write_mock_bytes(addr_static, bytes(code_buf))

        # 2. GOT entry -> klass_ptr
        reader.write_mock_bytes(got_target, struct.pack("<Q", klass_ptr))

        # 3. Il2CppClass -> static_fields (+0xb0)
        klass_buf = bytearray(0xc0)
        struct.pack_into("<Q", klass_buf, 0xb0, sf_ptr)
        reader.write_mock_bytes(klass_ptr, bytes(klass_buf))

        # 4. static_fields + 0x00 -> LogicBattleManager*
        reader.write_mock_bytes(sf_ptr, struct.pack("<Q", mgr_addr))

        # 5. LogicBattleManager + 0x180 -> _m_eState = 2 (InBattle)
        mgr_buf = bytearray(0x200)
        struct.pack_into("<i", mgr_buf, 0x180, 2)
        reader.write_mock_bytes(mgr_addr, bytes(mgr_buf))

        # Test deterministic resolution
        orchestrator = ProductionPerceptionOrchestrator(reader)
        resolved_mgr = orchestrator.discover_battle_manager()
        self.assertEqual(resolved_mgr, mgr_addr)

        # Test cached access
        self.assertEqual(orchestrator.cached_battle_manager_addr, mgr_addr)

        # 6. Test match lifecycle invalidation: set _m_eState = 3 (Victory/Defeat)
        struct.pack_into("<i", mgr_buf, 0x180, 3)
        reader.write_mock_bytes(mgr_addr, bytes(mgr_buf))

        # Calling discover_battle_manager should detect match finished and return 0 (fail-closed)
        resolved_after_end = orchestrator.discover_battle_manager()
        self.assertEqual(resolved_after_end, 0)
        self.assertEqual(orchestrator.cached_battle_manager_addr, 0)


if __name__ == "__main__":
    unittest.main()

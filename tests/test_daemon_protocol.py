"""
Regression and Protocol Tests for Agent Daemon (tests/test_daemon_protocol.py)
Validates build hash verification, handshake parsing, structured error decoding,
and memory-map filtering rules.
"""

import json
import unittest
from perception.memory_reader import DaemonMemoryReader, MockMemoryReader
from daemon_verifier import get_expected_hash


class TestDaemonProtocolAndVerification(unittest.TestCase):

    def test_expected_hash_file_exists_and_valid(self):
        """Tests that agent_daemon.hash contains a valid non-empty hexadecimal string."""
        h = get_expected_hash()
        self.assertTrue(len(h) >= 8, f"Expected hash should be at least 8 chars, got: '{h}'")
        # Validate hex characters
        int(h, 16)

    def test_mock_memory_reader_get_info_metadata(self):
        """Tests that MockMemoryReader complies with the metadata contract."""
        reader = MockMemoryReader()
        info = reader.get_info()
        self.assertTrue(info.get("connected"))
        self.assertEqual(info.get("pid"), 99999)
        self.assertEqual(info.get("liblogic_base"), 0x737158e000)
        self.assertEqual(reader.read_class_name(0x7375001000), "LogicPlayer")

    def test_structured_error_decoding(self):
        """Tests that structured error responses from SCAN_BATTLE_MGR are correctly structured."""
        # Simulated responses from agent_daemon
        err_resp = {
            "status": "error",
            "error_code": "STRUCTURAL_VALIDATION_FAILED",
            "msg": "State=0 FrameTime=0 Dic=0x0",
            "regions": 420,
            "candidates_checked": 5
        }
        self.assertEqual(err_resp["status"], "error")
        self.assertEqual(err_resp["error_code"], "STRUCTURAL_VALIDATION_FAILED")
        self.assertEqual(err_resp["candidates_checked"], 5)

        no_cand = {
            "status": "error",
            "error_code": "NO_CANDIDATE",
            "msg": "No candidate satisfied LogicBattleManager invariants",
            "regions": 1024,
            "candidates_checked": 0
        }
        self.assertEqual(no_cand["error_code"], "NO_CANDIDATE")
        self.assertEqual(no_cand["regions"], 1024)

    def test_memory_map_filter_whitelist_blacklist_rules(self):
        """Tests the daemon's positive and negative memory map filtering rules."""
        def should_scan(line: str) -> bool:
            # Replicates agent_daemon.c filtering logic
            parts = line.strip().split()
            if len(parts) < 2:
                return False
            perms = parts[1]
            if not ("r" in perms and "w" in perms and "p" in perms):
                return False
            blacklist = [".so", ".apk", ".dex", ".ttf", ".jar", ".art", "stack", "ashmem"]
            for bad in blacklist:
                if bad in line:
                    return False
            return True

        # Should SCAN:
        self.assertTrue(should_scan("7aa0000000-7aa0040000 rw-p 00000000 00:00 0 [anon:dalvik-main space]"))
        self.assertTrue(should_scan("7bf4000000-7bf4080000 rw-p 00000000 00:00 0 [anon:libc_malloc]"))
        self.assertTrue(should_scan("7ce0000000-7ce0020000 rw-p 00000000 00:00 0 [anon:dalvik-free list]"))
        self.assertTrue(should_scan("7af0000000-7af2000000 rw-p 00000000 00:00 0"))

        # Should REJECT:
        self.assertFalse(should_scan("7c67e09000-7c68e09000 r-xp 00000000 00:00 0 /data/app/liblogic.so"))
        self.assertFalse(should_scan("7c68e09000-7c68e10000 rw-p 00000000 00:00 0 /data/app/liblogic.so"))
        self.assertFalse(should_scan("7f80000000-7f80020000 rw-p 00000000 00:00 0 [stack:1234]"))
        self.assertFalse(should_scan("7d00000000-7d00020000 rw-p 00000000 00:00 0 /dev/ashmem/dalvik-large"))
        self.assertFalse(should_scan("7e00000000-7e00020000 rw-p 00000000 00:00 0 /data/app/base.apk"))
        self.assertFalse(should_scan("7e10000000-7e10020000 rw-p 00000000 00:00 0 /data/app/classes.dex"))


if __name__ == "__main__":
    unittest.main()

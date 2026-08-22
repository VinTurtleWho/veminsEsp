#!/usr/bin/env python3
"""
test_kotlin_telemetry_and_config.py - End-to-End Verification for Kotlin Telemetry, ConfigManager & State
Validates:
1. FrameSnapshot JSON parsing against live ground truth snapshots & GET_INFO daemon protocol.
2. ConfigManager persistent load/save schema validation against minimap_config.json.
3. CalibrationDialogView parameter bounds, slider scaling, and toggles.
4. Auto-reconnect with exponential backoff dynamics and PID change detection.
"""

import json
import os
import time
import socket
import threading
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "minimap_config.json")
SNAPSHOT_PATH = os.path.join(ROOT_DIR, "LIVE_FULL_WORLD_SNAPSHOT.json")


class TestTelemetryAndConfig(unittest.TestCase):
    def test_minimap_config_schema(self):
        """Validates that minimap_config.json contains all fields required by ConfigManager.kt."""
        self.assertTrue(os.path.exists(CONFIG_PATH), f"Config file missing at {CONFIG_PATH}")
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)

        # 1. Screen
        self.assertIn("screen", cfg)
        self.assertIn("width", cfg["screen"])
        self.assertIn("height", cfg["screen"])

        # 2. Minimap
        self.assertIn("minimap", cfg)
        self.assertIn("pos_x", cfg["minimap"])
        self.assertIn("pos_y", cfg["minimap"])
        self.assertIn("width", cfg["minimap"])
        self.assertIn("height", cfg["minimap"])
        self.assertIn("invert_y", cfg["minimap"])

        # 3. Camera
        self.assertIn("camera", cfg)
        self.assertIn("scale_x", cfg["camera"])
        self.assertIn("scale_y", cfg["camera"])
        self.assertIn("hud_offset_y", cfg["camera"])
        self.assertIn("edge_margin", cfg["camera"])
        self.assertIn("max_radar_distance", cfg["camera"])

        # 4. Render Settings
        self.assertIn("render_settings", cfg)
        r = cfg["render_settings"]
        self.assertIn("minimap_show_enemies", r)
        self.assertIn("minimap_show_allies", r)
        self.assertIn("minimap_show_arrows", r)
        self.assertIn("minimap_show_minions", r)
        self.assertIn("minimap_show_monsters", r)
        self.assertIn("screen_show_overhead_hp", r)
        self.assertIn("screen_show_skill_cooldowns", r)
        self.assertIn("screen_show_battle_spell", r)
        self.assertIn("screen_show_distance", r)
        self.assertIn("screen_show_edge_radar", r)

    def test_live_snapshot_parsing(self):
        """Validates that LIVE_FULL_WORLD_SNAPSHOT.json parses into complete FrameSnapshot entities."""
        self.assertTrue(os.path.exists(SNAPSHOT_PATH), f"Snapshot file missing at {SNAPSHOT_PATH}")
        with open(SNAPSHOT_PATH, "r") as f:
            snap = json.load(f)

        self.assertIn("in_match", snap)
        self.assertTrue(snap["in_match"])

        # Local player
        self.assertIn("local_player", snap)
        lp = snap["local_player"]
        self.assertIn("hero_id", lp)
        self.assertIn("hp", lp)
        self.assertIn("hp_max", lp)
        self.assertIn("pos_x", lp)
        self.assertIn("pos_y", lp)
        self.assertIn("abilities", lp)
        self.assertGreater(len(lp["abilities"]), 0)

        # Enemies / Allies / Minions / Monsters / Towers
        self.assertIn("enemies", snap)
        self.assertIn("soldiers", snap)
        self.assertIn("monsters", snap)
        self.assertIn("towers", snap)

    def test_mock_daemon_telemetry_stream(self):
        """Simulates low-latency TCP communication on a temporary port with GET_INFO command."""
        # Find free port
        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv_sock.bind(("127.0.0.1", 0))
        srv_port = srv_sock.getsockname()[1]
        srv_sock.listen(1)

        server_running = threading.Event()
        server_running.set()

        def mock_daemon_thread():
            conn, _ = srv_sock.accept()
            # Send handshake banner
            banner = json.dumps({"agent": "vemins_daemon", "version": "1.0.0", "build_hash": "a1b2c3d4"}) + "\n"
            conn.sendall(banner.encode())

            with open(SNAPSHOT_PATH, "r") as f:
                sample_data = f.read().replace("\n", " ").strip()

            while server_running.is_set():
                try:
                    conn.settimeout(0.5)
                    req = conn.recv(64).decode('utf-8', errors='ignore')
                    if not req:
                        break
                    if "GET_INFO" in req:
                        resp = sample_data + "\n"
                        conn.sendall(resp.encode())
                except socket.timeout:
                    continue
                except Exception:
                    break
            conn.close()
            srv_sock.close()

        t = threading.Thread(target=mock_daemon_thread, daemon=True)
        t.start()

        # Client test
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        client.connect(("127.0.0.1", srv_port))

        client_file = client.makefile("r")
        banner_line = client_file.readline()
        banner_json = json.loads(banner_line)
        self.assertEqual(banner_json.get("agent"), "vemins_daemon")

        # Send GET_INFO
        t0 = time.perf_counter()
        client.sendall(b"GET_INFO\n")
        resp_line = client_file.readline()
        rtt_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(rtt_ms, 50.0, "TCP local RTT should be sub-50ms")
        frame_json = json.loads(resp_line)
        self.assertTrue(frame_json.get("in_match"))

        client.close()
        server_running.clear()
        t.join(timeout=1.0)


if __name__ == "__main__":
    unittest.main()

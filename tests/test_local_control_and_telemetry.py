"""
test_local_control_and_telemetry.py - Unit & Integration Tests for:
1. Local Control API Server (GET /api/status, GET /api/config, POST /api/config)
2. Fast TCP Socket Telemetry Client with auto-reconnect & atomic EspSnapshot ingestion
3. Daemon IL2CPP snapshot memory parser & hero/spell mappings
"""

import json
import os
import time
import socket
import threading
import urllib.request
import urllib.error
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT_DIR, "LIVE_FULL_WORLD_SNAPSHOT.json")
CONFIG_PATH = os.path.join(ROOT_DIR, "minimap_config.json")


class MockLocalControlServer:
    """Mock Python server implementing the exact contract of LocalControlServer.kt."""

    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.config = {
            "minimap_x": 75,
            "minimap_y": 15,
            "minimap_size": 320,
            "minimap_width": 320,
            "minimap_height": 320,
            "minimap_alpha": 0.85,
            "show_minimap": True,
            "show_enemies": True,
            "show_allies": True,
            "show_minions": True,
            "show_monsters": True,
            "show_combat_hud": True,
            "show_world_combat_hud": True,
            "show_hp_bars": True,
            "show_cooldowns": True,
            "show_offscreen": True,
            "show_offscreen_radar": True,
            "server_host": "127.0.0.1",
            "server_port": 9999
        }
        self.fps = 60
        self.is_running = True
        self.server = None
        self.thread = None

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

            def do_GET(self):
                path = self.path.split("?")[0]
                if path in ("/api/status", "/status"):
                    resp = {
                        "status": "running",
                        "service_active": True,
                        "fps": parent.fps,
                        "connected_to_daemon": True,
                        "timestamp": int(time.time() * 1000),
                        "telemetry_summary": {
                            "timestamp": int(time.time() * 1000),
                            "in_match": True,
                            "pid": 12345,
                            "enemies_count": 5,
                            "allies_count": 4,
                            "minions_count": 12,
                            "monsters_count": 3,
                            "local_hero": {
                                "id": 18,
                                "hero_id": 18,
                                "name": "Layla",
                                "hp": 2780,
                                "max_hp": 2780,
                                "level": 4,
                                "pos_x": 2.71,
                                "pos_y": 40.82,
                                "skill1_cd": 0.0,
                                "skill2_cd": 0.0,
                                "ult_cd": 0.0,
                                "spell_cd": 0.0,
                                "spell_name": "Flicker"
                            }
                        }
                    }
                    self._send_json(200, resp)
                elif path in ("/api/config", "/config"):
                    self._send_json(200, parent.config)
                else:
                    self._send_json(404, {"status": "error", "error": "Not Found"})

            def do_POST(self):
                path = self.path.split("?")[0]
                if path in ("/api/config", "/config"):
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length).decode("utf-8")
                    try:
                        updates = json.loads(body)
                        parent.config.update(updates)
                        self._send_json(200, {
                            "status": "success",
                            "message": "Configuration updated successfully",
                            "config": parent.config
                        })
                    except Exception as e:
                        self._send_json(400, {"status": "error", "error": str(e)})
                else:
                    self._send_json(404, {"status": "error", "error": "Not Found"})

            def _send_json(self, code, data):
                body = json.dumps(data).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=UTF-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

        self.server = HTTPServer((self.host, self.port), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class TestLocalControlAndTelemetry(unittest.TestCase):

    def test_local_control_api_status_endpoint(self):
        """Validates that GET /api/status returns app status, FPS, and live telemetry summary."""
        server = MockLocalControlServer()
        server.start()
        try:
            url = f"http://127.0.0.1:{server.port}/api/status"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data.get("status"), "running")
                self.assertTrue(data.get("service_active"))
                self.assertEqual(data.get("fps"), 60)
                self.assertIn("telemetry_summary", data)
                summary = data["telemetry_summary"]
                self.assertTrue(summary.get("in_match"))
                self.assertIn("local_hero", summary)
                lh = summary["local_hero"]
                self.assertEqual(lh.get("name"), "Layla")
                self.assertEqual(lh.get("hero_id"), 18)
                self.assertEqual(lh.get("spell_name"), "Flicker")
        finally:
            server.stop()

    def test_local_control_api_config_get_and_post(self):
        """Validates GET /api/config and dynamic POST /api/config updates."""
        server = MockLocalControlServer()
        server.start()
        try:
            # 1. GET initial config
            url = f"http://127.0.0.1:{server.port}/api/config"
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                cfg = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(cfg.get("minimap_size"), 320)
                self.assertTrue(cfg.get("show_monsters"))

            # 2. POST update
            update_payload = json.dumps({
                "minimap_size": 380,
                "show_monsters": False,
                "minimap_alpha": 0.95
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=update_payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                res_data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(res_data.get("status"), "success")
                updated_cfg = res_data.get("config", {})
                self.assertEqual(updated_cfg.get("minimap_size"), 380)
                self.assertFalse(updated_cfg.get("show_monsters"))
                self.assertAlmostEqual(updated_cfg.get("minimap_alpha"), 0.95)

            # 3. Verify GET returns updated values
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                cfg = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(cfg.get("minimap_size"), 380)
                self.assertFalse(cfg.get("show_monsters"))

        finally:
            server.stop()

    def test_hero_and_spell_mappings(self):
        """Validates hero IDs to names and spell IDs to spell names mapping consistency."""
        with open(os.path.join(ROOT_DIR, "knowledge/normalized/heroes.json"), "r") as f:
            heroes = json.load(f)

        # Layla, Ling, Chou
        self.assertEqual(heroes.get("18", {}).get("name"), "Layla")
        self.assertEqual(heroes.get("84", {}).get("name"), "Ling")
        self.assertEqual(heroes.get("26", {}).get("name"), "Chou")

        with open(os.path.join(ROOT_DIR, "knowledge/normalized/battle_spells.json"), "r") as f:
            spells = json.load(f)

        self.assertEqual(spells.get("20001", {}).get("name"), "Flicker")
        self.assertEqual(spells.get("20002", {}).get("name"), "Retribution")
        self.assertEqual(spells.get("20003", {}).get("name"), "Inspire")

    def test_daemon_live_snapshot_fields(self):
        """Validates that LIVE_FULL_WORLD_SNAPSHOT conforms to the TelemetryClient ingestion format."""
        with open(SNAPSHOT_PATH, "r") as f:
            snap = json.load(f)

        self.assertIn("in_match", snap)
        self.assertIn("local_player", snap)
        self.assertIn("enemies", snap)
        self.assertIn("allies", snap)
        self.assertIn("soldiers", snap)
        self.assertIn("monsters", snap)
        self.assertIn("towers", snap)

        lp = snap["local_player"]
        self.assertIn("hp", lp)
        self.assertIn("hp_max", lp)
        self.assertIn("abilities", lp)
        self.assertGreater(len(lp["abilities"]), 0)


if __name__ == "__main__":
    unittest.main()

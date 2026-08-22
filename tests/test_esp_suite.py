#!/usr/bin/env python3
"""
test_esp_suite.py - End-to-End Verification Test Suite for VEMINS ESP (Dual-Layer Minimap & Screen Overlay)
"""

import os
import json
import unittest
from minimap_projection import MinimapProjector
from esp_overlay_engine import ESPOverlayEngine, ESPOfflineSim


class TestVeminsESPSuite(unittest.TestCase):
    def setUp(self):
        self.projector = MinimapProjector("minimap_config.json")
        self.engine = ESPOverlayEngine()

    def test_daemon_source_exists_and_no_evdev(self):
        """Verifies that vemins_daemon.c exists and has no evdev or touch injection code."""
        with open("vemins_daemon.c", "r") as f:
            code = f.read()
        self.assertIn("VEMINS ESP Telemetry Daemon", code)
        self.assertNotIn("linux/input.h", code)
        self.assertNotIn("ABS_MT_SLOT", code)
        self.assertNotIn("JOY_DOWN", code)
        self.assertNotIn("JOY_MOVE", code)

    def test_minimap_projection_bounds(self):
        """Verifies that 2D world-to-minimap math maps corners within the bounding box."""
        # Blue fountain
        bx, by = self.projector.world_to_minimap(-50.2, 0.0)
        self.assertTrue(self.projector.map_x <= bx <= self.projector.map_x + self.projector.map_w)
        self.assertTrue(self.projector.map_y <= by <= self.projector.map_y + self.projector.map_h)

        # Red fountain
        rx, ry = self.projector.world_to_minimap(50.2, 0.0)
        self.assertTrue(self.projector.map_x <= rx <= self.projector.map_x + self.projector.map_w)
        self.assertTrue(self.projector.map_y <= ry <= self.projector.map_y + self.projector.map_h)

        # Lord center
        lx, ly = self.projector.world_to_minimap(0.0, 20.5)
        self.assertTrue(self.projector.map_x <= lx <= self.projector.map_x + self.projector.map_w)
        self.assertTrue(self.projector.map_y <= ly <= self.projector.map_y + self.projector.map_h)

    def test_direction_arrow_calculation(self):
        """Verifies direction arrow projection."""
        sx, sy = 200.0, 200.0
        ex, ey = self.projector.calculate_direction_arrow(sx, sy, 1.0, 0.0, length=20.0)
        self.assertAlmostEqual(ex, 220.0, delta=0.1)
        self.assertAlmostEqual(ey, 200.0, delta=0.1)

    def test_isometric_world_to_screen_projection(self):
        """Verifies 3D-to-2D isometric World-to-Screen projection math."""
        # Local hero at (0, 0), enemy at (5, 3) -> should be on-screen
        sx, sy, is_on_screen = self.projector.world_to_screen_isometric(5.0, 3.0, 0.0, 0.0)
        self.assertTrue(is_on_screen)
        self.assertTrue(0 <= sx <= self.projector.screen_w)
        self.assertTrue(0 <= sy <= self.projector.screen_h)

        # Distant enemy at (100, 100) -> should be off-screen
        ox, oy, is_on_screen2 = self.projector.world_to_screen_isometric(100.0, 100.0, 0.0, 0.0)
        self.assertFalse(is_on_screen2)

    def test_edge_radar_border_clamping(self):
        """Verifies off-screen edge radar raycasting and clamping to screen margins."""
        # Project distant off-screen coordinate
        ox, oy, _ = self.projector.world_to_screen_isometric(50.0, -50.0, 0.0, 0.0)
        cx, cy, angle_deg = self.projector.calculate_edge_radar(ox, oy)
        
        # Must be clamped within margin inset
        pad = self.projector.edge_margin
        self.assertTrue(pad <= cx <= self.projector.screen_w - pad)
        self.assertTrue(pad <= cy <= self.projector.screen_h - pad)
        self.assertTrue(-180.0 <= angle_deg <= 180.0)

    def test_dual_layer_esp_draw_list_generation(self):
        """Verifies separate Layer 1 (Minimap) and Layer 2 (Screen Overhead HUD) generation."""
        frame = ESPOfflineSim.generate_sample_frame()
        
        # Layer 1: Minimap
        minimap_draws = self.engine.build_minimap_draw_list(frame)
        m_types = [d.item_type for d in minimap_draws]
        self.assertIn("minimap_box", m_types)
        self.assertIn("minimap_hero", m_types)
        self.assertIn("minimap_minion", m_types)
        self.assertIn("minimap_monster", m_types)
        # Verify no bulky cooldown HUD is present on minimap layer
        self.assertNotIn("screen_overhead_hud", m_types)

        # Layer 2: Main Screen Combat HUD
        screen_draws = self.engine.build_screen_hud_draw_list(frame)
        s_types = [d.item_type for d in screen_draws]
        self.assertTrue("screen_overhead_hud" in s_types or "screen_edge_indicator" in s_types)
        if "screen_overhead_hud" in s_types:
            hud_item = next(d for d in screen_draws if d.item_type == "screen_overhead_hud")
            self.assertIn("hp_pct", hud_item.props)
            self.assertIn("skills", hud_item.props)
            self.assertIn("ult_ready", hud_item.props)


if __name__ == "__main__":
    unittest.main()

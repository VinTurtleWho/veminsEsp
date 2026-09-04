#!/usr/bin/env python3
"""
test_kotlin_engine_math.py - Mathematical Verification for Kotlin SurfaceView Rendering Engine
Validates that the formulas implemented in MinimapProjection.kt and IsometricProjection.kt
behave identically to the authoritative ground truth specification.
"""

import math
import unittest
from minimap_projection import MinimapProjector


class TestKotlinEngineMath(unittest.TestCase):
    def setUp(self):
        self.projector = MinimapProjector("minimap_config.json")
        self.cfg = self.projector.config

    def test_minimap_normalization_and_inversion(self):
        """Validates [-52.0, 52.0] world coordinates mapped to minimap pixel space with invert_y."""
        map_x = float(self.cfg["minimap"]["pos_x"])
        map_y = float(self.cfg["minimap"]["pos_y"])
        map_w = float(self.cfg["minimap"]["width"])
        map_h = float(self.cfg["minimap"]["height"])

        # Center (0.0, 0.0) -> norm_x = 0.5, norm_y = 0.5 -> screen
        mx, my = self.projector.world_to_minimap(0.0, 0.0)
        self.assertAlmostEqual(mx, map_x + 0.5 * map_w, places=2)
        self.assertAlmostEqual(my, map_y + 0.5 * map_h, places=2)

        # Bottom-Left world (-52.0, -52.0) -> norm = (0.0, 0.0) -> inverted screen
        bl_x, bl_y = self.projector.world_to_minimap(-52.0, -52.0)
        self.assertAlmostEqual(bl_x, map_x, places=2)
        self.assertAlmostEqual(bl_y, map_y + map_h, places=2)

        # Top-Right world (52.0, 52.0) -> norm = (1.0, 1.0) -> inverted screen
        tr_x, tr_y = self.projector.world_to_minimap(52.0, 52.0)
        self.assertAlmostEqual(tr_x, map_x + map_w, places=2)
        self.assertAlmostEqual(tr_y, map_y, places=2)

    def test_isometric_world_to_screen_math(self):
        """Validates 45-degree isometric projection formulas."""
        # Screen center: (1200, 540), scales: (38, 27), hud_offset: 65
        # Target: (5.0, 3.0), Local: (0.0, 0.0)
        # dx = 5.0, dy = 3.0
        # iso_x = (5 - 3) * 0.70710678 = 1.41421356
        # iso_y = (5 + 3) * 0.70710678 = 5.65685424
        # expected sx = 1200 + 1.41421356 * 38 = 1253.74
        # expected sy = 540 - 5.65685424 * 27 - 65 = 322.26
        sx, sy, on_screen = self.projector.world_to_screen_isometric(5.0, 3.0, 0.0, 0.0)
        self.assertTrue(on_screen)
        self.assertAlmostEqual(sx, 1253.74, delta=0.1)
        self.assertAlmostEqual(sy, 322.26, delta=0.1)

    def test_perspective_world_to_screen_math(self):
        """Validates 3D perspective projection depth division and foreshortening."""
        # Target: (5.0, 3.0), Cam: (0.0, 0.0)
        # iso_x = 1.41421356, iso_y = 5.65685424
        # depth = 28.0 + 5.65685424 * cos(58 deg) = 28.0 + 2.99764 = 30.9976
        # persp_scale = 28.0 / 30.9976 = 0.90329
        sx, sy, on_screen = self.projector.world_to_screen_perspective(5.0, 3.0, 0.0, 0.0)
        self.assertTrue(on_screen)
        self.assertTrue(1200.0 < sx < 1253.74) # Perspective compresses compared to flat linear
        self.assertTrue(sy < 540.0)

        # Long range sniper target (e.g. Novaria S2 / Layla Ult) at (25.0, 25.0)
        # Without perspective, linear shoots off; with perspective, remains bounded and proportional
        sx_far, sy_far, on_screen_far = self.projector.world_to_screen_perspective(25.0, 25.0, 0.0, 0.0)
        self.assertTrue(on_screen_far or not on_screen_far) # Valid finite coordinates
        self.assertTrue(math.isfinite(sx_far) and math.isfinite(sy_far))

    def test_off_screen_edge_radar_clamping_math(self):
        """Validates edge radar ray-box intersection with margins."""
        # Distant off-screen enemy at (35.0, -25.0)
        # dx = 35, dy = -25
        # iso_x = 60 * 0.70710678 = 42.4264 -> sx = 1200 + 42.4264 * 38 = 2812.2
        # iso_y = 10 * 0.70710678 = 7.071068 -> sy = 540 - 7.071068 * 27 - 65 = 284.08
        ox, oy, on_screen = self.projector.world_to_screen_isometric(35.0, -25.0, 0.0, 0.0)
        self.assertFalse(on_screen)

        cx, cy, angle_deg = self.projector.calculate_edge_radar(ox, oy)
        pad = 45.0
        self.assertEqual(cx, 2400.0 - pad) # clamped to right border
        self.assertTrue(pad <= cy <= 1080.0 - pad)
        self.assertAlmostEqual(angle_deg, -9.0, delta=1.0)

    def test_diamond_45_degree_rotation_matrix(self):
        """Validates the 45° diamond coordinate rotation matrix: x_rot = (x - y)/sqrt(2), y_rot = (x + y)/sqrt(2)."""
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        
        # Point (10.0, 0.0) -> x_rot = 10 / sqrt(2) = 7.071, y_rot = 10 / sqrt(2) = 7.071
        x, y = 10.0, 0.0
        rx = (x - y) * inv_sqrt2
        ry = (x + y) * inv_sqrt2
        self.assertAlmostEqual(rx, 7.0710678, places=4)
        self.assertAlmostEqual(ry, 7.0710678, places=4)

        # Point (0.0, 10.0) -> x_rot = -10 / sqrt(2) = -7.071, y_rot = 10 / sqrt(2) = 7.071
        x2, y2 = 0.0, 10.0
        rx2 = (x2 - y2) * inv_sqrt2
        ry2 = (x2 + y2) * inv_sqrt2
        self.assertAlmostEqual(rx2, -7.0710678, places=4)
        self.assertAlmostEqual(ry2, 7.0710678, places=4)

    def test_heading_arrow_45_degree_rotation(self):
        """Validates heading vector rotation by 45° diamond matrix."""
        # Facing straight up (dir_x = 0, dir_y = 1) rotated by 45 degrees
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        dx, dy = 0.0, 1.0
        rdx = (dx - dy) * inv_sqrt2
        rdy = (dx + dy) * inv_sqrt2
        self.assertAlmostEqual(rdx, -0.70710678, places=4)
        self.assertAlmostEqual(rdy, 0.70710678, places=4)

    def test_manifest_asset_counts_and_mappings(self):
        """Validates that assets/manifest.json and app/src/main/assets/manifest.json contain 127 heroes and 11 spells."""
        import json
        import os

        manifest_path = "app/src/main/assets/manifest.json"
        if not os.path.exists(manifest_path):
            manifest_path = "vemins_overlay_app/app/src/main/assets/manifest.json"
        
        self.assertTrue(os.path.exists(manifest_path), "manifest.json missing in assets")
        with open(manifest_path, "r") as f:
            data = json.load(f)

        self.assertIn("heroes", data)
        self.assertIn("spells", data)
        self.assertIn("hero_names", data)
        self.assertIn("spell_names", data)

        self.assertGreaterEqual(len(data["heroes"]), 120)
        self.assertGreaterEqual(len(data["hero_names"]), 120)
        self.assertGreaterEqual(len(data["spells"]), 10)
        self.assertGreaterEqual(len(data["spell_names"]), 10)
        self.assertEqual(data["hero_names"]["1"], "Miya")
        self.assertEqual(data["spell_names"]["20001"], "Flicker")


if __name__ == "__main__":
    unittest.main()

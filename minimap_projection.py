#!/usr/bin/env python3
"""
minimap_projection.py - 2D World-to-Minimap & 3D Isometric World-to-Screen Projection Engine

Features:
1. World-to-Minimap Linear Mapping:
   - Projects world coordinates ([-52.0, +52.0]) onto the 2D top-left Minimap box.
   - Calculates direction velocity arrows.
2. World-to-Screen Isometric Projection (Main Gameplay Screen):
   - Projects relative world delta (target_pos - local_pos) onto the device screen
     using MLBB's 45°/55° isometric camera geometry.
   - Outputs exact screen pixel coordinates (X_hud, Y_hud) for overhead HP & Cooldown bars.
3. Off-Screen Edge Radar Border Clamping:
   - For enemies outside the active screen, projects a ray from screen center to the
     screen perimeter and calculates edge indicator chevrons with distance in meters.
"""

import json
import math
from typing import Tuple, Dict, Any, Optional


class MinimapProjector:
    def __init__(self, config_path: str = "minimap_config.json"):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self._update_cached_transforms()

    def load_config(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            return {
                "screen": {"width": 2400.0, "height": 1080.0},
                "minimap": {"pos_x": 75.0, "pos_y": 15.0, "width": 320.0, "height": 320.0, "rotation_degrees": 0.0, "invert_y": True},
                "camera": {"scale_x": 38.0, "scale_y": 27.0, "hud_offset_y": 65.0, "edge_margin": 45.0, "max_radar_distance": 45.0},
                "world_bounds": {"min_x": -52.0, "max_x": 52.0, "min_y": -52.0, "max_y": 52.0},
                "render_settings": {
                    "minimap_show_enemies": True,
                    "minimap_show_allies": False,
                    "minimap_show_arrows": True,
                    "minimap_show_minions": True,
                    "minimap_show_monsters": True,
                    "minimap_hero_dot_radius": 9.0,
                    "minimap_arrow_length": 18.0,
                    "minimap_minion_dot_radius": 3.5,
                    "minimap_monster_dot_radius": 7.0,
                    "screen_show_overhead_hp": True,
                    "screen_show_skill_cooldowns": True,
                    "screen_show_battle_spell": true,
                    "screen_show_distance": True,
                    "screen_show_edge_radar": True
                }
            }

    def save_config(self, path: Optional[str] = None):
        target = path or self.config_path
        with open(target, "w") as f:
            json.dump(self.config, f, indent=2)

    def _update_cached_transforms(self):
        s = self.config.get("screen", {})
        self.screen_w = float(s.get("width", 2400.0))
        self.screen_h = float(s.get("height", 1080.0))
        self.screen_cx = self.screen_w / 2.0
        self.screen_cy = self.screen_h / 2.0

        m = self.config.get("minimap", {})
        self.map_x = float(m.get("pos_x", 75.0))
        self.map_y = float(m.get("pos_y", 15.0))
        self.map_w = float(m.get("width", 320.0))
        self.map_h = float(m.get("height", 320.0))
        self.invert_y = bool(m.get("invert_y", True))

        c = self.config.get("camera", {})
        self.cam_scale_x = float(c.get("scale_x", 38.0))
        self.cam_scale_y = float(c.get("scale_y", 27.0))
        self.hud_offset_y = float(c.get("hud_offset_y", 65.0))
        self.edge_margin = float(c.get("edge_margin", 45.0))
        self.max_radar_distance = float(c.get("max_radar_distance", 45.0))

        w = self.config.get("world_bounds", {})
        self.min_x = float(w.get("min_x", -52.0))
        self.max_x = float(w.get("max_x", 52.0))
        self.min_y = float(w.get("min_y", -52.0))
        self.max_y = float(w.get("max_y", 52.0))
        self.world_w = self.max_x - self.min_x if (self.max_x - self.min_x) != 0 else 104.0
        self.world_h = self.max_y - self.min_y if (self.max_y - self.min_y) != 0 else 104.0

    # --- LAYER 1: MINIMAP PROJECTION MATH ---

    def world_to_minimap(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Maps world coordinates (X, Y) to screen pixel coordinates on the top-left Minimap box."""
        norm_x = (world_x - self.min_x) / self.world_w
        norm_y = (world_y - self.min_y) / self.world_h

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        screen_x = self.map_x + (norm_x * self.map_w)
        if self.invert_y:
            screen_y = self.map_y + ((1.0 - norm_y) * self.map_h)
        else:
            screen_y = self.map_y + (norm_y * self.map_h)

        return screen_x, screen_y

    def calculate_direction_arrow(self, screen_x: float, screen_y: float, dir_x: float, dir_y: float, length: float = 18.0) -> Tuple[float, float]:
        """Calculates arrow endpoint from position and normalized direction vector."""
        mag = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if mag < 0.001:
            return screen_x, screen_y

        ndx = dir_x / mag
        ndy = dir_y / mag

        if self.invert_y:
            ndy = -ndy

        end_x = screen_x + (ndx * length)
        end_y = screen_y + (ndy * length)
        return end_x, end_y

    # --- LAYER 2: ISOMETRIC WORLD-TO-SCREEN (W2S) & OVERHEAD HUD MATH ---

    def world_to_screen_isometric(
        self,
        target_x: float,
        target_y: float,
        local_x: float,
        local_y: float,
        offset_y: Optional[float] = None
    ) -> Tuple[float, float, bool]:
        """
        Transforms relative Cartesian world coordinates into 2D pixel coordinates on the main screen.
        MLBB uses an isometric camera tilted at approx 45°-55° centered on the local hero.
        
        Returns:
            (screen_x, screen_y, is_on_screen)
        """
        dx = target_x - local_x
        dy = target_y - local_y

        # Isometric coordinate transform (45-degree ground plane projection)
        iso_x = (dx - dy) * 0.70710678
        iso_y = (dx + dy) * 0.70710678

        screen_x = self.screen_cx + (iso_x * self.cam_scale_x)
        lift_y = offset_y if offset_y is not None else self.hud_offset_y
        screen_y = self.screen_cy - (iso_y * self.cam_scale_y) - lift_y

        is_on_screen = (0.0 <= screen_x <= self.screen_w and 0.0 <= screen_y <= self.screen_h)
        return screen_x, screen_y, is_on_screen

    def world_to_screen_perspective(
        self,
        target_x: float,
        target_y: float,
        cam_x: float,
        cam_y: float,
        offset_y: Optional[float] = None,
        cam_height: float = 28.0,
        pitch_deg: float = 58.0,
        target_z: float = 0.0
    ) -> Tuple[float, float, bool]:
        """
        Transforms 3D world coordinates into 2D screen coordinates using true perspective projection.
        Divides by depth along the camera ray (Z_depth = cam_height + iso_y * cos(pitch)),
        preventing far-distance overshooting and near-distance undershooting.
        """
        dx = target_x - cam_x
        dy = target_y - cam_y

        # 45-degree yaw rotation on ground plane
        iso_x = (dx - dy) * 0.70710678
        iso_y = (dx + dy) * 0.70710678

        pitch_rad = math.radians(pitch_deg)
        cos_pitch = math.cos(pitch_rad)
        sin_pitch = math.sin(pitch_rad)

        # Depth along camera line of sight
        depth = cam_height + (iso_y * cos_pitch) - (target_z * sin_pitch)
        if depth < 4.0:
            depth = 4.0
        persp_scale = cam_height / depth

        screen_x = self.screen_cx + (iso_x * self.cam_scale_x) * persp_scale
        lift_y = (offset_y if offset_y is not None else self.hud_offset_y) * persp_scale
        screen_y = self.screen_cy - (iso_y * self.cam_scale_y * persp_scale) - lift_y

        is_on_screen = (0.0 <= screen_x <= self.screen_w and 0.0 <= screen_y <= self.screen_h)
        return screen_x, screen_y, is_on_screen

    def calculate_edge_radar(
        self,
        screen_x: float,
        screen_y: float,
        margin: Optional[float] = None
    ) -> Tuple[float, float, float]:
        """
        For off-screen enemies, projects a ray from screen center to (screen_x, screen_y),
        clamping it to the screen border inset by margin.
        
        Returns:
            (clamped_x, clamped_y, angle_deg)
        """
        pad = margin if margin is not None else self.edge_margin
        min_x, max_x = pad, self.screen_w - pad
        min_y, max_y = pad, self.screen_h - pad

        vx = screen_x - self.screen_cx
        vy = screen_y - self.screen_cy

        angle_deg = math.degrees(math.atan2(vy, vx))

        # Find scale factor t to intersect screen bounding box
        t_candidates = []
        if vx > 0.001:
            t_candidates.append((max_x - self.screen_cx) / vx)
        elif vx < -0.001:
            t_candidates.append((min_x - self.screen_cx) / vx)

        if vy > 0.001:
            t_candidates.append((max_y - self.screen_cy) / vy)
        elif vy < -0.001:
            t_candidates.append((min_y - self.screen_cy) / vy)

        t = min(t_candidates) if t_candidates else 1.0
        t = max(0.0, t)

        clamped_x = self.screen_cx + vx * t
        clamped_y = self.screen_cy + vy * t

        clamped_x = max(min_x, min(max_x, clamped_x))
        clamped_y = max(min_y, min(max_y, clamped_y))

        return clamped_x, clamped_y, angle_deg

    @staticmethod
    def calc_distance_m(x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculates distance in meters between two world Cartesian coordinates."""
        return math.hypot(x2 - x1, y2 - y1)

    def calibrate_minimap(self, x: float, y: float, w: float, h: float):
        """Calibrates Minimap position & dimension bounds."""
        self.config["minimap"]["pos_x"] = x
        self.config["minimap"]["pos_y"] = y
        self.config["minimap"]["width"] = w
        self.config["minimap"]["height"] = h
        self._update_cached_transforms()
        self.save_config()

    def calibrate_camera(self, scale_x: float, scale_y: float, hud_offset_y: float):
        """Calibrates Isometric World-to-Screen projection parameters."""
        self.config["camera"]["scale_x"] = scale_x
        self.config["camera"]["scale_y"] = scale_y
        self.config["camera"]["hud_offset_y"] = hud_offset_y
        self._update_cached_transforms()
        self.save_config()


if __name__ == "__main__":
    projector = MinimapProjector("minimap_config.json")
    print("Testing Minimap & Isometric World-to-Screen Projections:")
    print("---------------------------------------------------------")
    
    # 1. Minimap mapping
    mx, my = projector.world_to_minimap(0.0, 0.0)
    print(f"[Minimap] Mid-River (0.0, 0.0) -> Minimap Pixel: ({mx:.1f}, {my:.1f})")

    # 2. Isometric On-Screen Overhead HUD mapping
    local_pos = (0.0, 0.0)
    enemy_pos = (5.0, 3.0)
    sx, sy, on_screen = projector.world_to_screen_isometric(enemy_pos[0], enemy_pos[1], local_pos[0], local_pos[1])
    dist = projector.calc_distance_m(local_pos[0], local_pos[1], enemy_pos[0], enemy_pos[1])
    print(f"[Screen W2S] Enemy @ {enemy_pos} (Dist: {dist:.1f}m) -> Screen Pixel: ({sx:.1f}, {sy:.1f}) | OnScreen: {on_screen}")

    # 3. Off-Screen Edge Radar clamping
    off_enemy_pos = (35.0, -25.0)
    ox, oy, on_screen2 = projector.world_to_screen_isometric(off_enemy_pos[0], off_enemy_pos[1], local_pos[0], local_pos[1])
    cx, cy, angle = projector.calculate_edge_radar(ox, oy)
    dist2 = projector.calc_distance_m(local_pos[0], local_pos[1], off_enemy_pos[0], off_enemy_pos[1])
    print(f"[Edge Radar] Enemy @ {off_enemy_pos} (Dist: {dist2:.1f}m) -> Clamped Border: ({cx:.1f}, {cy:.1f}), Angle: {angle:.1f}° | OnScreen: {on_screen2}")

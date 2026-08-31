#!/usr/bin/env python3
"""
esp_overlay_engine.py - VEMINS Dual-Layer ESP Overlay Engine

Features:
1. Layer 1: Minimap Radar (Top-Left In-Game Map Box)
   - Minimap Hero Dots & IDs
   - Movement Velocity / Heading Direction Arrows
   - Lane Minion Wave Dots (Blue/Red)
   - Jungle Creep & Boss Markers (Lord, Turtle, Buffs)
   - (Zero skill/cooldown text clutter on the minimap)

2. Layer 2: Main In-Game Screen Overhead HUD & Edge Radar
   - Isometric 3D-to-2D World-to-Screen Projection
   - Overhead Combat HUD:
     • Current HP & Max HP bar + Active Shields
     • Ultimate (Skill 3/4) Countdown & READY state
     • Skill 1 & Skill 2 Cooldown Badges
     • Battle Spell Cooldown Timer
     • Distance from local player in meters
   - Off-Screen Perimeter Edge Indicator:
     • Border chevrons pointing toward approaching enemies
     • Distance in meters & Ult Ready alert
"""

import time
import math
from typing import Dict, List, Any, Optional, Tuple

from perception.memory_reader import DaemonMemoryReader
from perception.orchestrator import ProductionPerceptionOrchestrator
from perception.models import WorldSnapshot, HeroEntity, SoldierEntity, MonsterEntity
from minimap_projection import MinimapProjector


class ESPOfflineSim:
    @staticmethod
    def generate_sample_frame() -> WorldSnapshot:
        """Generates a representative WorldSnapshot for headless offline testing."""
        from perception.models import HeroEntity, SoldierEntity, MonsterEntity, TowerEntity, HeroAbilities, AbilityCooldown
        import time

        local_abilities = HeroAbilities(
            is_casting=False,
            cooldowns=(
                AbilityCooldown(spell_id=1, remaining_cd_ms=0, max_cd_ms=4000, start_time_ms=0, is_cooling_down=False),
                AbilityCooldown(spell_id=2, remaining_cd_ms=1500, max_cd_ms=6000, start_time_ms=1000, is_cooling_down=True),
                AbilityCooldown(spell_id=3, remaining_cd_ms=8000, max_cd_ms=25000, start_time_ms=2000, is_cooling_down=True),
            )
        )

        enemy_abilities = HeroAbilities(
            is_casting=False,
            cooldowns=(
                AbilityCooldown(spell_id=1, remaining_cd_ms=2000, max_cd_ms=5000, start_time_ms=500, is_cooling_down=True),
                AbilityCooldown(spell_id=2, remaining_cd_ms=0, max_cd_ms=8000, start_time_ms=0, is_cooling_down=False),
                AbilityCooldown(spell_id=3, remaining_cd_ms=15000, max_cd_ms=30000, start_time_ms=1000, is_cooling_down=True),
            )
        )

        local_hero = HeroEntity(
            address=0x12345678,
            hero_id=18,
            level=12,
            hp=4500,
            hp_max=5200,
            is_dead=False,
            camp=1,
            pos_x=-15.0,
            pos_y=5.0,
            gold=6200,
            is_bot=False,
            is_local_player=True,
            mp=800,
            mp_max=1000,
            facing_x=0.707,
            facing_y=0.707,
            in_battle=True,
            abilities=local_abilities
        )

        enemy_hero = HeroEntity(
            address=0x87654321,
            hero_id=78,
            level=11,
            hp=3800,
            hp_max=4900,
            is_dead=False,
            camp=2,
            pos_x=12.0,
            pos_y=-8.0,
            gold=5800,
            is_bot=False,
            is_local_player=False,
            mp=600,
            mp_max=900,
            facing_x=-1.0,
            facing_y=0.0,
            in_battle=True,
            abilities=enemy_abilities
        )

        minion = SoldierEntity(
            address=0x11223344,
            soldier_id=101,
            soldier_type=1,
            lane=2,
            point_index=3,
            hp=1200,
            hp_max=1200,
            is_dead=False,
            camp=2,
            pos_x=5.0,
            pos_y=-3.0
        )

        monster = MonsterEntity(
            address=0x55667788,
            monster_id=201,
            monster_type=1,
            hp=3500,
            hp_max=3500,
            is_dead=False,
            camp=0,
            pos_x=0.0,
            pos_y=15.0
        )

        return WorldSnapshot(
            timestamp_ns=time.time_ns(),
            in_match=True,
            local_player=local_hero,
            allies=(),
            enemies=(enemy_hero,),
            towers=(),
            soldiers=(minion,),
            monsters=(monster,),
            bullets=(),
            sequence_id=1,
            frame_time_ms=int(time.time() * 1000),
            battle_state=6
        )


class ESPRenderItem:
    def __init__(self, item_type: str, x: float, y: float, **kwargs):
        self.item_type = item_type
        self.x = x
        self.y = y
        self.props = kwargs

    @property
    def type(self) -> str:
        return self.item_type

    def to_dict(self) -> Dict[str, Any]:
        d = {"type": self.item_type, "x": round(self.x, 1), "y": round(self.y, 1)}
        d.update(self.props)
        return d


class ESPOverlayEngine:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999, config_path: str = "minimap_config.json"):
        self.host = host
        self.port = port
        self.projector = MinimapProjector(config_path)
        self.reader = DaemonMemoryReader(host=host, port=port)
        self.orchestrator = ProductionPerceptionOrchestrator(self.reader)
        self.is_connected = False

    def connect(self) -> bool:
        try:
            ok = self.reader.connect()
            self.is_connected = ok
            return ok
        except Exception:
            self.is_connected = False
            return False

    def fetch_snapshot(self) -> WorldSnapshot:
        """Fetches live verified WorldSnapshot via Python Perception V3 orchestrator."""
        if not self.is_connected or not self.reader._sock:
            if not self.connect():
                return WorldSnapshot(
                    timestamp_ns=time.time_ns(),
                    in_match=False,
                    local_player=None,
                    allies=(),
                    enemies=(),
                    towers=(),
                    soldiers=(),
                    monsters=(),
                    bullets=(),
                    sequence_id=0,
                    frame_time_ms=0,
                    battle_state=0
                )

        try:
            return self.orchestrator.get_world_snapshot()
        except Exception:
            self.is_connected = False
            return WorldSnapshot(
                timestamp_ns=time.time_ns(),
                in_match=False,
                local_player=None,
                allies=(),
                enemies=(),
                towers=(),
                soldiers=(),
                monsters=(),
                bullets=(),
                sequence_id=0,
                frame_time_ms=0,
                battle_state=0
            )

    # --- LAYER 1: MINIMAP VIEWPORT DRAW LIST (TOP-LEFT ONLY) ---

    def build_minimap_draw_list(self, snapshot: WorldSnapshot) -> List[ESPRenderItem]:
        """Generates pure 2D minimap radar elements (No text/cooldown clutter)."""
        draw_list: List[ESPRenderItem] = []
        cfg = self.projector.config.get("render_settings", {})

        # 1. Minimap Background Bounding Box
        m = self.projector.config.get("minimap", {})
        draw_list.append(ESPRenderItem(
            "minimap_box",
            m.get("pos_x", 75.0),
            m.get("pos_y", 15.0),
            w=m.get("width", 320.0),
            h=m.get("height", 320.0)
        ))

        # 2. Minions Layer (Blue = Ally, Red = Enemy)
        if cfg.get("minimap_show_minions", True):
            for soldier in snapshot.soldiers:
                if soldier.is_dead or soldier.hp <= 0:
                    continue
                sx, sy = self.projector.world_to_minimap(soldier.pos_x, soldier.pos_y)
                draw_list.append(ESPRenderItem(
                    "minimap_minion",
                    sx, sy,
                    camp=soldier.camp,
                    hp=soldier.hp,
                    max_hp=soldier.hp_max,
                    radius=cfg.get("minimap_minion_dot_radius", 3.5)
                ))

        # 3. Jungle Creeps & Bosses (Lord, Turtle, Buffs)
        if cfg.get("minimap_show_monsters", True):
            for monster in snapshot.monsters:
                if monster.is_dead or monster.hp <= 0:
                    continue
                sx, sy = self.projector.world_to_minimap(monster.pos_x, monster.pos_y)
                draw_list.append(ESPRenderItem(
                    "minimap_monster",
                    sx, sy,
                    id=monster.monster_type,
                    hp=monster.hp,
                    max_hp=monster.hp_max,
                    radius=cfg.get("minimap_monster_dot_radius", 7.0)
                ))

        # 4. Local Player Minimap Dot (Green)
        if snapshot.local_player and not snapshot.local_player.is_dead:
            lp = snapshot.local_player
            sx, sy = self.projector.world_to_minimap(lp.pos_x, lp.pos_y)
            draw_list.append(ESPRenderItem(
                "minimap_hero",
                sx, sy,
                hero_id=lp.hero_id,
                level=lp.level,
                is_local=True,
                camp=lp.camp,
                radius=cfg.get("minimap_hero_dot_radius", 9.0)
            ))
            if cfg.get("minimap_show_arrows", True) and (abs(lp.facing_x) > 0.01 or abs(lp.facing_y) > 0.01):
                ex, ey = self.projector.calculate_direction_arrow(sx, sy, lp.facing_x, lp.facing_y, cfg.get("minimap_arrow_length", 18.0))
                draw_list.append(ESPRenderItem("minimap_arrow", sx, sy, end_x=ex, end_y=ey, color="self"))

        # 5. Allied Heroes Minimap Dots (Blue)
        if cfg.get("minimap_show_allies", False):
            for ally in snapshot.allies:
                if ally.is_dead or ally.hp <= 0:
                    continue
                sx, sy = self.projector.world_to_minimap(ally.pos_x, ally.pos_y)
                draw_list.append(ESPRenderItem(
                    "minimap_hero",
                    sx, sy,
                    hero_id=ally.hero_id,
                    level=ally.level,
                    is_local=False,
                    is_ally=True,
                    camp=ally.camp,
                    radius=cfg.get("minimap_hero_dot_radius", 9.0)
                ))

        # 6. Enemy Heroes Minimap Dots (Red) + Movement Arrows
        if cfg.get("minimap_show_enemies", True):
            for enemy in snapshot.enemies:
                if enemy.is_dead or enemy.hp <= 0:
                    continue
                sx, sy = self.projector.world_to_minimap(enemy.pos_x, enemy.pos_y)
                draw_list.append(ESPRenderItem(
                    "minimap_hero",
                    sx, sy,
                    hero_id=enemy.hero_id,
                    level=enemy.level,
                    is_local=False,
                    is_ally=False,
                    camp=enemy.camp,
                    radius=cfg.get("minimap_hero_dot_radius", 9.0)
                ))

                if cfg.get("minimap_show_arrows", True) and (abs(enemy.facing_x) > 0.01 or abs(enemy.facing_y) > 0.01):
                    ex, ey = self.projector.calculate_direction_arrow(sx, sy, enemy.facing_x, enemy.facing_y, cfg.get("minimap_arrow_length", 18.0))
                    draw_list.append(ESPRenderItem("minimap_arrow", sx, sy, end_x=ex, end_y=ey, color="enemy"))

        return draw_list

    # --- LAYER 2: MAIN IN-GAME SCREEN OVERHEAD COMBAT HUD & EDGE RADAR ---

    def build_screen_hud_draw_list(self, snapshot: WorldSnapshot) -> List[ESPRenderItem]:
        """
        Generates in-game screen space combat HUDs:
        - Overhead HP / Cooldown badges for enemies inside the screen viewport.
        - Border Edge Chevrons for off-screen approaching enemies.
        """
        draw_list: List[ESPRenderItem] = []
        cfg = self.projector.config.get("render_settings", {})

        local_x = snapshot.local_player.pos_x if snapshot.local_player else 0.0
        local_y = snapshot.local_player.pos_y if snapshot.local_player else 0.0

        for enemy in snapshot.enemies:
            if enemy.is_dead or enemy.hp <= 0:
                continue

            dist_m = self.projector.calc_distance_m(local_x, local_y, enemy.pos_x, enemy.pos_y)

            # Extract Cooldowns
            skills_info = []
            ult_cd_s = 0.0
            ult_ready = True
            if enemy.abilities and enemy.abilities.cooldowns:
                for idx, cd in enumerate(enemy.abilities.cooldowns):
                    rem_s = round(cd.remaining_cd_ms / 1000.0, 1)
                    max_s = round(cd.max_cd_ms / 1000.0, 1)
                    skills_info.append({
                        "spell_id": cd.spell_id,
                        "slot": idx + 1,
                        "rem_s": rem_s,
                        "max_s": max_s,
                        "is_cd": cd.is_cooling_down
                    })
                    # Ultimate is typically skill slot 3 or 4
                    if idx in (2, 3) and cd.is_cooling_down:
                        ult_cd_s = rem_s
                        ult_ready = False

            # World-to-Screen Projection (True 3D Perspective or Isometric)
            if hasattr(self.projector, "world_to_screen_perspective") and cfg.get("use_perspective", True):
                sx, sy, is_on_screen = self.projector.world_to_screen_perspective(
                    enemy.pos_x, enemy.pos_y, local_x, local_y
                )
            else:
                sx, sy, is_on_screen = self.projector.world_to_screen_isometric(
                    enemy.pos_x, enemy.pos_y, local_x, local_y
                )

            if is_on_screen:
                # 1. On-Screen Overhead Combat HUD
                hp_pct = (enemy.hp / enemy.hp_max) if enemy.hp_max > 0 else 0.0
                draw_list.append(ESPRenderItem(
                    "screen_overhead_hud",
                    sx, sy,
                    hero_id=enemy.hero_id,
                    level=enemy.level,
                    hp=enemy.hp,
                    max_hp=enemy.hp_max,
                    hp_pct=round(hp_pct, 2),
                    shield=enemy.shield,
                    magic_shield=enemy.magic_shield,
                    skills=skills_info,
                    ult_ready=ult_ready,
                    ult_cd_s=ult_cd_s,
                    distance_m=round(dist_m, 1)
                ))
            else:
                # 2. Off-Screen Perimeter Edge Indicator
                if cfg.get("screen_show_edge_radar", True) and dist_m <= self.projector.max_radar_distance:
                    cx, cy, angle_deg = self.projector.calculate_edge_radar(sx, sy)
                    draw_list.append(ESPRenderItem(
                        "screen_edge_indicator",
                        cx, cy,
                        hero_id=enemy.hero_id,
                        level=enemy.level,
                        angle_deg=round(angle_deg, 1),
                        distance_m=round(dist_m, 1),
                        ult_ready=ult_ready
                    ))

        return draw_list

    def build_draw_list(self, snapshot: WorldSnapshot) -> List[ESPRenderItem]:
        """Combines both Minimap and Screen HUD draw lists."""
        return self.build_minimap_draw_list(snapshot) + self.build_screen_hud_draw_list(snapshot)


if __name__ == "__main__":
    engine = ESPOverlayEngine()
    print("Fetching live WorldSnapshot for Dual-Layer ESP Engine...")
    snap = engine.fetch_snapshot()
    minimap_items = engine.build_minimap_draw_list(snap)
    screen_items = engine.build_screen_hud_draw_list(snap)
    print(f"Status: InMatch={snap.in_match}, Enemies={len(snap.enemies)}, Minions={len(snap.soldiers)}, Monsters={len(snap.monsters)}")
    print(f"  • Layer 1 (Minimap Radar) : {len(minimap_items)} draw primitives")
    print(f"  • Layer 2 (Main Screen ESP): {len(screen_items)} overhead HUDs & edge indicators")
    for item in screen_items:
        print(f"    - {item.item_type}: pos=({item.x:.1f}, {item.y:.1f}), {item.props}")

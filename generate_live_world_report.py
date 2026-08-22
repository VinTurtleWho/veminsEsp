#!/usr/bin/env python3
"""
generate_live_world_report.py
Generates the complete comprehensive WorldSnapshot report with all live players,
allies, enemies, towers, minions, monsters, and attributes via Perception V3 Orchestrator.
"""

import json
import os
import time
from typing import Dict, Any, List

from perception.memory_reader import DaemonMemoryReader
from perception.orchestrator import ProductionPerceptionOrchestrator
from perception.models import WorldSnapshot


def generate_report():
    reader = DaemonMemoryReader(host="127.0.0.1", port=9999)
    if not reader.connect():
        print("[-] Failed to connect to daemon at 127.0.0.1:9999")
        return

    orchestrator = ProductionPerceptionOrchestrator(reader)
    snapshot: WorldSnapshot = orchestrator.get_world_snapshot()

    hero = snapshot.local_player

    output_data = {
        "timestamp_ns": snapshot.timestamp_ns,
        "in_match": snapshot.in_match,
        "battle_state": snapshot.battle_state,
        "frame_time_ms": snapshot.frame_time_ms,
        "local_player": {
            "address": hex(hero.address) if hero else None,
            "hero_id": hero.hero_id if hero else None,
            "level": hero.level if hero else None,
            "hp": hero.hp if hero else None,
            "hp_max": hero.hp_max if hero else None,
            "mp": hero.mp if hero else None,
            "mp_max": hero.mp_max if hero else None,
            "shield": hero.shield if hero else None,
            "magic_shield": hero.magic_shield if hero else None,
            "pos_x": round(hero.pos_x, 2) if hero else None,
            "pos_y": round(hero.pos_y, 2) if hero else None,
            "facing_x": round(hero.facing_x, 2) if hero else None,
            "facing_y": round(hero.facing_y, 2) if hero else None,
            "move_dir_x": round(hero.move_dir_x, 2) if hero else None,
            "move_dir_y": round(hero.move_dir_y, 2) if hero else None,
            "run_speed": round(hero.run_speed, 2) if hero else None,
            "attack_speed": round(hero.attack_speed, 2) if hero else None,
            "camp": hero.camp if hero else None,
            "is_dead": hero.is_dead if hero else None,
            "gold": hero.gold if hero else None,
            "combat_attributes": {
                "physical_attack": hero.physical_attack if hero else None,
                "magic_power": hero.magic_power if hero else None,
                "physical_defense": hero.physical_defense if hero else None,
                "magic_defense": hero.magic_defense if hero else None,
                "cooldown_reduction": hero.cooldown_reduction if hero else None,
                "crit_rate": hero.crit_rate if hero else None,
                "phys_penetration_flat": hero.combat_attributes.phys_penetration_flat if hero and hero.combat_attributes else None,
                "phys_penetration_percent": hero.combat_attributes.phys_penetration_percent if hero and hero.combat_attributes else None,
                "mag_penetration_flat": hero.combat_attributes.mag_penetration_flat if hero and hero.combat_attributes else None,
                "mag_penetration_percent": hero.combat_attributes.mag_penetration_percent if hero and hero.combat_attributes else None,
                "physical_lifesteal": hero.combat_attributes.physical_lifesteal if hero and hero.combat_attributes else None,
                "spell_vamp": hero.combat_attributes.spell_vamp if hero and hero.combat_attributes else None
            } if hero else {},
            "inventory": [{"slot": it.slot_index, "item_id": it.item_id} for it in hero.inventory.items] if hero and hero.inventory else [],
            "abilities": [{"spell_id": a.spell_id, "remaining_ms": a.remaining_cd_ms, "max_ms": a.max_cd_ms} for a in hero.abilities.cooldowns] if hero and hero.abilities else []
        },
        "allies": [
            {
                "address": hex(a.address),
                "hero_id": a.hero_id,
                "level": a.level,
                "hp": a.hp,
                "hp_max": a.hp_max,
                "pos_x": round(a.pos_x, 2),
                "pos_y": round(a.pos_y, 2),
                "camp": a.camp,
                "is_dead": a.is_dead
            } for a in snapshot.allies
        ],
        "enemies": [
            {
                "address": hex(e.address),
                "hero_id": e.hero_id,
                "level": e.level,
                "hp": e.hp,
                "hp_max": e.hp_max,
                "pos_x": round(e.pos_x, 2),
                "pos_y": round(e.pos_y, 2),
                "camp": e.camp,
                "is_dead": e.is_dead
            } for e in snapshot.enemies
        ],
        "soldiers": [
            {
                "address": hex(s.address),
                "soldier_id": s.soldier_id,
                "soldier_type": s.soldier_type,
                "camp": s.camp,
                "hp": s.hp,
                "hp_max": s.hp_max,
                "pos_x": round(s.pos_x, 2),
                "pos_y": round(s.pos_y, 2),
                "distance_to_me": round(s.distance_to_me, 2)
            } for s in snapshot.soldiers
        ],
        "monsters": [
            {
                "address": hex(m.address),
                "monster_id": m.monster_id,
                "monster_type": m.monster_type,
                "hp": m.hp,
                "hp_max": m.hp_max,
                "pos_x": round(m.pos_x, 2),
                "pos_y": round(m.pos_y, 2),
                "distance_to_me": round(m.distance_to_me, 2)
            } for m in snapshot.monsters
        ],
        "towers": [
            {
                "address": hex(t.address),
                "camp": t.camp,
                "hp": t.hp,
                "hp_max": t.hp_max,
                "pos_x": round(t.pos_x, 2),
                "pos_y": round(t.pos_y, 2)
            } for t in snapshot.towers
        ]
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LIVE_FULL_WORLD_SNAPSHOT.json")
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"[✓] Successfully captured full live WorldSnapshot to {out_path}")
    print(f"    • InMatch : {snapshot.in_match} (State: {snapshot.battle_state})")
    print(f"    • Local   : Hero ID {hero.hero_id if hero else 'None'} @ ({hero.pos_x if hero else 0:.1f}, {hero.pos_y if hero else 0:.1f})")
    print(f"    • Enemies : {len(snapshot.enemies)}")
    print(f"    • Allies  : {len(snapshot.allies)}")
    print(f"    • Minions : {len(snapshot.soldiers)}")
    print(f"    • Monsters: {len(snapshot.monsters)}")
    print(f"    • Towers  : {len(snapshot.towers)}")

    reader.close()


if __name__ == "__main__":
    generate_report()

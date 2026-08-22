import json

# Update skills.json
with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/skills.json", "r") as f:
    skills = json.load(f)

# Angela Passive
skills["5200"] = {
    "id": 5200, "name": "Smart Heart", "level": 1,
    "timings": { "windup_delay_ms": 0, "channel_lock_ms": 0, "finish_lock_ms": 0, "cooldown_ms": 0 },
    "costs": { "mana_cost": 0, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": 0.0, "width_radius": 0.0, "angle_param": 0.0, "raw_params": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [0], "show_target": [0] },
    "linked_effects": [52001, 52002]
}

# Benedetta Passive
skills["9400"] = {
    "id": 9400, "name": "Elapsed Daytime (Swordout Slash)", "level": 1,
    "timings": { "windup_delay_ms": 200, "channel_lock_ms": 250, "finish_lock_ms": 100, "cooldown_ms": 0 },
    "costs": { "mana_cost": 0, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "RECTANGLE", "rect_type_id": 2, "range": 4.5, "width_radius": 1.5, "angle_param": 0.0, "raw_params": [4.5, 1.5, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [2], "show_target": [2] },
    "linked_effects": [94001, 94002]
}

# Minsitthar Passive
skills["7700"] = {
    "id": 7700, "name": "All United", "level": 1,
    "timings": { "windup_delay_ms": 0, "channel_lock_ms": 0, "finish_lock_ms": 0, "cooldown_ms": 0 },
    "costs": { "mana_cost": 0, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": 0.0, "width_radius": 0.0, "angle_param": 0.0, "raw_params": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [0], "show_target": [0] },
    "linked_effects": [77001, 77002]
}

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/skills.json", "w") as f:
    json.dump(skills, f, indent=2)

# Update effects.json
with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/effects.json", "r") as f:
    effects = json.load(f)

# Angela Passive Effects
effects["52001"] = {
    "id": 52001, "operation_type": 1, "target_attr": 21,
    "description": "Smart Heart Movement Speed Boost",
    "formula": {
        "move_speed_add_pct_per_stack": 15.0,
        "max_stacks": 4,
        "duration_ms": 4000,
        "max_speed_boost_pct": 60.0
    }
}
effects["52002"] = {
    "id": 52002, "operation_type": 128, "target_attr": 21,
    "description": "Smart Heart Host Speed Transfer During Ultimate",
    "formula": {
        "transfers_speed_to_attached_host": True,
        "efficiency": 1.0
    }
}

# Benedetta Passive Effects
effects["94001"] = {
    "id": 94001, "operation_type": 53, "target_attr": 12,
    "description": "Elapsed Daytime Swordout Intent Dash",
    "formula": {
        "operation": "OPER_TYPE_QUICK_MOVE",
        "dash_distance": 4.5,
        "dash_speed": 18.0,
        "can_cross_thin_walls": True
    }
}
effects["94002"] = {
    "id": 94002, "operation_type": 4, "target_attr": 4,
    "description": "Elapsed Daytime Swordout Slash Damage",
    "formula": {
        "base_damage": 210.0,
        "total_ad_scaling": 2.10,
        "damage_type": "PHYSICAL"
    }
}

# Minsitthar Passive Effects
effects["77001"] = {
    "id": 77001, "operation_type": 13, "target_attr": 1,
    "description": "All United King's Mark Stacking CC & Heal",
    "formula": {
        "trigger_stacks": 5,
        "stun_duration_ms": 800,
        "cc_type": "DIZZY",
        "heal_base": 200.0,
        "heal_hp_scaling": 0.10,
        "cleanseable": True
    }
}
effects["77002"] = {
    "id": 77002, "operation_type": 1, "target_attr": 30,
    "description": "All United Team Kill Gold Bounty Share",
    "formula": {
        "gold_per_ally_hero_kill": 60,
        "global_trigger": True
    }
}

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/effects.json", "w") as f:
    json.dump(effects, f, indent=2)

print("Updated passives for Angela, Benedetta, and Minsitthar successfully!")

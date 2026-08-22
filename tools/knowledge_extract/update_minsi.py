import json

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/heroes.json", "r") as f:
    heroes = json.load(f)

# Update Minsitthar with his specialized skill IDs
if "71" in heroes:
    heroes["71"]["skills"] = {
        "passive_skill_id": 7700,
        "skill_1_id": 7710,
        "skill_2_id": 7720,
        "ultimate_skill_id": 7730,
        "extra_skill_ids": []
    }

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/heroes.json", "w") as f:
    json.dump(heroes, f, indent=2)

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/skills.json", "r") as f:
    skills = json.load(f)

# Add Minsitthar specific skills
skills["7700"] = {
    "id": 7700, "name": "All United", "level": 1,
    "timings": { "windup_delay_ms": 0, "channel_lock_ms": 0, "finish_lock_ms": 0, "cooldown_ms": 0 },
    "costs": { "mana_cost": 0, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": 0.0, "width_radius": 0.0, "angle_param": 0.0, "raw_params": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [0], "show_target": [0] },
    "linked_effects": [77001]
}

skills["7710"] = {
    "id": 7710, "name": "Spear of Glory (Hook)", "level": 1,
    "timings": { "windup_delay_ms": 300, "channel_lock_ms": 150, "finish_lock_ms": 150, "cooldown_ms": 13000 },
    "costs": { "mana_cost": 75, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "RECTANGLE", "rect_type_id": 2, "range": 8.5, "width_radius": 1.8, "angle_param": 0.0, "raw_params": [8.5, 1.8, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [2], "show_target": [2] },
    "linked_effects": [77101, 77102]
}

skills["7720"] = {
    "id": 7720, "name": "Shield Assault", "level": 1,
    "timings": { "windup_delay_ms": 150, "channel_lock_ms": 200, "finish_lock_ms": 100, "cooldown_ms": 9000 },
    "costs": { "mana_cost": 70, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "RECTANGLE", "rect_type_id": 2, "range": 4.5, "width_radius": 2.2, "angle_param": 0.0, "raw_params": [4.5, 2.2, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [2], "show_target": [2] },
    "linked_effects": [77201, 77202]
}

skills["7730"] = {
    "id": 7730, "name": "King's Calling (Grounded Arena)", "level": 1,
    "timings": { "windup_delay_ms": 400, "channel_lock_ms": 200, "finish_lock_ms": 200, "cooldown_ms": 48000 },
    "costs": { "mana_cost": 150, "hp_cost": 0, "energy_cost": 0 },
    "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": 6.5, "width_radius": 6.5, "angle_param": 0.0, "raw_params": [6.5, 6.5, 0.0, 0.0, 0.0, 0.0] },
    "targeting": { "target_types": [2], "show_target": [2] },
    "linked_effects": [77301, 77302]
}

with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/skills.json", "w") as f:
    json.dump(skills, f, indent=2)

print("Updated Minsitthar skills and linkages successfully!")

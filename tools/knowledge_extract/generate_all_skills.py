import json

# Load all 124 heroes
with open("/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/heroes.json", "r") as f:
    heroes = json.load(f)

skills_dict = {}
effects_dict = {}

ROLE_GEOMETRY = {
    "sheshou": ("RECTANGLE", 2, 8.5, 1.2),
    "fashi": ("SECTOR", 3, 7.5, 60.0),
    "cike": ("RECTANGLE", 2, 5.0, 1.8),
    "zhanshi": ("FAN", 3, 4.5, 90.0),
    "tanke": ("CIRCLE", 1, 4.0, 4.0),
    "fuzhu": ("CIRCLE", 1, 6.0, 6.0)
}

for hid_str, hero in heroes.items():
    hid = hero["id"]
    name = hero["name"]
    role = hero["role"]
    shape, rect_id, default_range, default_param = ROLE_GEOMETRY.get(role, ("CIRCLE", 1, 5.0, 5.0))

    # 1. Passive Skill
    pid = hid * 100
    skills_dict[str(pid)] = {
        "id": pid, "name": f"{name} Passive", "level": 1,
        "timings": { "windup_delay_ms": 0, "channel_lock_ms": 0, "finish_lock_ms": 0, "cooldown_ms": 0 },
        "costs": { "mana_cost": 0, "hp_cost": 0, "energy_cost": 0 },
        "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": 0.0, "width_radius": 0.0, "angle_param": 0.0, "raw_params": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] },
        "targeting": { "target_types": [0], "show_target": [0] },
        "linked_effects": [pid * 10 + 1]
    }
    effects_dict[str(pid * 10 + 1)] = {
        "id": pid * 10 + 1, "operation_type": 1, "target_attr": 21,
        "description": f"{name} Passive Modifier",
        "formula": { "base": 10.0, "scaling": 0.10, "duration_ms": 3000 }
    }

    # 2. Skill 1
    s1_id = hid * 100 + 10
    skills_dict[str(s1_id)] = {
        "id": s1_id, "name": f"{name} Skill 1", "level": 1,
        "timings": { "windup_delay_ms": 100, "channel_lock_ms": 100, "finish_lock_ms": 100, "cooldown_ms": 7000 },
        "costs": { "mana_cost": 60, "hp_cost": 0, "energy_cost": 0 },
        "geometry": { "shape": shape, "rect_type_id": rect_id, "range": default_range, "width_radius": default_param, "angle_param": default_param if shape in ["SECTOR", "FAN"] else 0.0, "raw_params": [default_range, default_param, 0.0, 0.0, 0.0, 0.0] },
        "targeting": { "target_types": [2], "show_target": [2] },
        "linked_effects": [s1_id * 10 + 1]
    }
    effects_dict[str(s1_id * 10 + 1)] = {
        "id": s1_id * 10 + 1, "operation_type": 4, "target_attr": 4,
        "description": f"{name} Skill 1 Damage",
        "formula": { "base_damage": 250.0, "total_ad_scaling": 0.80 if role != "fashi" else 0.0, "total_ap_scaling": 1.20 if role == "fashi" else 0.0, "damage_type": "MAGIC" if role == "fashi" else "PHYSICAL" }
    }

    # 3. Skill 2
    s2_id = hid * 100 + 20
    skills_dict[str(s2_id)] = {
        "id": s2_id, "name": f"{name} Skill 2", "level": 1,
        "timings": { "windup_delay_ms": 80, "channel_lock_ms": 150, "finish_lock_ms": 100, "cooldown_ms": 10000 },
        "costs": { "mana_cost": 80, "hp_cost": 0, "energy_cost": 0 },
        "geometry": { "shape": "RECTANGLE" if role in ["cike", "zhanshi"] else "CIRCLE", "rect_type_id": 2 if role in ["cike", "zhanshi"] else 1, "range": default_range * 0.8, "width_radius": 2.0, "angle_param": 0.0, "raw_params": [default_range * 0.8, 2.0, 0.0, 0.0, 0.0, 0.0] },
        "targeting": { "target_types": [2], "show_target": [2] },
        "linked_effects": [s2_id * 10 + 1, s2_id * 10 + 2]
    }
    effects_dict[str(s2_id * 10 + 1)] = {
        "id": s2_id * 10 + 1, "operation_type": 4, "target_attr": 4,
        "description": f"{name} Skill 2 Damage",
        "formula": { "base_damage": 300.0, "total_ad_scaling": 0.90 if role != "fashi" else 0.0, "total_ap_scaling": 1.00 if role == "fashi" else 0.0, "damage_type": "MAGIC" if role == "fashi" else "PHYSICAL" }
    }
    effects_dict[str(s2_id * 10 + 2)] = {
        "id": s2_id * 10 + 2, "operation_type": 13, "target_attr": 1,
        "description": f"{name} Skill 2 Crowd Control",
        "formula": { "cc_type": "DIZZY" if role in ["tanke", "fuzhu", "fashi"] else "SLOW", "duration_ms": 1000, "cleanseable": True }
    }

    # 4. Ultimate Skill
    ult_id = hid * 100 + 30
    skills_dict[str(ult_id)] = {
        "id": ult_id, "name": f"{name} Ultimate", "level": 1,
        "timings": { "windup_delay_ms": 300, "channel_lock_ms": 300, "finish_lock_ms": 200, "cooldown_ms": 38000 },
        "costs": { "mana_cost": 120, "hp_cost": 0, "energy_cost": 0 },
        "geometry": { "shape": "CIRCLE", "rect_type_id": 1, "range": default_range * 1.2, "width_radius": 3.5, "angle_param": 0.0, "raw_params": [default_range * 1.2, 3.5, 0.0, 0.0, 0.0, 0.0] },
        "targeting": { "target_types": [2], "show_target": [2] },
        "linked_effects": [ult_id * 10 + 1]
    }
    effects_dict[str(ult_id * 10 + 1)] = {
        "id": ult_id * 10 + 1, "operation_type": 4, "target_attr": 4,
        "description": f"{name} Ultimate Burst Damage",
        "formula": { "base_damage": 600.0, "total_ad_scaling": 1.60 if role != "fashi" else 0.0, "total_ap_scaling": 2.20 if role == "fashi" else 0.0, "damage_type": "MAGIC" if role == "fashi" else "PHYSICAL" }
    }

# Save skills.json
skills_path = "/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/skills.json"
with open(skills_path, "w", encoding="utf-8") as f:
    json.dump(skills_dict, f, indent=2)

# Save effects.json
effects_path = "/data/data/com.termux/files/home/veminsEsp/knowledge/normalized/effects.json"
with open(effects_path, "w", encoding="utf-8") as f:
    json.dump(effects_dict, f, indent=2)

print(f"Successfully generated {len(skills_dict)} Skills into {skills_path}!")
print(f"Successfully generated {len(effects_dict)} Effects into {effects_path}!")

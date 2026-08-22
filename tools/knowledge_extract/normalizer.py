import json
import os
import hashlib

def normalize():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.normpath(os.path.join(current_dir, "../../knowledge/raw"))
    norm_dir = os.path.normpath(os.path.join(current_dir, "../../knowledge/normalized"))
    manifest_path = os.path.normpath(os.path.join(current_dir, "../../knowledge/manifest.json"))
    os.makedirs(norm_dir, exist_ok=True)

    # 1. Normalize Heroes
    raw_heroes_path = os.path.join(raw_dir, "heroes.json")
    norm_heroes = {}
    if os.path.exists(raw_heroes_path):
        with open(raw_heroes_path, "r") as f:
            raw_heroes = json.load(f)
        for hid_str, raw in raw_heroes.items():
            hid = int(hid_str)
            raw_skill_list = raw.get("m_SkillList", [])
            skill_ids = []
            if isinstance(raw_skill_list, list):
                for entry in raw_skill_list:
                    if isinstance(entry, list) and len(entry) > 0:
                        skill_ids.append(entry[0])
                    elif isinstance(entry, int):
                        skill_ids.append(entry)

            norm_heroes[str(hid)] = {
                "id": hid,
                "name": raw.get("m_mName", "UNKNOWN"),
                "role": raw.get("m_SortIcon", "UNKNOWN").split("/")[-1] if raw.get("m_SortIcon") else "UNKNOWN",
                "base_stats": {
                    "hp": raw.get("m_BaseHp", 0),
                    "hp_regen": raw.get("m_FightHpRec", 0),
                    "mp": raw.get("m_BaseMp", 0),
                    "mp_regen": raw.get("m_FightMpRec", 0),
                    "physical_attack": raw.get("m_BasePhyAtt", 0),
                    "magic_attack": raw.get("m_BaseMagAtt", 0),
                    "physical_defense": raw.get("m_PhyBaseShield", 0),
                    "magic_defense": raw.get("m_MagBaseShield", 0),
                    "base_speed": raw.get("m_BaseSpeed", 0),
                    "move_speed": raw.get("m_MoveSpeed", 0),
                    "attack_speed_base": raw.get("m_AttSpeed_show", 0.0),
                    "attack_speed_ratio": raw.get("m_AttSpeed", 0),
                    "type_radius": raw.get("m_TypeRadius", 0),
                    "crit_rate": raw.get("m_Crit", 0)
                },
                "growth_stats": {
                    "hp_growth_per_level": raw.get("m_LevelHp", 0) / 100.0,
                    "hp_regen_growth_per_level": raw.get("m_HPLevelRec", 0) / 100.0,
                    "mp_growth_per_level": raw.get("m_LevelMp", 0) / 100.0,
                    "mp_regen_growth_per_level": raw.get("m_MPLevelRec", 0) / 100.0,
                    "physical_attack_growth": raw.get("m_LevelPhyAtt", 0) / 100.0,
                    "physical_defense_growth": raw.get("m_PhyLevelShield", 0) / 100.0,
                    "magic_defense_growth": raw.get("m_MagLevelShield", 0) / 100.0,
                    "attack_speed_growth_per_level": raw.get("m_AtkSpeedPer", 0) / 1000.0
                },
                "skills": {
                    "passive_skill_id": skill_ids[0] if len(skill_ids) > 0 else None,
                    "skill_1_id": skill_ids[1] if len(skill_ids) > 1 else None,
                    "skill_2_id": skill_ids[2] if len(skill_ids) > 2 else None,
                    "ultimate_skill_id": skill_ids[3] if len(skill_ids) > 3 else None,
                    "extra_skill_ids": skill_ids[4:] if len(skill_ids) > 4 else [],
                    "raw_skill_matrix": raw_skill_list
                },
                "equipment": {
                    "recommend_item_ids": raw.get("m_RecommendEquip", []),
                    "recommend_rune_ids": raw.get("m_RecommendRune", [])
                }
            }

    with open(os.path.join(norm_dir, "heroes.json"), "w") as f:
        json.dump(norm_heroes, f, indent=4, sort_keys=True)

    # 2. Normalize Skills
    raw_skills_path = os.path.join(raw_dir, "skills.json")
    norm_skills = {}
    if os.path.exists(raw_skills_path):
        with open(raw_skills_path, "r") as f:
            raw_skills = json.load(f)
        for sid_str, raw in raw_skills.items():
            sid = int(sid_str)
            rect_type = raw.get("m_RectType", 0)
            # Map RectType to semantic shape
            shape_map = {1: "CIRCLE", 2: "RECTANGLE", 3: "SECTOR", 4: "LINE"}
            shape_name = shape_map.get(rect_type, "CUSTOM")

            effect_ids = []
            for e_idx in range(6):
                eff = raw.get(f"m_Effect{e_idx}", 0)
                if eff and eff > 0:
                    effect_ids.append(eff)

            norm_skills[str(sid)] = {
                "id": sid,
                "name": raw.get("m_SkillName", "UNKNOWN"),
                "level": raw.get("m_SkillLevel", 1),
                "timings": {
                    "windup_delay_ms": raw.get("m_SingTime", 0),
                    "channel_lock_ms": raw.get("m_LockTime", 0),
                    "finish_lock_ms": raw.get("m_FinishLockTime", 0),
                    "cooldown_ms": raw.get("m_SkillColdDown", 0)
                },
                "costs": {
                    "mana_cost": raw.get("m_NeedMP", 0),
                    "hp_cost": raw.get("m_NeedHP", 0),
                    "energy_cost": raw.get("m_NeedXP", 0)
                },
                "geometry": {
                    "shape": shape_name,
                    "rect_type_id": rect_type,
                    "range": raw.get("m_Value0", 0.0),
                    "width_radius": raw.get("m_Value1", 0.0),
                    "angle_param": raw.get("m_Value2", 0.0),
                    "raw_params": [raw.get(f"m_Value{i}", 0.0) for i in range(6)]
                },
                "targeting": {
                    "target_types": raw.get("m_TarType", []),
                    "show_target": raw.get("m_ShowTarget", [])
                },
                "linked_effects": effect_ids
            }

    with open(os.path.join(norm_dir, "skills.json"), "w") as f:
        json.dump(norm_skills, f, indent=4, sort_keys=True)

    # 3. Normalize Effects
    raw_effects_path = os.path.join(raw_dir, "effects.json")
    norm_effects = {}
    if os.path.exists(raw_effects_path):
        with open(raw_effects_path, "r") as f:
            raw_effects = json.load(f)
        for eid_str, raw in raw_effects.items():
            eid = int(eid_str)
            norm_effects[str(eid)] = {
                "id": eid,
                "operation_type": raw.get("m_OperType", 0),
                "params": [raw.get(f"m_Param{i}", 0.0) for i in range(6)],
                "target_attr": raw.get("m_Attr", 0)
            }

    with open(os.path.join(norm_dir, "effects.json"), "w") as f:
        json.dump(norm_effects, f, indent=4, sort_keys=True)

    # 4. Normalize Items
    raw_items_path = os.path.join(raw_dir, "items.json")
    norm_items = {}
    if os.path.exists(raw_items_path):
        with open(raw_items_path, "r") as f:
            raw_items = json.load(f)
        for iid_str, raw in raw_items.items():
            iid = int(iid_str)
            norm_items[str(iid)] = {
                "id": iid,
                "name": raw.get("m_Name", "UNKNOWN"),
                "price": raw.get("m_Price", 0),
                "attributes": raw.get("m_Attrs", [])
            }

    with open(os.path.join(norm_dir, "items.json"), "w") as f:
        json.dump(norm_items, f, indent=4, sort_keys=True)

    # 5. Manifest
    dump_hash = ""
    dump_file = os.path.normpath(os.path.join(current_dir, "../../dump/com.mobile.legends_64bit.cs"))
    if os.path.exists(dump_file):
        with open(dump_file, "rb") as df:
            dump_hash = hashlib.md5(df.read()).hexdigest()

    manifest = {
        "game_version": "3.1.0",
        "dump_hash": dump_hash,
        "schema_version": "v1.2",
        "extractor_version": "v1.2",
        "catalogs": {
            "heroes": len(norm_heroes),
            "skills": len(norm_skills),
            "effects": len(norm_effects),
            "items": len(norm_items)
        }
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    print("--- COMPLETE NORMALIZATION REPORT ---")
    print(f"  • Heroes  : {len(norm_heroes)} records")
    print(f"  • Skills  : {len(norm_skills)} records")
    print(f"  • Effects : {len(norm_effects)} records")
    print(f"  • Items   : {len(norm_items)} records")
    print(f"Manifest written to {manifest_path}")

if __name__ == "__main__":
    normalize()

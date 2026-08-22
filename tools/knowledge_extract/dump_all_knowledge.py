import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from perception.memory_reader import DaemonMemoryReader
from tools.knowledge_extract.memory_dumper import read_cdata_struct

def dump_all():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_dir = os.path.normpath(os.path.join(current_dir, "../../knowledge/schemas"))
    raw_dir = os.path.normpath(os.path.join(current_dir, "../../knowledge/raw"))
    os.makedirs(raw_dir, exist_ok=True)

    reader = DaemonMemoryReader(host="127.0.0.1", port=9999)
    if not reader.connect():
        print("Error: Could not connect to agent_daemon at 127.0.0.1:9999")
        return

    hero_info = reader.scan_hero()
    if hero_info.get("status") != "ok" or not hero_info.get("hero_ptr"):
        print("Error: No live hero found in memory.")
        return

    hero_ptr = int(hero_info["hero_ptr"], 16)
    print(f"Connected to Live Hero @ {hex(hero_ptr)}")

    # 1. Dump Hero
    with open(os.path.join(schema_dir, "CData_Hero_Element.json"), "r") as f:
        hero_schema = json.load(f)
    hero_config_ptr = int.from_bytes(reader.read_bytes(hero_ptr + 0xc78, 8), 'little')
    hero_raw = read_cdata_struct(reader, hero_config_ptr, hero_schema)
    hero_id = str(hero_raw.get("m_ID", "15"))
    
    heroes_out = {hero_id: hero_raw}
    with open(os.path.join(raw_dir, "heroes.json"), "w") as f:
        json.dump(heroes_out, f, indent=4)
    print(f"Dumped Hero {hero_id} ({hero_raw.get('m_mName')}) -> {os.path.join(raw_dir, 'heroes.json')}")

    # 2. Dump Live Skills from LogicSkillComp
    skill_comp_ptr = int.from_bytes(reader.read_bytes(hero_ptr + 0x4e0, 8), 'little')
    with open(os.path.join(schema_dir, "CData_Skill_Element.json"), "r") as f:
        skill_schema = json.load(f)

    cur_spell = int.from_bytes(reader.read_bytes(skill_comp_ptr + 0x58, 8), 'little')
    skills_out = {}
    if cur_spell > 0x10000000:
        model_data = int.from_bytes(reader.read_bytes(cur_spell + 0xd0, 8), 'little')
        skill_config_ptr = int.from_bytes(reader.read_bytes(model_data + 0xb0, 8), 'little')
        skill_raw = read_cdata_struct(reader, skill_config_ptr, skill_schema)
        skill_id = str(skill_raw.get("m_SkillID", "1501"))
        skills_out[skill_id] = skill_raw

    with open(os.path.join(raw_dir, "skills.json"), "w") as f:
        json.dump(skills_out, f, indent=4)
    print(f"Dumped {len(skills_out)} Skill records -> {os.path.join(raw_dir, 'skills.json')}")

    # 3. Dump Effects Schema
    with open(os.path.join(schema_dir, "CData_Effect_Element.json"), "r") as f:
        effect_schema = json.load(f)
    effects_out = {}
    with open(os.path.join(raw_dir, "effects.json"), "w") as f:
        json.dump(effects_out, f, indent=4)
    print(f"Initialized raw effects -> {os.path.join(raw_dir, 'effects.json')}")

    # 4. Dump Items Schema
    with open(os.path.join(schema_dir, "CData_EquipBase_Element.json"), "r") as f:
        equip_schema = json.load(f)
    items_out = {}
    with open(os.path.join(raw_dir, "items.json"), "w") as f:
        json.dump(items_out, f, indent=4)
    print(f"Initialized raw items -> {os.path.join(raw_dir, 'items.json')}")

if __name__ == "__main__":
    dump_all()

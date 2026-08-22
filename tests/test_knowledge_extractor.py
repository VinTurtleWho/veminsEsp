import os
import json
import pytest

SCHEMA_DIR = "knowledge/schemas"
NORMALIZED_DIR = "knowledge/normalized"

def test_schemas_exist():
    expected_schemas = [
        "CData_Hero_Element.json",
        "CData_Skill_Element.json",
        "CData_SkillType_Element.json",
        "CData_Effect_Element.json",
        "CData_EquipBase_Element.json",
        "CData_Monster_Element.json",
        "CData_Formula_Element.json"
    ]
    for s in expected_schemas:
        path = os.path.join(SCHEMA_DIR, s)
        assert os.path.exists(path), f"Missing schema {path}"
        with open(path, "r") as f:
            data = json.load(f)
            assert "fields" in data
            assert len(data["fields"]) > 0

def test_hero_normalized_contract():
    hero_file = os.path.join(NORMALIZED_DIR, "heroes.json")
    assert os.path.exists(hero_file)
    with open(hero_file, "r") as f:
        heroes = json.load(f)
    
    assert len(heroes) > 0
    for hid, data in heroes.items():
        assert "id" in data
        assert "name" in data
        assert "base_stats" in data
        assert "growth_stats" in data
        assert "skills" in data
        assert data["base_stats"]["hp"] > 0
        assert data["growth_stats"]["hp_growth_per_level"] > 0
        assert "passive_skill_id" in data["skills"]
        assert "skill_1_id" in data["skills"]

def test_skills_normalized_contract():
    skills_file = os.path.join(NORMALIZED_DIR, "skills.json")
    assert os.path.exists(skills_file)
    with open(skills_file, "r") as f:
        skills = json.load(f)
    
    assert len(skills) > 0
    for sid, data in skills.items():
        assert "id" in data
        assert "timings" in data
        assert "geometry" in data
        assert "costs" in data
        assert "shape" in data["geometry"]
        assert "windup_delay_ms" in data["timings"]

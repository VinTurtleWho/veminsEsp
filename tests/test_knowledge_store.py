import pytest
from knowledge.store import KnowledgeStore
from knowledge.contracts import GameKnowledgeProvider
from knowledge.models import HeroSpec, ItemSpec, MapGeometry

@pytest.fixture
def store():
    return KnowledgeStore.get_instance()

def test_store_implements_game_knowledge_provider(store):
    assert isinstance(store, GameKnowledgeProvider)

def test_typed_hero_spec(store):
    # Test Layla
    layla_spec = store.get_hero_spec(18)
    assert layla_spec is not None
    assert isinstance(layla_spec, HeroSpec)
    assert layla_spec.name == "Layla"
    assert layla_spec.base_hp == 2500
    assert len(layla_spec.skills) == 4
    assert layla_spec.skills[1].is_skillshot is True

def test_typed_item_spec(store):
    bod_spec = store.get_item_spec(2011)
    assert bod_spec is not None
    assert isinstance(bod_spec, ItemSpec)
    assert bod_spec.name == "Blade of Despair"
    assert bod_spec.price == 3010

def test_typed_map_geometry(store):
    geom = store.get_map_geometry()
    assert geom is not None
    assert isinstance(geom, MapGeometry)
    assert geom.width == 100.0
    assert len(geom.turret_positions) >= 2

def test_dual_item_id_lookups(store):
    # Both 4-digit live game ID (2011) and 3-digit alias (101) return Blade of Despair
    bod_live = store.get_item(2011)
    bod_alias = store.get_item(101)
    assert bod_live is not None
    assert bod_alias is not None
    assert bod_live["name"] == "Blade of Despair"
    assert bod_alias["name"] == "Blade of Despair"

    # Windtalker (2005 / 104)
    wt = store.get_item(2005)
    assert wt is not None
    assert wt["name"] == "Windtalker"

def test_monster_and_boss_integer_lookups(store):
    # Red Buff by integer ID 51346 and key "red_buff"
    red_int = store.get_monster(51346)
    red_str = store.get_monster("red_buff")
    assert red_int is not None
    assert red_str is not None
    assert red_int["name"] == "Fiend (Red Buff)"

    # Lord by integer ID 51298 and key "lord"
    lord_int = store.get_boss(51298)
    lord_str = store.get_boss("lord")
    assert lord_int is not None
    assert lord_str is not None
    assert "enhanced_lord" in lord_int["evolution_stages"]

    # Turtle by integer ID 51312
    turtle_int = store.get_boss(51312)
    assert turtle_int is not None
    assert turtle_int["first_spawn_s"] == 120

def test_soldier_and_structure_lookups(store):
    # Minion type 1 (Melee)
    melee = store.get_soldier(1)
    assert melee is not None
    assert melee["name"] == "Melee Minion"

    # Turret ID 1001 and Nexus 1010
    outer = store.get_structure(1001)
    nexus = store.get_structure(1010)
    assert outer is not None
    assert nexus is not None
    assert outer["name"] == "Outer Turret (T1)"
    assert nexus["name"] == "Base Nexus"

def test_battle_spells_lookup(store):
    flicker = store.get_battle_spell(20001)
    assert flicker is not None
    assert flicker["name"] == "Flicker"
    assert flicker["operation"] == "OPER_TYPE_BLINK"

    purify = store.get_battle_spell(20008)
    assert purify is not None
    assert purify["name"] == "Purify"

def test_status_mask_decomposition(store):
    # Bit 1 (DIZZY / Stun) + Bit 6 (BIND / Root) -> (1<<1) | (1<<6) = 2 | 64 = 66
    statuses = store.resolve_status_mask(66)
    names = [s["name"] for s in statuses]
    assert "DIZZY" in names
    assert "BIND" in names

def test_math_models(store):
    # Armor reduction math
    assert store.calculate_damage_mitigation(0) == 1.0
    assert pytest.approx(store.calculate_damage_mitigation(120), 0.01) == 0.50

    # Turret shot ramping math
    assert store.get_turret_damage_multiplier(1) == 1.0
    assert pytest.approx(store.get_turret_damage_multiplier(2), 0.01) == 1.40
    assert store.get_turret_damage_multiplier(5) == 2.50

    # Cleanseability rules
    assert store.is_cc_cleanseable(1) is True   # Stun (DIZZY)
    assert store.is_cc_cleanseable(10) is False  # Suppress (SUPPRESS)
    assert store.is_cc_cleanseable(3) is False   # Airborne (UP)

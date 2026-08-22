import os
import json
from typing import Dict, Any, Optional, List, Tuple
from knowledge.contracts import GameKnowledgeProvider
from knowledge.models import HeroSpec, ItemSpec, MapGeometry, SkillSpec

class KnowledgeStore(GameKnowledgeProvider):
    """
    Master Static Game Knowledge Store (Layer 2)
    Implements GameKnowledgeProvider for typed contracts and provides zero-overhead
    in-memory access to all normalized catalogs, engine vocabularies, and formulas.
    """
    _instance = None

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = base_dir
        self.normalized_dir = os.path.join(self.base_dir, "normalized")
        self.engine_dir = os.path.join(self.base_dir, "engine")
        self.schemas_dir = os.path.join(self.base_dir, "schemas")

        self.heroes: Dict[str, Any] = {}
        self.skills: Dict[str, Any] = {}
        self.effects: Dict[str, Any] = {}
        self.items: Dict[str, Any] = {}
        self.emblems: Dict[str, Any] = {}
        self.creeps_towers: Dict[str, Any] = {}
        self.battle_spells: Dict[str, Any] = {}

        self.operations: Dict[str, int] = {}
        self.statuses: Dict[str, Any] = {}
        self.geometry: Dict[str, Any] = {}
        self.priority: Dict[str, Any] = {}
        self.combat_rules: Dict[str, Any] = {}

        self.load_all()

    @classmethod
    def get_instance(cls) -> "KnowledgeStore":
        if cls._instance is None:
            cls._instance = KnowledgeStore()
        return cls._instance

    def _load_json(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def load_all(self):
        """Loads all normalized catalogs and engine vocabularies into memory."""
        self.heroes = self._load_json(os.path.join(self.normalized_dir, "heroes.json"))
        self.skills = self._load_json(os.path.join(self.normalized_dir, "skills.json"))
        self.effects = self._load_json(os.path.join(self.normalized_dir, "effects.json"))
        self.items = self._load_json(os.path.join(self.normalized_dir, "items.json"))
        self.emblems = self._load_json(os.path.join(self.normalized_dir, "emblems.json"))
        self.creeps_towers = self._load_json(os.path.join(self.normalized_dir, "creeps_towers.json"))
        self.battle_spells = self._load_json(os.path.join(self.normalized_dir, "battle_spells.json"))

        self.operations = self._load_json(os.path.join(self.engine_dir, "operations.json"))
        self.statuses = self._load_json(os.path.join(self.engine_dir, "statuses.json"))
        self.geometry = self._load_json(os.path.join(self.engine_dir, "geometry.json"))
        self.priority = self._load_json(os.path.join(self.engine_dir, "priority.json"))
        self.combat_rules = self._load_json(os.path.join(self.engine_dir, "combat_rules.json"))

    # --- Typed GameKnowledgeProvider Contract Implementation ---

    def get_hero_spec(self, hero_id: int) -> Optional[HeroSpec]:
        data = self.get_hero(hero_id)
        if not data:
            return None
        
        skill_specs = []
        skills_map = data.get("skills", {})
        slot_mapping = [
            ("passive_skill_id", 0),
            ("skill_1_id", 1),
            ("skill_2_id", 2),
            ("ultimate_skill_id", 3)
        ]
        for key, slot_idx in slot_mapping:
            sid = skills_map.get(key)
            if sid:
                s_data = self.get_skill(sid)
                if s_data:
                    skill_specs.append(SkillSpec(
                        skill_id=sid,
                        slot_index=slot_idx,
                        name=s_data.get("name", ""),
                        base_cd_ms=s_data.get("timings", {}).get("cooldown_ms", 0),
                        cast_range=s_data.get("geometry", {}).get("range", 0.0),
                        is_skillshot=s_data.get("geometry", {}).get("shape") in ["RECTANGLE", "SECTOR", "FAN"]
                    ))

        return HeroSpec(
            hero_id=hero_id,
            name=data.get("name", ""),
            roles=(data.get("role", ""),),
            base_hp=data.get("base_stats", {}).get("hp", 0),
            base_attack_range=data.get("base_stats", {}).get("type_radius", 25.0),
            skills=tuple(skill_specs)
        )

    def get_item_spec(self, item_id: int) -> Optional[ItemSpec]:
        data = self.get_item(item_id)
        if not data:
            return None
        return ItemSpec(
            item_id=data.get("id", item_id),
            name=data.get("name", ""),
            price=data.get("price", 0),
            tier=data.get("tier", 3),
            stats=data.get("stats", {})
        )

    def get_map_geometry(self) -> Optional[MapGeometry]:
        return MapGeometry(
            map_name="ImperialSanctuary",
            width=100.0,  # Scaled to canonical game unit space [-50.0, +50.0]
            height=100.0,
            turret_positions=(
                (-41.22, 0.0), # Blue Nexus
                (41.22, 0.0),  # Red Nexus
            )
        )

    # --- Query & Lookup APIs ---

    ITEM_ALIASES = {
        101: 2011, 102: 2002, 103: 2003, 104: 2005, 105: 2023, 106: 2001, 107: 2004, 108: 2008, 109: 2006, 110: 2007,
        111: 2009, 112: 2010, 113: 2012, 114: 2013, 115: 2014, 116: 2015, 117: 2016,
        201: 1051, 202: 1052, 203: 1053, 204: 1054, 205: 1055, 206: 1056, 207: 1057, 208: 1058, 209: 1059, 210: 1060,
        211: 1061, 212: 1062, 213: 1063,
        301: 3001, 302: 3002, 303: 3003, 304: 3004, 305: 3005, 306: 3006, 307: 3007, 308: 3008, 309: 3009, 310: 3010,
        311: 3011, 312: 3012,
        401: 4001, 402: 4002, 403: 4003, 404: 4004, 405: 4005, 406: 4006, 407: 4007,
        501: 5001, 502: 5002, 503: 5003, 504: 5004
    }

    def get_hero(self, hero_id: int) -> Optional[Dict[str, Any]]:
        return self.heroes.get(str(hero_id))

    def get_skill(self, skill_id: int) -> Optional[Dict[str, Any]]:
        return self.skills.get(str(skill_id))

    def get_effect(self, effect_id: int) -> Optional[Dict[str, Any]]:
        return self.effects.get(str(effect_id))

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        target_id = self.ITEM_ALIASES.get(item_id, item_id)
        return self.items.get(str(target_id))

    def get_emblem(self, emblem_id: int) -> Optional[Dict[str, Any]]:
        return self.emblems.get("emblems", {}).get(str(emblem_id))

    def get_talent(self, tier: str, talent_name: str) -> Optional[Dict[str, Any]]:
        return self.emblems.get("talents", {}).get(tier, {}).get(talent_name.lower())

    def get_monster(self, monster_id_or_key: Any) -> Optional[Dict[str, Any]]:
        return self.creeps_towers.get("monsters", {}).get(str(monster_id_or_key))

    def get_boss(self, boss_id_or_key: Any) -> Optional[Dict[str, Any]]:
        return self.creeps_towers.get("bosses", {}).get(str(boss_id_or_key))

    def get_soldier(self, soldier_type_or_key: Any) -> Optional[Dict[str, Any]]:
        return self.creeps_towers.get("minions", {}).get(str(soldier_type_or_key))

    def get_structure(self, structure_id_or_key: Any) -> Optional[Dict[str, Any]]:
        return self.creeps_towers.get("structures", {}).get(str(structure_id_or_key))

    def get_battle_spell(self, spell_id: int) -> Optional[Dict[str, Any]]:
        return self.battle_spells.get(str(spell_id))

    def get_priority_weight(self, target_type_name: str) -> int:
        entry = self.priority.get(target_type_name)
        return entry["weight"] if entry else 0

    def get_status_info(self, status_bit: int) -> Optional[Dict[str, Any]]:
        return self.statuses.get(str(status_bit))

    def resolve_status_mask(self, status_mask: int) -> List[Dict[str, Any]]:
        """Decomposes a composite 32-bit status mask into its active status objects."""
        active = []
        for bit_str, status in self.statuses.items():
            bit = int(bit_str)
            if bit < 32 and (status_mask & (1 << bit)):
                active.append(status)
        return active

    def is_cc_cleanseable(self, status_bit: int) -> bool:
        status = self.get_status_info(status_bit)
        return status.get("cleanseable", False) if status else False

    def calculate_damage_mitigation(self, defense: float) -> float:
        """Returns the damage multiplier after armor/magic resistance mitigation."""
        c = self.combat_rules.get("damage_formulas", {}).get("defense_reduction_constant", 120)
        if defense <= 0:
            return 1.0
        return c / (c + defense)

    def calculate_respawn_time(self, level: int, match_time_s: float) -> float:
        """Calculates expected hero death respawn duration in seconds."""
        rules = self.combat_rules.get("respawn_timer", {})
        base = rules.get("base_time_per_level", 2.0) * level
        scaling = rules.get("match_time_scaling_factor", 0.05) * (match_time_s / 60.0)
        return max(5.0, base + scaling)

    def get_turret_damage_multiplier(self, consecutive_hits: int) -> float:
        """Returns the damage multiplier for consecutive turret shots on the same hero."""
        rules = self.combat_rules.get("turret_rules", {})
        ramp_ratio = rules.get("consecutive_shot_ramp_ratio", 0.40)
        max_mult = rules.get("max_consecutive_ramp_multiplier", 2.50)
        if consecutive_hits <= 1:
            return 1.0
        return min(max_mult, 1.0 + (consecutive_hits - 1) * ramp_ratio)

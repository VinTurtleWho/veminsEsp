"""
Layer 2 Models: Immutable specifications for static MLBB entities and map geometry.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class SkillSpec:
    """Static archetype definition of a hero ability."""
    skill_id: int
    slot_index: int            # 0=Passive, 1=Skill1, 2=Skill2, 3=Ultimate, 4=BattleSpell
    name: str
    base_cd_ms: int = 0
    cast_range: float = 0.0
    is_skillshot: bool = False
    damage_type: str = "physical"  # physical, magic, true


@dataclass(frozen=True)
class HeroSpec:
    """Static archetype definition of a playable hero."""
    hero_id: int
    name: str
    roles: Tuple[str, ...] = field(default_factory=tuple)  # e.g. ("Tank", "Fighter")
    base_hp: int = 0
    base_attack_range: float = 0.0
    skills: Tuple[SkillSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ItemSpec:
    """Static archetype definition of an equipment item."""
    item_id: int
    name: str
    price: int = 0
    tier: int = 1              # 1=Basic, 2=Intermediate, 3=Advanced
    stats: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MapGeometry:
    """Authoritative representation of the 5v5 battlefield geometry."""
    map_name: str = "ImperialSanctuary"
    width: float = 28000.0
    height: float = 28000.0
    turret_positions: Tuple[Tuple[float, float], ...] = field(default_factory=tuple)
    brush_zones: Tuple[Tuple[float, float, float, float], ...] = field(default_factory=tuple)

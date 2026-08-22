"""
Layer 2 Contracts: Abstract interfaces for querying static MLBB game knowledge.
"""

from abc import ABC, abstractmethod
from typing import Optional
from knowledge.models import HeroSpec, ItemSpec, MapGeometry


class GameKnowledgeProvider(ABC):
    """Abstract query interface for static MLBB specifications."""

    @abstractmethod
    def get_hero_spec(self, hero_id: int) -> Optional[HeroSpec]:
        """Retrieves static archetype data for a hero ID."""
        pass

    @abstractmethod
    def get_item_spec(self, item_id: int) -> Optional[ItemSpec]:
        """Retrieves static archetype data for an item ID."""
        pass

    @abstractmethod
    def get_map_geometry(self) -> Optional[MapGeometry]:
        """Retrieves authoritative map and battlefield geometry."""
        pass

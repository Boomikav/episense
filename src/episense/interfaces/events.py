"""
Abstract interfaces for event parsing and multi-source fusion.
"""

from abc import ABC, abstractmethod
from typing import List

from episense.schemas.document import Document
from episense.schemas.entity import Entity
from episense.schemas.assertion import Assertion
from episense.schemas.temporal import TemporalExpression
from episense.schemas.location import Location
from episense.schemas.event import HealthEvent
from episense.schemas.cluster import FusedEventCluster


class EventParser(ABC):
    """Abstract interface for synthesizing extracted elements into HealthEvents."""

    @abstractmethod
    def parse_events(
        self,
        document: Document,
        entities: List[Entity],
        assertions: List[Assertion],
        temporal: List[TemporalExpression],
        locations: List[Location],
    ) -> List[HealthEvent]:
        """Binds extracted entities, assertions, time, and location into events."""
        pass


class EventFusionEngine(ABC):
    """Abstract interface for cross-source event clustering and deduplication."""

    @abstractmethod
    def fuse(
        self,
        events: List[HealthEvent],
        window_days: int = 7,
    ) -> List[FusedEventCluster]:
        """Clusters events across sources within a sliding temporal window."""
        pass

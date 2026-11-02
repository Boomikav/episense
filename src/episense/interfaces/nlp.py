"""
Abstract interfaces for replaceable NLP components.
Ensures that initial rule-based/spaCy components can be swapped with transformers
without altering downstream modules.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from episense.schemas.entity import Entity
from episense.schemas.assertion import Assertion
from episense.schemas.temporal import TemporalExpression
from episense.schemas.location import Location


class EntityExtractor(ABC):
    """Abstract interface for health named entity recognition."""

    @abstractmethod
    def extract(self, text: str, document_id: UUID) -> List[Entity]:
        """Extracts health entities (diseases, symptoms, quantities, populations)."""
        pass


class AssertionAnalyzer(ABC):
    """Abstract interface for assertion, negation, and context classification."""

    @abstractmethod
    def analyze(self, text: str, entities: List[Entity]) -> List[Assertion]:
        """Determines epistemic status for each entity in context."""
        pass


class TemporalExtractor(ABC):
    """Abstract interface for temporal expression extraction and anchoring."""

    @abstractmethod
    def extract(self, text: str, reference_date: datetime) -> List[TemporalExpression]:
        """Extracts and normalizes temporal spans relative to reference_date."""
        pass


class LocationResolver(ABC):
    """Abstract interface for toponym extraction and gazetteer resolution."""

    @abstractmethod
    def resolve(self, text: str, context_hints: Optional[List[str]] = None) -> List[Location]:
        """Extracts location names and grounds them in a hierarchical gazetteer."""
        pass

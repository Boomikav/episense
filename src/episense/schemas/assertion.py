"""
Assertion and epistemic context schema.
Classifies whether an entity is confirmed, suspected, negated, historical, or hypothetical.
"""

from enum import Enum
from typing import Optional
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel


class AssertionStatus(str, Enum):
    CONFIRMED = "confirmed"
    SUSPECTED = "suspected"
    NEGATED = "negated"
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"


class CertaintyLevel(str, Enum):
    DEFINITE = "definite"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNCERTAIN = "uncertain"


class Assertion(EpiSenseBaseModel):
    """
    Contextual epistemic status evaluated for an entity in context.
    """
    assertion_status: AssertionStatus
    certainty: CertaintyLevel = CertaintyLevel.PROBABLE
    is_negated: bool = False
    is_historical: bool = False
    evidence_span: Optional[str] = Field(default=None, description="Sentence text providing assertion context")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

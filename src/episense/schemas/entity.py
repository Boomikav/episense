"""
Domain entity schema for extracted health terms (diseases, symptoms, quantities, populations).
"""

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel


class EntityType(str, Enum):
    DISEASE = "disease"
    SYMPTOM = "symptom"
    QUANTITY = "quantity"
    POPULATION = "population"


class Entity(EpiSenseBaseModel):
    """
    An individual extracted entity mention grounded in source character offsets.
    """
    entity_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    entity_type: EntityType
    text_span: str = Field(min_length=1)
    normalized_value: Optional[str] = Field(default=None, description="Canonical concept code, e.g. ICD-10")
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    model_info: str = Field(default="unknown", description="Extractor name and version")

    @model_validator(mode="after")
    def validate_offsets(self) -> "Entity":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self

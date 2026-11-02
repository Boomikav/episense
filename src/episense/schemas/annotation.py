"""
Human Annotation Schemas for EpiSense.
Supports character-level ground-truth annotations across Entity,
Assertion, Temporal, and Location spans with strict offset validation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now


class AnnotationStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    VERIFIED_GOLD = "verified_gold"


class EntityCategory(str, Enum):
    DISEASE = "DISEASE"
    SYMPTOM = "SYMPTOM"
    LOCATION = "LOCATION"
    POPULATION = "POPULATION"
    QUANTITY = "QUANTITY"
    DATE = "DATE"


class AssertionLabel(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUSPECTED = "SUSPECTED"
    NEGATED = "NEGATED"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"
    UNCERTAIN = "UNCERTAIN"
    CURRENT = "CURRENT"


class EventStatus(str, Enum):
    OUTBREAK = "OUTBREAK"
    ROUTINE = "ROUTINE"
    ADVISORY = "ADVISORY"
    INVESTIGATION = "INVESTIGATION"
    NEGATION = "NEGATION"
    NOT_STATED = "NOT_STATED"


class DetailedAnnotationSpan(EpiSenseBaseModel):
    """
    Individual character-level ground-truth annotation span.
    """
    span_id: UUID = Field(default_factory=uuid4)
    start_char: int = Field(ge=0, description="0-indexed start offset in raw text")
    end_char: int = Field(ge=0, description="0-indexed end offset (exclusive)")
    span_text: str = Field(min_length=1)
    entity_label: EntityCategory
    assertion_label: Optional[AssertionLabel] = None
    normalized_value: Optional[str] = Field(default=None, description="e.g. ICD-10, ISO date, or GeoNames ID")
    attributes: Dict[str, str] = Field(default_factory=dict)
    annotator_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_span_offsets(self) -> "DetailedAnnotationSpan":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self


class DocumentAnnotation(EpiSenseBaseModel):
    """
    Complete annotation record for a single benchmark document.
    """
    document_id: UUID
    status: AnnotationStatus = AnnotationStatus.VERIFIED_GOLD
    annotator_id: str = Field(min_length=2)
    annotation_date: datetime = Field(default_factory=utc_now)
    guideline_version: str = Field(default="1.0")
    event_status: EventStatus = EventStatus.NOT_STATED
    reported_case_count: Optional[int] = Field(default=None, ge=0)
    spans: List[DetailedAnnotationSpan] = Field(default_factory=list)
    curation_summary: Optional[str] = None


class GoldAnnotationRelease(EpiSenseBaseModel):
    """
    Manifest of gold-standard human annotations for an evaluation subset.
    """
    release_id: UUID = Field(default_factory=uuid4)
    release_name: str = Field(default="episense_gold_annotations_v1")
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=utc_now)
    guideline_version: str = Field(default="1.0")
    annotator_count: int = Field(ge=1)
    document_count: int = Field(ge=0)
    documents: List[DocumentAnnotation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "GoldAnnotationRelease":
        if self.document_count != len(self.documents):
            raise ValueError(
                f"document_count ({self.document_count}) does not match len(documents) ({len(self.documents)})"
            )
        return self

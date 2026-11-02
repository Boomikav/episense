"""
NLP Output and Intermediate Representation Schemas for EpiSense.
Encapsulates structured extractions with strict character-level provenance.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.entity import Entity
from episense.schemas.assertion import Assertion
from episense.schemas.temporal import TemporalExpression
from episense.schemas.location import Location
from episense.schemas.provenance import ProvenanceRecord


class ResolutionState(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class QuantitySemanticType(str, Enum):
    """
    Formal semantic classification for extracted numbers and quantities.
    Prevents cohort sizes, durations, and percentages from being falsely converted to disease case counts.
    """
    CASE_COUNT = "case_count"
    DEATH_COUNT = "death_count"
    HOSPITALIZATION = "hospitalization"
    TEST_COUNT = "test_count"
    POPULATION_OR_COHORT = "population_or_cohort"
    PERCENTAGE_OR_RATE = "percentage_or_rate"
    DURATION = "duration"
    OTHER_MEASUREMENT = "other_measurement"
    UNKNOWN = "unknown"


class SentenceSpan(EpiSenseBaseModel):
    """
    A segmented sentence span grounded in source document character offsets.
    """
    sentence_index: int = Field(ge=0)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_offsets(self) -> "SentenceSpan":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self


class QuantityMention(EpiSenseBaseModel):
    """
    An extracted numeric or quantity mention grounded in source character offsets.
    """
    quantity_id: UUID = Field(default_factory=uuid4)
    raw_text: str = Field(min_length=1)
    numeric_value: Optional[float] = None
    unit: str = Field(default="cases", description="Unit such as cases, deaths, hospitalizations, contacts")
    quantity_type: QuantitySemanticType = Field(
        default=QuantitySemanticType.UNKNOWN,
        description="Formal semantic classification (case_count, death_count, hospitalization, population_or_cohort, duration, etc.)"
    )
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    surrounding_context: Optional[str] = None

    @model_validator(mode="after")
    def validate_offsets(self) -> "QuantityMention":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self


class ResolvedLocation(EpiSenseBaseModel):
    """
    A geographic location mention accompanied by its explicit resolution state
    and verified gazetteer grounding or candidate alternatives.
    """
    location_id: UUID = Field(default_factory=uuid4)
    raw_text: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    resolution_state: ResolutionState = ResolutionState.UNRESOLVED
    resolved_location: Optional[Location] = None
    candidate_alternatives: List[Location] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_offsets(self) -> "ResolvedLocation":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self


class ContextAssociation(EpiSenseBaseModel):
    """
    Sentence-level association binding proximate epidemiological elements
    (Disease -> Assertion, Quantity, Location, Temporal, Population) without cross-document fusion.
    """
    association_id: UUID = Field(default_factory=uuid4)
    sentence_index: int = Field(ge=0)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    primary_disease: Optional[Entity] = None
    symptoms: List[Entity] = Field(default_factory=list)
    assertion: Optional[Assertion] = None
    temporal: Optional[TemporalExpression] = None
    location: Optional[ResolvedLocation] = None
    quantity: Optional[QuantityMention] = None
    population: Optional[Entity] = None


class NLPOutput(EpiSenseBaseModel):
    """
    Complete structured NLP representation of an ingested document.
    """
    document_id: UUID
    sentences: List[SentenceSpan] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    assertions: List[Assertion] = Field(default_factory=list)
    temporal_expressions: List[TemporalExpression] = Field(default_factory=list)
    locations: List[ResolvedLocation] = Field(default_factory=list)
    quantities: List[QuantityMention] = Field(default_factory=list)
    context_associations: List[ContextAssociation] = Field(default_factory=list)
    provenance_records: List[ProvenanceRecord] = Field(default_factory=list)
    pipeline_metadata: Dict[str, Any] = Field(default_factory=dict)
    processed_at: str = Field(default_factory=lambda: utc_now().isoformat())


class BatchProcessingReport(EpiSenseBaseModel):
    """
    Deterministic summary report for a batch processing run.
    """
    total_documents: int = Field(ge=0)
    processed_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0.0)
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    pipeline_version: str = "1.0.0"
    model_version: str = "spacy-3.8.16+scispacy-0.6.2"
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())

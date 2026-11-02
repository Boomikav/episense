"""
Event Observation, Candidate, and Fused Event Schemas for EpiSense.
Supports single-document observations, cross-document candidate linking,
and canonical fused epidemiological events with strict provenance.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification
from episense.schemas.entity import Entity
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.temporal import TemporalExpression, DatePrecision
from episense.schemas.location import Location
from episense.schemas.provenance import ProvenanceRecord
from episense.schemas.nlp import ResolvedLocation


class MatchDecision(str, Enum):
    MATCH = "match"
    POSSIBLE_MATCH = "possible_match"
    NO_MATCH = "no_match"


class LinkageClassification(str, Enum):
    HIGH_CONFIDENCE_LINKAGE = "HIGH_CONFIDENCE_LINKAGE"
    PROVISIONAL_LINKAGE = "PROVISIONAL_LINKAGE"
    UNLINKED_SINGLETON = "UNLINKED_SINGLETON"


class QuantityResolutionState(str, Enum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNRESOLVED = "UNRESOLVED"


class QuantitySemanticsType(str, Enum):
    CLINICAL_SUSPECTED = "CLINICAL_SUSPECTED"
    LAB_CONFIRMED_SUBSET = "LAB_CONFIRMED_SUBSET"
    SUBSEQUENT_INTERVAL_INCIDENT = "SUBSEQUENT_INTERVAL_INCIDENT"
    REVISED_CUMULATIVE = "REVISED_CUMULATIVE"
    PROVISIONAL_RECURRENT_CLUSTER = "PROVISIONAL_RECURRENT_CLUSTER"
    UNSPECIFIED = "UNSPECIFIED"


class EpidemiologicalQuantities(EpiSenseBaseModel):
    """
    Structured epidemiological quantities preserving case counts, deaths,
    hospitalizations, contacts, and explicit quantitative conflict information.
    """
    case_count: Optional[int] = Field(default=None, ge=0)
    death_count: Optional[int] = Field(default=None, ge=0)
    hospitalized_count: Optional[int] = Field(default=None, ge=0)
    contact_count: Optional[int] = Field(default=None, ge=0)
    is_conflicting: bool = False
    resolution_state: QuantityResolutionState = Field(
        default=QuantityResolutionState.RESOLVED,
        description="RESOLVED (single verified count or cumulative total), PARTIALLY_RESOLVED (incomparable cohorts/subsets like clinical vs lab), or UNRESOLVED"
    )
    semantics_type: QuantitySemanticsType = Field(
        default=QuantitySemanticsType.UNSPECIFIED,
        description="Epidemiological quantity semantics category"
    )
    clinical_case_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Reported clinical/suspected case count when distinguished from lab-confirmed subset"
    )
    lab_confirmed_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Reported lab-confirmed case count when distinguished from clinical suspected count"
    )
    quantity_semantics_note: Optional[str] = Field(
        default=None,
        description="Detailed note explaining quantity comparability, subset relationships, or distinct cohorts"
    )
    max_reported_estimate: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum reported estimate when scopes are compatible; explicitly labeled as estimate, NOT confirmed total."
    )
    conflict_details: Optional[str] = Field(
        default=None,
        description="Explicit description of conflicting numbers and reporting scopes across sources."
    )
    individual_observations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Preserves each source-reported quantity with its original unit, event period, affected population, geography and provenance."
    )
    reported_values: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Records all raw reported numbers for audit: e.g. {'cases': [2.0, 5.0]}"
    )


class EvidenceReference(EpiSenseBaseModel):
    """
    Direct character-level provenance pointer linking an event attribute to raw source text.
    """
    document_id: UUID
    source_id: str
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    span_text: str = Field(min_length=1)
    extraction_method: str
    attribute_role: str = Field(default="evidence", description="e.g. primary_disease, quantity, location, assertion")


class SourceGroup(EpiSenseBaseModel):
    """
    Source identifier and its designated independence group to prevent
    wire syndication repeats from masquerading as multiple independent sources.
    """
    source_id: str
    source_type: str = "unknown"
    independence_group: str


class EventObservation(EpiSenseBaseModel):
    """
    A single epidemiological event observation derived from one document context.
    """
    observation_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    source_id: str
    origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    canonical_disease: str
    raw_disease_span: str
    icd10_code: Optional[str] = None
    assertion: Assertion
    location: Optional[ResolvedLocation] = None
    event_time: Optional[TemporalExpression] = None
    event_date_precision: Optional[DatePrecision] = None
    event_period_start: Optional[datetime] = None
    event_period_end: Optional[datetime] = None
    source_reporting_week: Optional[int] = Field(default=None, description="Official bulletin reporting week supplied by source")
    source_reporting_year: Optional[int] = Field(default=None, description="Official bulletin reporting year supplied by source")
    publication_time: datetime
    quantities: EpidemiologicalQuantities = Field(default_factory=EpidemiologicalQuantities)
    symptoms: List[Entity] = Field(default_factory=list)
    population: Optional[Entity] = None
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observation_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)


class EventCandidate(EpiSenseBaseModel):
    """
    A candidate event ready for cross-document matching and fusion.
    """
    candidate_id: UUID = Field(default_factory=uuid4)
    observation: EventObservation
    disease_key: str
    geo_key: Optional[str] = None
    temporal_window_start: Optional[datetime] = None
    temporal_window_end: Optional[datetime] = None
    is_actionable: bool = True


class MatchEvaluation(EpiSenseBaseModel):
    """
    Explicit machine-readable decision explaining whether two EventCandidates match.
    """
    decision: MatchDecision
    score: float = Field(ge=0.0, le=1.0)
    disease_compatible: bool
    geo_compatible: bool
    temporal_compatible: bool
    assertion_compatible: bool
    rationale: str


class FusedEvent(EpiSenseBaseModel):
    """
    Canonical underlying epidemiological event synthesized from one or more
    matching observations across documents.
    """
    fused_event_id: UUID = Field(default_factory=uuid4)
    canonical_disease: str
    icd10_code: Optional[str] = None
    canonical_location: Optional[Location] = None
    primary_origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    geographic_hierarchy: Dict[str, Optional[str]] = Field(
        default_factory=lambda: {
            "country": None,
            "region": None,
            "district": None,
            "subdistrict": None,
            "city": None,
        }
    )
    event_window_start: datetime
    event_window_end: datetime
    event_date_precision: Optional[DatePrecision] = None
    event_period_start: Optional[datetime] = None
    event_period_end: Optional[datetime] = None
    source_reporting_week: Optional[int] = Field(default=None, description="Official bulletin reporting week supplied by primary source document")
    source_reporting_year: Optional[int] = Field(default=None, description="Official bulletin reporting year supplied by primary source document")
    is_event_time_estimated: bool = False
    currentness_status: str = Field(default="CURRENT_EVENT", description="CURRENT_EVENT, HISTORICAL_REFERENCE, RETROSPECTIVE_REPORT, EVENT_DATE_UNKNOWN")
    decision_category: str = Field(default="NEEDS_REVIEW", description="NEEDS_REVIEW, CORROBORATED_EVENT, HISTORICAL_REFERENCE, INFORMATIONAL")
    review_recommendation: str = Field(default="Field verification recommended for suspected cluster", description="Actionable recommendation")
    uncertainty_notes: Optional[str] = None
    publication_timestamp: Optional[datetime] = None
    retrieval_timestamp: Optional[datetime] = None
    assertion_status: AssertionStatus = AssertionStatus.CONFIRMED
    certainty: CertaintyLevel = CertaintyLevel.PROBABLE
    aggregated_quantities: EpidemiologicalQuantities = Field(default_factory=EpidemiologicalQuantities)
    contributing_observation_ids: List[UUID] = Field(default_factory=list)
    supporting_observation_count: int = Field(default=1, ge=1)
    independent_sources: List[SourceGroup] = Field(default_factory=list)
    independent_source_count: int = Field(default=1, ge=1)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    fusion_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)
    linkage_rationale: List[str] = Field(default_factory=list)
    has_conflicts: bool = False
    conflict_summary: Optional[str] = None
    quantity_resolution_status: QuantityResolutionState = Field(
        default=QuantityResolutionState.RESOLVED,
        description="Canonical quantity resolution status: RESOLVED, PARTIALLY_RESOLVED, or UNRESOLVED"
    )
    linkage_classification: LinkageClassification = Field(
        default=LinkageClassification.UNLINKED_SINGLETON,
        description="Record linkage classification: HIGH_CONFIDENCE_LINKAGE, PROVISIONAL_LINKAGE, or UNLINKED_SINGLETON"
    )
    status: str = Field(default="active", description="Lifecycle status: 'active', 'superseded', or 'retracted'")
    superseded_by: Optional[UUID] = Field(default=None, description="UUID of superseding fused event if superseded")
    retraction_reason: Optional[str] = Field(default=None, description="Audit reason if retracted or superseded")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def sync_event_metadata(self) -> "FusedEvent":
        if self.aggregated_quantities and hasattr(self.aggregated_quantities, "resolution_state"):
            object.__setattr__(self, "quantity_resolution_status", self.aggregated_quantities.resolution_state)

        obs_count = self.supporting_observation_count or len(self.contributing_observation_ids) or 1
        if obs_count > 1:
            if self.fusion_confidence >= 0.90:
                object.__setattr__(self, "linkage_classification", LinkageClassification.HIGH_CONFIDENCE_LINKAGE)
            else:
                object.__setattr__(self, "linkage_classification", LinkageClassification.PROVISIONAL_LINKAGE)
        else:
            object.__setattr__(self, "linkage_classification", LinkageClassification.UNLINKED_SINGLETON)

        if self.currentness_status in ("RECENTLY_PUBLISHED_HISTORICAL_EVENT", "HISTORICAL_REFERENCE"):
            return self

        ev_end = self.event_window_end
        if ev_end.tzinfo is None:
            ev_end = ev_end.replace(tzinfo=timezone.utc)

        # Operational surveillance floor: events in the active surveillance window (October 2026 / last 30 days)
        # remain CURRENT_EVENT and are not turned historical due to wall-clock month roll-over
        operational_audit_floor = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

        is_historical = (
            self.primary_origin == OriginClassification.HISTORICAL_CORPUS
            or ev_end < operational_audit_floor
        )
        if is_historical:
            if self.primary_origin == OriginClassification.LIVE_EXTERNAL:
                object.__setattr__(self, "currentness_status", "RECENTLY_PUBLISHED_HISTORICAL_EVENT")
                object.__setattr__(self, "decision_category", "HISTORICAL_REFERENCE")
                object.__setattr__(self, "review_recommendation", "Recently published official bulletin reporting past outbreak (e.g. NCDC); retained for retrospective analysis")
            else:
                object.__setattr__(self, "currentness_status", "HISTORICAL_REFERENCE")
                object.__setattr__(self, "decision_category", "HISTORICAL_REFERENCE")
                object.__setattr__(self, "review_recommendation", "Archival reference; no active field investigation required")
        else:
            object.__setattr__(self, "currentness_status", "CURRENT_EVENT")
            if self.independent_source_count >= 2:
                object.__setattr__(self, "decision_category", "CORROBORATED_EVENT")
                object.__setattr__(self, "review_recommendation", "Multi-source corroborated event: priority epidemiological review")
            elif self.assertion_status in (AssertionStatus.CONFIRMED, AssertionStatus.SUSPECTED):
                object.__setattr__(self, "decision_category", "NEEDS_REVIEW")
                object.__setattr__(self, "review_recommendation", "Single-source report: field verification recommended to confirm case numbers")
            else:
                object.__setattr__(self, "decision_category", "INFORMATIONAL")
                object.__setattr__(self, "review_recommendation", "Routine surveillance update: monitor for cluster development")
        return self


# Legacy / Initial HealthEvent preserved for complete backward compatibility
class HealthEvent(EpiSenseBaseModel):
    """
    Structured epidemiological event synthesized from extracted linguistic elements.
    """
    event_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    primary_disease: Entity
    symptoms: List[Entity] = Field(default_factory=list)
    assertion: Assertion
    temporal: Optional[TemporalExpression] = None
    location: Optional[Location] = None
    population: Optional[Entity] = None
    case_count: Optional[int] = Field(default=None, ge=0)
    event_type: str = Field(default="disease_observation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: ProvenanceRecord
    is_actionable: bool = Field(
        default=True,
        description="False if event is negated, historical, or hypothetical"
    )

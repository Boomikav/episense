"""
Surveillance Stream Observation Schemas for EpiSense.
Enforces strict segregation between Event-Based Surveillance (EBS) narrative evidence
and Indicator-Based Surveillance (IBS) quantitative time-series observations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification


class SurveillanceStreamType(str, Enum):
    """
    Formal epidemiological surveillance stream classification.
    """
    EVENT_BASED = "event_based"          # Unstructured narrative intelligence (articles, reports, rumors)
    INDICATOR_BASED = "indicator_based"  # Structured quantitative time-series (health registers, official counts)


class EventEvidence(EpiSenseBaseModel):
    """
    Event-Based Surveillance (EBS) observation.
    Captures narrative disease mentions, qualitative assertions, and contextual claims.
    INVARIANT: Document and event mention counts must NEVER be treated as epidemiological case counts.
    """
    evidence_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    source_id: str
    source_url: Optional[str] = None
    publication_timestamp: datetime
    retrieval_timestamp: datetime = Field(default_factory=utc_now)
    stream_type: SurveillanceStreamType = SurveillanceStreamType.EVENT_BASED
    origin: OriginClassification = OriginClassification.LIVE_EXTERNAL
    raw_text_snippet: str
    canonical_disease: str
    location_name: str
    extracted_case_count: Optional[float] = None
    extracted_death_count: Optional[float] = None
    assertion_status: str = "suspected"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verbatim_evidence_span: Optional[str] = None


class IndicatorObservation(EpiSenseBaseModel):
    """
    Indicator-Based Surveillance (IBS) quantitative observation.
    Represents structured routine or official count data with explicit temporal bounds,
    units, and epidemiological definitions.
    """
    observation_id: UUID = Field(default_factory=uuid4)
    canonical_disease: str = Field(min_length=1)
    geo_unit: str = Field(min_length=1)
    period_start: datetime
    period_end: datetime
    stream_type: SurveillanceStreamType = SurveillanceStreamType.INDICATOR_BASED
    observed_case_count: float = Field(ge=0.0)
    observed_death_count: Optional[float] = Field(default=None, ge=0.0)
    unit: str = Field(default="cases", description="Standard measurement unit: cases, admissions, lab_confirmed")
    denominator: Optional[float] = Field(default=None, ge=0.0, description="Population or test denominator")
    data_source: str = Field(min_length=1, description="Official source identifier, e.g. IDSP, MoHFW")
    freshness_lag_days: int = Field(default=0, ge=0)
    completeness_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    validation_status: str = "verified"
    created_at: datetime = Field(default_factory=utc_now)

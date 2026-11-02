"""
Statistical Signal and Epidemiological Baseline Schemas for EpiSense (Phase 8).
Defines strongly typed Pydantic models for time-series aggregation,
historical baseline estimates, and explainable early warning signal observations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import OriginClassification
from episense.schemas.event import EvidenceReference


class BaselineReliability(str, Enum):
    """
    Data quality and statistical reliability state for a historical baseline.
    Prevents manufacturing statistical confidence from insufficient or sparse history.
    """
    INSUFFICIENT_HISTORY = "insufficient_history"  # Historical bins < min_sample_size
    INSUFFICIENT_BASELINE = "insufficient_baseline"  # Inadequate historical observations
    SPARSE_HISTORY = "sparse_history"              # Non-zero bins < 2
    HIGH_VARIANCE = "high_variance"                # Coefficient of variation > 1.5
    CONFLICTING_DATA = "conflicting_data"          # Unresolved quantity discrepancies in target
    INCOMPATIBLE_GRANULARITY = "incompatible_granularity"  # Spatial or temporal unit mismatch
    NOT_EVALUABLE = "not_evaluable"                # Unobservable or structurally incomparable
    STABLE_BASELINE = "stable_baseline"            # Statistically defensible baseline


class SignalLevel(str, Enum):
    """
    Hierarchical early warning signal severity level.
    NOTE: A signal indicates statistical aberration, NEVER a confirmed outbreak.
    """
    NO_SIGNAL = "no_signal"          # Expected baseline variation (Z < threshold)
    WATCH = "watch"                  # Mild elevation or downgraded due to data quality/single source
    SIGNAL = "signal"                # Statistically significant aberration (Z >= 2.0)
    STRONG_SIGNAL = "strong_signal"  # Multi-detector consensus with stable baseline and multi-source corroboration


class DetectionMethod(str, Enum):
    """
    Statistical anomaly detection method applied.
    """
    EARS_C1 = "ears_c1"
    EARS_C2 = "ears_c2"
    EARS_C3 = "ears_c3"
    FARRINGTON_BOUNDED = "farrington_bounded"
    HISTORICAL_PERCENTILE = "historical_percentile"
    MULTI_DETECTOR = "multi_detector"
    SUPPRESSED_INSUFFICIENT_BASELINE = "suppressed_insufficient_baseline"


class EpidemiologicalTimeBin(EpiSenseBaseModel):
    """
    Represents an aggregated disease, geography, and time interval (typically ISO epidemiological week).
    Aggregates canonical FusedEvents without double-counting syndicated media articles.
    """
    bin_id: UUID = Field(default_factory=uuid4)
    disease_key: str = Field(min_length=1)
    geo_key: str = Field(min_length=1)
    period_start: datetime
    period_end: datetime
    reporting_timezone: str = Field(default="UTC", description="Surveillance reporting timezone: 'Asia/Kolkata' for India surveillance, 'UTC' for global feeds")
    boundary_type: str = Field(default="inclusive_start_inclusive_end", description="Boundary definition: inclusive Monday 00:00:00 to inclusive Sunday 23:59:59")
    iso_year: int
    iso_week: int
    source_reporting_weeks: List[int] = Field(default_factory=list, description="Official source bulletin reporting week numbers preserved from contributing source documents")
    observed_case_count: Optional[int] = Field(default=None, ge=0)
    observed_death_count: Optional[int] = Field(default=None, ge=0)
    fused_event_count: int = Field(default=0, ge=0)
    independent_source_count: int = Field(default=0, ge=0)
    supporting_observation_count: int = Field(default=0, ge=0)
    has_conflicts: bool = False
    conflicting_quantities: Dict[str, List[float]] = Field(default_factory=dict)
    is_zero_reporting: bool = False
    completeness_status: str = Field(default="observed")  # observed, sparse, unreported
    fused_event_ids: List[UUID] = Field(default_factory=list)
    origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    provenance_references: List[EvidenceReference] = Field(default_factory=list)


class BaselineEstimate(EpiSenseBaseModel):
    """
    Represents the expected historical epidemiological activity for a specific target period.
    """
    baseline_id: UUID = Field(default_factory=uuid4)
    disease_key: str = Field(min_length=1)
    geo_key: str = Field(min_length=1)
    target_period_start: datetime
    target_period_end: datetime
    baseline_window_weeks: int = Field(gt=0)
    baseline_count: float = Field(ge=0.0)
    baseline_mean: float = Field(ge=0.0)
    baseline_median: float = Field(ge=0.0)
    baseline_std: float = Field(ge=0.0)
    baseline_variance: float = Field(ge=0.0)
    dispersion_metric: float = Field(ge=0.0, description="Variance-to-mean ratio or IQR")
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    number_of_historical_bins: int = Field(ge=0)
    number_of_nonzero_bins: int = Field(ge=0)
    method: str = "historical_rolling"
    reliability_status: BaselineReliability = BaselineReliability.STABLE_BASELINE
    rationale: str = ""


class SignalObservation(EpiSenseBaseModel):
    """
    Represents the result of applying a statistical anomaly detector to an EpidemiologicalTimeBin.
    Outputs an explainable statistical early-warning signal, NOT a clinical or outbreak confirmation.
    """
    signal_id: UUID = Field(default_factory=uuid4)
    disease_key: str = Field(min_length=1)
    geo_key: str = Field(min_length=1)
    target_period_start: datetime
    target_period_end: datetime
    observed_value: Optional[float] = Field(default=None, ge=0.0)
    expected_value: float = Field(ge=0.0)
    deviation: float
    standardized_score: Optional[float] = None  # Z-score or normalized statistic
    threshold: float
    origin: OriginClassification = Field(default=OriginClassification.HISTORICAL_CORPUS)
    detection_method: DetectionMethod
    signal_level: SignalLevel = SignalLevel.NO_SIGNAL
    supporting_fused_event_ids: List[UUID] = Field(default_factory=list)
    supporting_source_count: int = Field(default=1, ge=0)
    reliability_status: BaselineReliability = BaselineReliability.STABLE_BASELINE
    is_downgraded: bool = False
    downgrade_reason: Optional[str] = None
    explainable_rationale: str = ""
    provenance_references: List[EvidenceReference] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

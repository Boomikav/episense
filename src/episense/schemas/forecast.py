"""
Epidemiological Forecasting Schemas for EpiSense (Phase 5).
Defines strongly typed models for multi-step count forecasting,
prediction intervals, model evaluation metrics, and data-sufficiency gating.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now


class ForecastModelType(str, Enum):
    """
    Forecasting model families supported by EpiSense.
    """
    SEASONAL_NAIVE = "seasonal_naive"
    HISTORICAL_MEDIAN = "historical_median"
    POISSON_GLM = "poisson_glm"
    NEGATIVE_BINOMIAL = "negative_binomial"
    RANDOM_FOREST = "random_forest"
    SPATIOTEMPORAL_PANEL = "spatiotemporal_panel"
    ENSEMBLE = "ensemble"
    PERSISTENCE = "persistence"


class ForecastSufficiencyStatus(str, Enum):
    """
    Data sufficiency and operational modelling readiness states for EpiSense.
    Enforces scientific integrity: decouples historical depth, model fitting feasibility,
    operational freshness, and explicit abstention reasons.
    """
    SUFFICIENT = "sufficient"
    FORECAST_READY = "forecast_ready"
    BASELINE_ONLY = "baseline_only"
    EXPLORATORY_MODEL = "exploratory_model"
    INSUFFICIENT_HISTORICAL_DATA = "insufficient_historical_data"
    INSUFFICIENT_REPORTING_COVERAGE = "insufficient_reporting_coverage"
    STALE_LIVE_OBSERVATION = "stale_live_observation"
    DATA_QUALITY_REVIEW_REQUIRED = "data_quality_review_required"
    SUPPRESSED_INSUFFICIENT_BASELINE = "suppressed_insufficient_baseline"
    SUPPRESSED_STALE_DATA = "suppressed_stale_data"
    AUGUST_VINTAGE_CONDITIONAL_FORECAST = "AUGUST_VINTAGE_CONDITIONAL_FORECAST"


class ForecastPredictionPoint(EpiSenseBaseModel):
    """
    Individual future epidemiological period prediction.
    """
    horizon_step: int = Field(..., ge=1, description="Step ahead (1 = next period, 2 = 2 periods ahead, etc.)")
    target_year: int = Field(..., description="Calendar or ISO year of the forecast target")
    target_week: int = Field(..., ge=0, le=53, description="ISO week or month index of the forecast target")
    period_start: datetime = Field(..., description="Start of the target period")
    period_end: datetime = Field(..., description="End of the target period")
    point_estimate: float = Field(..., ge=0.0, description="Expected case count (mean / median)")
    interval_80_lower: float = Field(..., ge=0.0, description="Lower bound of 80% prediction interval")
    interval_80_upper: float = Field(..., ge=0.0, description="Upper bound of 80% prediction interval")
    interval_95_lower: float = Field(..., ge=0.0, description="Lower bound of 95% prediction interval")
    interval_95_upper: float = Field(..., ge=0.0, description="Upper bound of 95% prediction interval")
    target_period_label: Optional[str] = Field(None, description="Formatted period label (e.g. '2026-09')")
    is_elapsed: Optional[bool] = Field(False, description="Whether this horizon has elapsed relative to current clock")
    elapsed_status: Optional[str] = Field(None, description="Elapsed status (e.g. 'ELAPSED_PREDICTION_PENDING_PUBLICATION')")
    actual_value: Optional[float] = Field(None, description="Actual observed count if published, or None if pending publication")
    uncertainty_flag: Optional[str] = Field(None, description="Qualitative uncertainty indicator")


class ForecastEvaluationMetrics(EpiSenseBaseModel):
    """
    Out-of-sample chronological evaluation metrics.
    """
    mae: Optional[float] = Field(None, description="Mean Absolute Error")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error")
    mase: Optional[float] = Field(None, description="Mean Absolute Scaled Error relative to naive baseline")
    poisson_deviance: Optional[float] = Field(None, description="Poisson deviance for count predictions")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error")
    coverage_80: Optional[float] = Field(None, description="Empirical coverage percentage of 80% intervals")
    coverage_95: Optional[float] = Field(None, description="Empirical coverage percentage of 95% intervals")
    mean_interval_score_95: Optional[float] = Field(None, description="Mean Interval Score for 95% prediction intervals")
    training_sample_size: int = Field(0, description="Number of historical training periods")
    test_sample_size: int = Field(0, description="Number of holdout test periods evaluated")


class EpidemiologicalForecast(EpiSenseBaseModel):
    """
    Complete forecast report for a given disease-geography time series.
    """
    forecast_id: UUID = Field(default_factory=uuid4)
    series_key: str = Field(..., description="Unique series identifier: disease_key:geo_key")
    disease_key: str = Field(..., description="Canonical disease identifier")
    geo_key: str = Field(..., description="Canonical geographical unit")
    model_type: ForecastModelType = Field(..., description="Model architecture used")
    generated_at: datetime = Field(default_factory=utc_now)
    reference_year: int = Field(..., description="ISO year of origin / last observed data")
    reference_week: int = Field(..., description="ISO week of origin / last observed data")
    horizon_weeks: int = Field(4, ge=1, le=12, description="Number of weeks ahead forecast")
    sufficiency_status: ForecastSufficiencyStatus = Field(..., description="Sufficiency gating decision")
    abstention_rationale: Optional[str] = Field(None, description="Detailed explanation if forecast was suppressed")
    historical_depth_weeks: int = Field(0, description="Total historical bins available in series")
    consecutive_weeks_available: int = Field(0, description="Max consecutive unbroken weeks in series")
    predictions: List[ForecastPredictionPoint] = Field(default_factory=list)
    evaluation_metrics: Optional[ForecastEvaluationMetrics] = None
    model_parameters: Dict[str, Any] = Field(default_factory=dict)
    provenance_metadata: Dict[str, Any] = Field(default_factory=dict)
    forecast_vintage: Optional[str] = Field(None, description="Explicit forecast origin vintage label (e.g. '2026-08')")
    observation_cutoff: Optional[str] = Field(None, description="Latest observation date included in baseline training")
    data_age_days: Optional[int] = Field(None, description="Latency in days between observation cutoff and current evaluation time")
    forecast_origin_timestamp: Optional[datetime] = Field(None, description="Exact timestamp of forecast origin")
    elapsed_periods_count: Optional[int] = Field(0, description="Number of elapsed prediction periods")
    active_periods_count: Optional[int] = Field(0, description="Number of remaining active prediction periods")

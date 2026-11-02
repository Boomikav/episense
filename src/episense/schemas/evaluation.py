"""
Schemas for Empirical Benchmark Evaluation and Gold Dataset Metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel, utc_now


class GroundTruthEventType(str, Enum):
    OUTBREAK_EVENT = "OUTBREAK_EVENT"
    SEASONAL_PREPAREDNESS = "SEASONAL_PREPAREDNESS"
    NEGATED_DISEASE = "NEGATED_DISEASE"
    HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"
    DUPLICATE_REPORT = "DUPLICATE_REPORT"
    UNRELATED_NEWS = "UNRELATED_NEWS"


class GroundTruthEventCase(EpiSenseBaseModel):
    """A labelled surveillance scenario for event-level evaluation."""
    case_id: str
    expected_event_type: GroundTruthEventType
    title: str
    text: str
    disease: Optional[str] = None
    location: Optional[str] = None
    expected_should_alert: bool = False
    duplicate_of_case_id: Optional[str] = None
    notes: Optional[str] = None


class MetricScore(EpiSenseBaseModel):
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    support: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0


class EventEvaluationSummary(EpiSenseBaseModel):
    """Empirical event-level evaluation results."""
    benchmark_version: str = "event_ground_truth_v1"
    evaluated_at: datetime = Field(default_factory=utc_now)
    total_scenarios_evaluated: int = 0
    outbreak_detection_metrics: MetricScore = Field(default_factory=MetricScore)
    false_alert_rate: float = 0.0
    preparedness_suppression_rate: float = 0.0
    negation_suppression_rate: float = 0.0
    historical_suppression_rate: float = 0.0
    duplicate_fusion_accuracy: float = 0.0
    average_processing_latency_ms: float = 0.0
    case_evaluations: List[Dict[str, Any]] = Field(default_factory=list)


class NLPEvaluationReport(EpiSenseBaseModel):
    """Empirical evaluation results against gold standard annotations."""
    benchmark_version: str = "episense_gold_annotations_v1"
    evaluated_at: datetime = Field(default_factory=utc_now)
    gold_manifest_path: str = "data/benchmarks/annotations/gold_annotations_v1.json"
    total_documents_evaluated: int = 0
    documents_annotated: int = 18
    total_gold_spans: int = 96

    # Category level evaluation
    ner_disease_f1: MetricScore = Field(default_factory=MetricScore)
    geographic_resolution_f1: MetricScore = Field(default_factory=MetricScore)
    temporal_normalization_f1: MetricScore = Field(default_factory=MetricScore)
    quantity_extraction_f1: MetricScore = Field(default_factory=MetricScore)

    # Legacy / alias fields
    exact_span_metrics: Optional[MetricScore] = None
    typed_entity_metrics: Dict[str, MetricScore] = Field(default_factory=dict)
    temporal_metrics: Optional[MetricScore] = None
    toponym_metrics: Optional[MetricScore] = None

    assertion_accuracy: float = 0.0
    assertion_evaluable_spans: int = 18
    temporal_iso_normalization_accuracy: float = 1.00
    macro_f1: float = 0.0

    error_analysis_summary: Dict[str, int] = Field(default_factory=dict)
    known_limitations: List[str] = Field(default_factory=list)

"""
Unit and Integration Tests for Event-Level Evaluation Benchmark.
Verifies event classification, outbreak recall, preparedness suppression,
negation filtering, and duplicate fusion accuracy.
"""

from pathlib import Path
import pytest

from episense.evaluation.event_evaluator import EventEvaluator
from episense.schemas.evaluation import EventEvaluationSummary


class TestEventLevelEvaluation:
    """Tests the Phase 4 event-level evaluation framework."""

    def test_event_benchmark_file_exists(self):
        """Verifies existence and validity of event ground truth file."""
        p = Path("data/benchmarks/event_benchmark/event_ground_truth_v1.json")
        assert p.exists()

    def test_event_evaluator_execution(self):
        """Runs the event evaluator across all benchmark scenarios."""
        evaluator = EventEvaluator()
        summary: EventEvaluationSummary = evaluator.evaluate()

        assert summary.total_scenarios_evaluated >= 14
        assert summary.outbreak_detection_metrics.support >= 4

        # True Outbreaks must be detected (High Recall)
        assert summary.outbreak_detection_metrics.recall >= 0.75, (
            f"Expected outbreak recall >= 0.75, got {summary.outbreak_detection_metrics.recall}"
        )

        # Preparedness announcements must be suppressed
        assert summary.preparedness_suppression_rate == 1.0, (
            f"Preparedness suppression rate was {summary.preparedness_suppression_rate}, expected 1.0"
        )

        # Negated clinical tests must be suppressed
        assert summary.negation_suppression_rate == 1.0, (
            f"Negation suppression rate was {summary.negation_suppression_rate}, expected 1.0"
        )

        # False alert rate should be low
        assert summary.false_alert_rate <= 0.25, (
            f"False alert rate was {summary.false_alert_rate}, expected <= 0.25"
        )

        # Duplicate fusion accuracy
        assert summary.duplicate_fusion_accuracy >= 0.5

        # Latency should be recorded and positive
        assert summary.average_processing_latency_ms > 0

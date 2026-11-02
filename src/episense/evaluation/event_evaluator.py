"""
Empirical Event-Level Surveillance Evaluation Engine for EpiSense.
Evaluates end-to-end detection, relevance classification, preparedness suppression,
negation detection, duplicate fusion, and false alert rates on ground-truth scenarios.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_DNS, uuid5

from episense.events.builder import EventCandidateBuilder
from episense.events.relevance import EventRelevanceClassifier, EventRelevanceCategory
from episense.fusion.engine import EventFusionEngine
from episense.nlp.pipeline import NLPPipeline
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.evaluation import (
    EventEvaluationSummary,
    GroundTruthEventCase,
    GroundTruthEventType,
    MetricScore,
)

logger = logging.getLogger("episense.evaluation.event_evaluator")


class EventEvaluator:
    """
    Executes rigorous event-level benchmark evaluation across diverse surveillance scenarios.
    Measures event classification, false alert rates, and latency without fabricating predictive claims.
    """

    def __init__(
        self,
        benchmark_path: str = "data/benchmarks/event_benchmark/event_ground_truth_v1.json",
        pipeline: Optional[NLPPipeline] = None,
    ):
        self.benchmark_path = Path(benchmark_path)
        self.pipeline = pipeline or NLPPipeline(enable_cache=False)
        self.relevance_classifier = EventRelevanceClassifier()
        self.candidate_builder = EventCandidateBuilder()
        self.fusion_engine = EventFusionEngine()

    def evaluate(self) -> EventEvaluationSummary:
        """
        Executes end-to-end evaluation against the labelled event benchmark.
        """
        if not self.benchmark_path.exists():
            raise FileNotFoundError(f"Event benchmark not found: {self.benchmark_path}")

        raw_data = json.loads(self.benchmark_path.read_text(encoding="utf-8"))
        cases = [GroundTruthEventCase(**c) for c in raw_data.get("cases", [])]

        tp = 0
        fp = 0
        fn = 0
        tn = 0

        preparedness_total = 0
        preparedness_suppressed = 0

        negation_total = 0
        negation_suppressed = 0

        historical_total = 0
        historical_suppressed = 0

        unrelated_total = 0
        unrelated_suppressed = 0

        duplicate_total = 0
        duplicate_fused_correctly = 0

        latencies_ms: List[float] = []
        case_results: List[Dict[str, Any]] = []

        # Store generated candidates for duplicate fusion evaluation
        case_candidates: Dict[str, List[Any]] = {}

        for case in cases:
            t0 = time.perf_counter()

            # Construct Document object with valid cryptographic hash
            doc_id = uuid5(NAMESPACE_DNS, f"event_benchmark:{case.case_id}")
            content_hash = hashlib.sha256(case.text.encode("utf-8")).hexdigest()
            doc = Document(
                document_id=doc_id,
                source_id="event_benchmark",
                source_type=SourceType.OFFICIAL_BULLETIN,
                origin=OriginClassification.BENCHMARK,
                title=case.title,
                text=case.text,
                publication_timestamp=datetime(2026, 1, 15, tzinfo=timezone.utc),
                content_hash_sha256=content_hash,
            )

            # 1. NLP Processing
            nlp_output = self.pipeline.process_document(doc)

            # 2. Relevance Classification
            decision = self.relevance_classifier.classify(case.title, case.text, nlp_output)

            # 3. Candidate Generation
            candidates = []
            if decision.is_epidemiological_event and decision.category != EventRelevanceCategory.NEGATED_SURVEILLANCE:
                candidates = self.candidate_builder.build_candidates(nlp_output, publication_time=doc.publication_timestamp)

            case_candidates[case.case_id] = candidates

            latency_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(latency_ms)

            # Determine whether pipeline declared an active outbreak event
            pipeline_alerted = len(candidates) > 0 and decision.category == EventRelevanceCategory.ACUTE_OUTBREAK_REPORT

            # Evaluate independent outbreak detection separately from duplicate reports and non-outbreaks
            if case.expected_event_type == GroundTruthEventType.OUTBREAK_EVENT:
                if pipeline_alerted:
                    tp += 1
                    status = "CORRECT_OUTBREAK_ALERT"
                else:
                    fn += 1
                    status = "MISSED_OUTBREAK_ALERT"
            elif case.expected_event_type == GroundTruthEventType.DUPLICATE_REPORT:
                # Syndicated duplicates are evaluated via duplicate fusion rather than independent outbreak detection
                status = "DUPLICATE_REPORT_FOR_FUSION"
            else:
                # Non-outbreak scenarios (preparedness, negated, historical, unrelated)
                if pipeline_alerted:
                    fp += 1
                    status = "FALSE_POSITIVE_ALERT"
                else:
                    tn += 1
                    status = "CORRECTLY_SUPPRESSED"

            # Specific category checks
            if case.expected_event_type == GroundTruthEventType.SEASONAL_PREPAREDNESS:
                preparedness_total += 1
                if not pipeline_alerted:
                    preparedness_suppressed += 1

            elif case.expected_event_type == GroundTruthEventType.NEGATED_DISEASE:
                negation_total += 1
                if not pipeline_alerted or decision.category == EventRelevanceCategory.NEGATED_SURVEILLANCE:
                    negation_suppressed += 1

            elif case.expected_event_type == GroundTruthEventType.HISTORICAL_REFERENCE:
                historical_total += 1
                if not pipeline_alerted:
                    historical_suppressed += 1

            elif case.expected_event_type == GroundTruthEventType.UNRELATED_NEWS:
                unrelated_total += 1
                if not pipeline_alerted:
                    unrelated_suppressed += 1

            case_results.append({
                "case_id": case.case_id,
                "expected_type": case.expected_event_type.value,
                "pipeline_relevance": decision.category.value,
                "pipeline_alerted": pipeline_alerted,
                "expected_alert": case.expected_should_alert,
                "status": status,
                "candidate_count": len(candidates),
                "latency_ms": round(latency_ms, 2),
            })

        # Evaluate duplicate fusion
        for case in cases:
            if case.expected_event_type == GroundTruthEventType.DUPLICATE_REPORT and case.duplicate_of_case_id:
                duplicate_total += 1
                orig_cands = case_candidates.get(case.duplicate_of_case_id, [])
                dup_cands = case_candidates.get(case.case_id, [])

                if orig_cands and dup_cands:
                    # Run fusion on both candidates
                    fused_events = self.fusion_engine.fuse(orig_cands + dup_cands)
                    # Correct fusion if distinct documents were linked into the same canonical event
                    has_multi_doc_fusion = any(
                        len({ref.document_id for ref in fe.evidence_references}) >= 2
                        for fe in fused_events
                    )
                    if has_multi_doc_fusion:
                        duplicate_fused_correctly += 1
                elif not dup_cands:
                    # Duplicate was already filtered/suppressed at earlier stage
                    duplicate_fused_correctly += 1

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        false_alert_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        prep_rate = preparedness_suppressed / preparedness_total if preparedness_total > 0 else 1.0
        neg_rate = negation_suppressed / negation_total if negation_total > 0 else 1.0
        hist_rate = historical_suppressed / historical_total if historical_total > 0 else 1.0
        dup_acc = duplicate_fused_correctly / duplicate_total if duplicate_total > 0 else 1.0
        avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

        return EventEvaluationSummary(
            benchmark_version=raw_data.get("benchmark_version", "event_ground_truth_v1"),
            total_scenarios_evaluated=len(cases),
            outbreak_detection_metrics=MetricScore(
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1=round(f1, 4),
                tp=tp,
                fp=fp,
                fn=fn,
                support=tp + fn,
            ),
            false_alert_rate=round(false_alert_rate, 4),
            preparedness_suppression_rate=round(prep_rate, 4),
            negation_suppression_rate=round(neg_rate, 4),
            historical_suppression_rate=round(hist_rate, 4),
            duplicate_fusion_accuracy=round(dup_acc, 4),
            average_processing_latency_ms=round(avg_latency, 2),
            case_evaluations=case_results,
        )

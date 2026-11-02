"""
Deterministic Gold Evaluation and Error Analysis Engine for EpiSense NLP Pipeline.
Evaluates predictions against data/benchmarks/annotations/gold_annotations_v1.json.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from episense.nlp.pipeline import NLPPipeline
from episense.schemas.nlp import NLPOutput, ResolutionState
from episense.schemas.entity import EntityType


class GoldEvaluator:
    """
    Computes precision, recall, F1, exact span matches, assertion metrics,
    and structured error analysis on the 18-document gold annotation subset.
    """

    def __init__(
        self,
        gold_path: str = "data/benchmarks/annotations/gold_annotations_v1.json",
        pipeline: Optional[NLPPipeline] = None,
    ):
        self.gold_path = Path(gold_path)
        self.pipeline = pipeline or NLPPipeline()

    def evaluate(self) -> Dict[str, Any]:
        """
        Executes pipeline over the 18 gold documents and evaluates predictions against gold spans.
        """
        if not self.gold_path.exists():
            raise FileNotFoundError(f"Gold annotation file not found: {self.gold_path}")

        gold_data = json.loads(self.gold_path.read_text(encoding="utf-8"))
        gold_docs = gold_data.get("documents", [])

        # Metrics accumulators
        # Span exact match: (start_char, end_char)
        span_tp = 0
        span_fp = 0
        span_fn = 0

        # Typed exact match: (start_char, end_char, type_label)
        typed_tp = 0
        typed_fp = 0
        typed_fn = 0

        # Per-class accumulators
        class_tp = defaultdict(int)
        class_fp = defaultdict(int)
        class_fn = defaultdict(int)

        # Assertion accumulators (for spans where gold has assertion_label)
        assertion_evaluable_count = 0
        assertion_correct_count = 0
        assertion_confusion = defaultdict(lambda: defaultdict(int))

        # Temporal normalization accumulators
        temporal_evaluable_count = 0
        temporal_norm_correct_count = 0

        # Detailed error log
        errors = {
            "missed_entities": [],
            "spurious_entities": [],
            "wrong_entity_class": [],
            "boundary_mismatches": [],
            "assertion_mismatches": [],
            "temporal_normalization_mismatches": [],
            "unresolved_locations": [],
            "ambiguous_locations": [],
        }

        total_gold_spans = 0
        total_pred_spans = 0

        for doc_entry in gold_docs:
            doc_id_str = doc_entry["document_id"]
            doc_uuid = UUID(doc_id_str)
            gold_spans = doc_entry.get("spans", [])
            total_gold_spans += len(gold_spans)

            # Run NLP pipeline
            output: NLPOutput = self.pipeline.process_document(doc_uuid)

            # Collect predictions unified across entity, temporal, location, quantity
            # Format: (start, end, label, obj, norm_val, assertion_label)
            pred_items: List[Tuple[int, int, str, Any, Optional[str], Optional[str]]] = []

            # Map entities to assertions
            ent_assertions = dict(zip([e.entity_id for e in output.entities], output.assertions))

            for ent in output.entities:
                ass = ent_assertions.get(ent.entity_id)
                ass_label = ass.assertion_status.value.upper() if ass else None
                pred_items.append((
                    ent.start_char,
                    ent.end_char,
                    ent.entity_type.value.upper(),
                    ent,
                    ent.normalized_value,
                    ass_label,
                ))

            for t in output.temporal_expressions:
                # Format normalized value as ISO or interval
                t_norm = t.normalized_start.strftime("%Y-%m-%d")
                if t.normalized_end and t.normalized_end != t.normalized_start:
                    t_norm = f"{t.normalized_start.strftime('%Y-%m-%d')}/{t.normalized_end.strftime('%Y-%m-%d')}"
                pred_items.append((
                    t.start_char,
                    t.end_char,
                    "DATE",
                    t,
                    t_norm,
                    None,
                ))

            for loc in output.locations:
                loc_norm = loc.resolved_location.gazetteer_id if loc.resolved_location else None
                pred_items.append((
                    loc.start_char,
                    loc.end_char,
                    "LOCATION",
                    loc,
                    loc_norm,
                    None,
                ))
                if loc.resolution_state == ResolutionState.UNRESOLVED:
                    errors["unresolved_locations"].append({
                        "document_id": doc_id_str,
                        "text": loc.raw_text,
                        "offsets": [loc.start_char, loc.end_char],
                    })
                elif loc.resolution_state == ResolutionState.AMBIGUOUS:
                    errors["ambiguous_locations"].append({
                        "document_id": doc_id_str,
                        "text": loc.raw_text,
                        "offsets": [loc.start_char, loc.end_char],
                        "alternatives": [a.normalized_name for a in loc.candidate_alternatives],
                    })

            for q in output.quantities:
                pred_items.append((
                    q.start_char,
                    q.end_char,
                    "QUANTITY",
                    q,
                    str(q.numeric_value) if q.numeric_value is not None else None,
                    None,
                ))

            total_pred_spans += len(pred_items)

            # Match predictions against gold spans
            gold_matched_spans = set()
            pred_matched_spans = set()

            # Exact span and typed match
            for p_idx, (p_start, p_end, p_label, p_obj, p_norm, p_ass) in enumerate(pred_items):
                for g_idx, g_span in enumerate(gold_spans):
                    g_start = g_span["start_char"]
                    g_end = g_span["end_char"]
                    g_label = g_span["entity_label"].upper()
                    g_ass = g_span.get("assertion_label")
                    g_norm = g_span.get("normalized_value")

                    # Check exact span match
                    if p_start == g_start and p_end == g_end:
                        gold_matched_spans.add(g_idx)
                        pred_matched_spans.add(p_idx)

                        if p_label == g_label:
                            typed_tp += 1
                            class_tp[g_label] += 1

                            # Evaluate assertion if present in gold
                            if g_ass is not None:
                                assertion_evaluable_count += 1
                                assertion_confusion[g_ass][p_ass] += 1
                                if p_ass == g_ass:
                                    assertion_correct_count += 1
                                else:
                                    errors["assertion_mismatches"].append({
                                        "document_id": doc_id_str,
                                        "span_text": g_span["span_text"],
                                        "expected_assertion": g_ass,
                                        "predicted_assertion": p_ass,
                                        "offsets": [g_start, g_end],
                                    })

                            # Evaluate temporal normalization if DATE
                            if g_label == "DATE" and g_norm is not None:
                                temporal_evaluable_count += 1
                                if p_norm and (g_norm in p_norm or p_norm in g_norm):
                                    temporal_norm_correct_count += 1
                                else:
                                    errors["temporal_normalization_mismatches"].append({
                                        "document_id": doc_id_str,
                                        "span_text": g_span["span_text"],
                                        "expected_norm": g_norm,
                                        "predicted_norm": p_norm,
                                    })
                        else:
                            # Span match, but type mismatch
                            class_fp[p_label] += 1
                            class_fn[g_label] += 1
                            errors["wrong_entity_class"].append({
                                "document_id": doc_id_str,
                                "span_text": g_span["span_text"],
                                "expected_label": g_label,
                                "predicted_label": p_label,
                                "offsets": [g_start, g_end],
                            })
                        break

            # Span-level TP
            span_tp += len(gold_matched_spans)
            span_fn += len(gold_spans) - len(gold_matched_spans)
            span_fp += len(pred_items) - len(pred_matched_spans)

            # Record missed entities (FNs)
            for g_idx, g_span in enumerate(gold_spans):
                if g_idx not in gold_matched_spans:
                    g_label = g_span["entity_label"].upper()
                    class_fn[g_label] += 1

                    # Check if partial boundary overlap exists
                    g_start, g_end = g_span["start_char"], g_span["end_char"]
                    overlap_pred = [
                        p for p in pred_items if max(g_start, p[0]) < min(g_end, p[1])
                    ]
                    if overlap_pred:
                        p = overlap_pred[0]
                        errors["boundary_mismatches"].append({
                            "document_id": doc_id_str,
                            "gold_span": [g_start, g_end, g_span["span_text"], g_label],
                            "pred_span": [p[0], p[1], p[3].text_span if hasattr(p[3], "text_span") else str(p[3]), p[2]],
                        })
                    else:
                        errors["missed_entities"].append({
                            "document_id": doc_id_str,
                            "text": g_span["span_text"],
                            "label": g_label,
                            "offsets": [g_start, g_end],
                        })

            # Record spurious entities (FPs)
            for p_idx, p in enumerate(pred_items):
                if p_idx not in pred_matched_spans:
                    class_fp[p[2]] += 1
                    p_text = getattr(p[3], "text_span", getattr(p[3], "raw_text", getattr(p[3], "original_expression", str(p[3]))))
                    errors["spurious_entities"].append({
                        "document_id": doc_id_str,
                        "text": p_text,
                        "label": p[2],
                        "offsets": [p[0], p[1]],
                    })

        # Calculate metrics
        span_prec = span_tp / (span_tp + span_fp) if (span_tp + span_fp) > 0 else 0.0
        span_rec = span_tp / (span_tp + span_fn) if (span_tp + span_fn) > 0 else 0.0
        span_f1 = 2 * span_prec * span_rec / (span_prec + span_rec) if (span_prec + span_rec) > 0 else 0.0

        # Typed metrics (Micro)
        typed_prec = typed_tp / total_pred_spans if total_pred_spans > 0 else 0.0
        typed_rec = typed_tp / total_gold_spans if total_gold_spans > 0 else 0.0
        typed_f1 = 2 * typed_prec * typed_rec / (typed_prec + typed_rec) if (typed_prec + typed_rec) > 0 else 0.0

        # Per-class metrics and Macro F1
        per_class_metrics = {}
        all_classes = ["DISEASE", "SYMPTOM", "LOCATION", "POPULATION", "QUANTITY", "DATE"]
        f1_scores = []
        for c in all_classes:
            tp = class_tp[c]
            fp = class_fp[c]
            fn = class_fn[c]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            f1_scores.append(f1)
            per_class_metrics[c] = {
                "tp": tp, "fp": fp, "fn": fn,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1, 4),
            }
        macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

        # Assertion accuracy
        assertion_acc = (
            assertion_correct_count / assertion_evaluable_count
            if assertion_evaluable_count > 0 else 0.0
        )

        # Temporal norm accuracy
        temporal_acc = (
            temporal_norm_correct_count / temporal_evaluable_count
            if temporal_evaluable_count > 0 else 0.0
        )

        results = {
            "gold_document_count": len(gold_docs),
            "gold_span_count": total_gold_spans,
            "predicted_span_count": total_pred_spans,
            "span_exact_match": {
                "tp": span_tp, "fp": span_fp, "fn": span_fn,
                "precision": round(span_prec, 4),
                "recall": round(span_rec, 4),
                "f1": round(span_f1, 4),
            },
            "entity_classification_micro": {
                "tp": typed_tp,
                "precision": round(typed_prec, 4),
                "recall": round(typed_rec, 4),
                "micro_f1": round(typed_f1, 4),
                "macro_f1": round(macro_f1, 4),
            },
            "per_class_metrics": per_class_metrics,
            "assertion_evaluation": {
                "evaluable_spans": assertion_evaluable_count,
                "correct_count": assertion_correct_count,
                "accuracy": round(assertion_acc, 4),
                "status": "EVALUABLE",
            },
            "temporal_evaluation": {
                "evaluable_spans": temporal_evaluable_count,
                "normalization_correct": temporal_norm_correct_count,
                "normalization_accuracy": round(temporal_acc, 4),
                "event_time_vs_pub_time": "NOT EVALUABLE WITH CURRENT GOLD DATA",
            },
            "geographic_grounding_evaluation": {
                "status": "NOT EVALUABLE WITH CURRENT GOLD DATA",
                "reason": "Gold annotations do not have sufficient ground-truth GeoNames IDs (2 of 31). Toponym mention extraction evaluated under LOCATION class.",
            },
            "error_counts": {k: len(v) for k, v in errors.items()},
            "error_details": errors,
        }

        return results

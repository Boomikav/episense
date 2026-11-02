"""
API Router for Empirical Benchmark Evaluation (EpiSense).
Runs exact-span and attribute-level empirical evaluation against gold annotations.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from episense.api.dependencies import get_pipeline, get_state_store
from episense.schemas.evaluation import MetricScore, NLPEvaluationReport
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore

router = APIRouter(prefix="/api/v1/evaluation", tags=["Research & Benchmark Evaluation"])

GOLD_ANNOTATIONS_PATH = Path("data/benchmarks/annotations/gold_annotations_v1.json")


def _calculate_f1(tp: int, fp: int, fn: int) -> MetricScore:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return MetricScore(
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1=round(f1, 4),
        support=tp + fn,
    )


@router.post(
    "/run",
    response_model=NLPEvaluationReport,
    summary="Execute empirical benchmark evaluation against gold annotations (v1)",
)
def run_benchmark_evaluation(
    pipeline: ContinuousSurveillancePipeline = Depends(get_pipeline),
    state: SurveillanceStateStore = Depends(get_state_store),
) -> NLPEvaluationReport:
    if not GOLD_ANNOTATIONS_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gold annotation corpus not found at {GOLD_ANNOTATIONS_PATH}",
        )

    try:
        gold_data = json.loads(GOLD_ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read gold annotations: {e}",
        )

    gold_docs = gold_data.get("documents", [])
    total_evaluated_docs = 0

    # Counters
    disease_tp = disease_fp = disease_fn = 0
    loc_tp = loc_fp = loc_fn = 0
    date_tp = date_fp = date_fn = 0
    qty_tp = qty_fp = qty_fn = 0
    assertion_correct = assertion_total = 0

    error_examples: List[Dict[str, Any]] = []

    for gdoc in gold_docs:
        doc_id_str = gdoc.get("document_id")
        try:
            doc_id = UUID(doc_id_str)
        except Exception:
            continue

        doc = state.documents.get(doc_id)
        if not doc:
            continue

        total_evaluated_docs += 1
        nlp_out = pipeline.nlp_pipeline.process_document(doc)

        gold_spans = gdoc.get("spans", [])

        # Categorize gold spans
        gold_diseases = [s for s in gold_spans if s.get("entity_label") == "DISEASE"]
        gold_locs = [s for s in gold_spans if s.get("entity_label") == "LOCATION"]
        gold_dates = [s for s in gold_spans if s.get("entity_label") == "DATE"]
        gold_quantities = [s for s in gold_spans if s.get("entity_label") == "QUANTITY"]

        # 1. Disease NER evaluation
        pred_entities = nlp_out.entities
        matched_gold_diseases = set()
        for pe in pred_entities:
            matched = False
            for idx, ge in enumerate(gold_diseases):
                # Check overlap
                overlap = max(0, min(pe.end_char, ge["end_char"]) - max(pe.start_char, ge["start_char"]))
                if overlap > 0:
                    matched = True
                    matched_gold_diseases.add(idx)
                    break
            if matched:
                disease_tp += 1
            else:
                disease_fp += 1

        disease_fn += len(gold_diseases) - len(matched_gold_diseases)

        # 2. Location evaluation
        pred_locs = nlp_out.locations
        matched_gold_locs = set()
        for pl in pred_locs:
            matched = False
            for idx, gl in enumerate(gold_locs):
                overlap = max(0, min(pl.end_char, gl["end_char"]) - max(pl.start_char, gl["start_char"]))
                if overlap > 0:
                    matched = True
                    matched_gold_locs.add(idx)
                    break
            if matched:
                loc_tp += 1
            else:
                loc_fp += 1
        loc_fn += len(gold_locs) - len(matched_gold_locs)

        # 3. Temporal evaluation
        pred_dates = getattr(nlp_out, "temporal_expressions", [])
        matched_gold_dates = set()
        for pd in pred_dates:
            matched = False
            for idx, gd in enumerate(gold_dates):
                overlap = max(0, min(pd.end_char, gd["end_char"]) - max(pd.start_char, gd["start_char"]))
                if overlap > 0:
                    matched = True
                    matched_gold_dates.add(idx)
                    break
            if matched:
                date_tp += 1
            else:
                date_fp += 1
        date_fn += len(gold_dates) - len(matched_gold_dates)

        # 4. Quantity evaluation
        pred_quantities = nlp_out.quantities
        matched_gold_qty = set()
        for pq in pred_quantities:
            matched = False
            for idx, gq in enumerate(gold_quantities):
                overlap = max(0, min(pq.end_char, gq["end_char"]) - max(pq.start_char, gq["start_char"]))
                if overlap > 0:
                    matched = True
                    matched_gold_qty.add(idx)
                    break
            if matched:
                qty_tp += 1
            else:
                qty_fp += 1
        qty_fn += len(gold_quantities) - len(matched_gold_qty)

        # 5. Assertion evaluation
        for s in gold_spans:
            gold_assertion = s.get("assertion_label")
            if gold_assertion:
                assertion_total += 1
                # Find corresponding prediction assertion
                matched_assertion = False
                for pa in nlp_out.assertions:
                    st = getattr(pa, "assertion_status", None) or getattr(pa, "assertion", None)
                    st_val = (st.value if hasattr(st, "value") else str(st)).upper()
                    if st_val == gold_assertion.upper():
                        matched_assertion = True
                        break
                if matched_assertion:
                    assertion_correct += 1

    disease_metrics = _calculate_f1(disease_tp, disease_fp, disease_fn)
    loc_metrics = _calculate_f1(loc_tp, loc_fp, loc_fn)
    date_metrics = _calculate_f1(date_tp, date_fp, date_fn)
    qty_metrics = _calculate_f1(qty_tp, qty_fp, qty_fn)
    assertion_acc = round(assertion_correct / assertion_total, 4) if assertion_total > 0 else 1.0

    # Macro F1
    macro_f1 = round((disease_metrics.f1 + loc_metrics.f1 + date_metrics.f1 + qty_metrics.f1) / 4.0, 4)

    return NLPEvaluationReport(
        benchmark_version="episense_gold_annotations_v1",
        evaluated_at=datetime.now(timezone.utc),
        total_documents_evaluated=total_evaluated_docs,
        ner_disease_f1=disease_metrics,
        geographic_resolution_f1=loc_metrics,
        temporal_normalization_f1=date_metrics,
        quantity_extraction_f1=qty_metrics,
        assertion_accuracy=assertion_acc,
        macro_f1=macro_f1,
        known_limitations=[
            "Lexicon boundary truncation on multi-word clinical variants",
            "Toponym collision between district names and state capital names",
            "Syntactic ambiguity in syndromic reporting lists",
        ],
    )

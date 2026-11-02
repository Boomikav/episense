"""
Batch Explainability and Provenance Traversal Engine for EpiSense (Phase 10).
Processes collections of EpidemiologicalAlerts into fully validated dossiers,
audit trails, and provenance graphs with deterministic serialization.
"""

from collections import defaultdict
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID
from pydantic import BaseModel, Field

from episense.schemas.base import utc_now
from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.document import Document
from episense.schemas.event import FusedEvent
from episense.schemas.explainability import ExplainabilityDossier
from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin, SignalObservation
from episense.explainability.dossier import DossierGenerator
from episense.logging import get_logger

logger = get_logger("explainability.batch")


class ExplainabilityBatchReport(BaseModel):
    """
    Deterministic summary report for an explainability and audit batch execution.
    """
    total_alerts_processed: int = Field(ge=0)
    provenance_complete_alerts_count: int = Field(ge=0)
    provenance_incomplete_alerts_count: int = Field(ge=0)
    total_evidence_spans_reconstructed: int = Field(ge=0)
    valid_evidence_spans_count: int = Field(ge=0)
    invalid_evidence_spans_count: int = Field(ge=0)
    total_audit_trails_generated: int = Field(ge=0)
    total_provenance_graphs_generated: int = Field(ge=0)
    average_nodes_per_graph: float = Field(ge=0.0)
    average_edges_per_graph: float = Field(ge=0.0)
    elapsed_seconds: float = Field(ge=0.0)
    pipeline_version: str = "1.0.0"
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class ExplainabilityBatchRunner:
    """
    Coordinates batch generation of explainability dossiers and audit artifacts.
    """

    def __init__(
        self,
        output_dir: str = "data/explainability",
        dossier_generator: Optional[DossierGenerator] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generator = dossier_generator or DossierGenerator()

    def process_alerts(
        self,
        alerts: List[EpidemiologicalAlert],
        signals: Optional[List[SignalObservation]] = None,
        fused_events: Optional[List[FusedEvent]] = None,
        time_bins: Optional[List[EpidemiologicalTimeBin]] = None,
        baselines: Optional[List[BaselineEstimate]] = None,
        documents: Optional[List[Document]] = None,
        run_name: str = "batch_run",
    ) -> Tuple[ExplainabilityBatchReport, List[ExplainabilityDossier]]:
        """
        Processes a collection of alerts into comprehensive explainability dossiers.
        """
        t0 = time.time()

        # Build fast lookup indices
        sig_map: Dict[UUID, SignalObservation] = {}
        if signals:
            for s in signals:
                sig_map[s.signal_id] = s

        fused_map: Dict[UUID, FusedEvent] = {}
        if fused_events:
            for fe in fused_events:
                fused_map[fe.fused_event_id] = fe

        bin_map: Dict[Tuple[str, str, str], EpidemiologicalTimeBin] = {}
        if time_bins:
            for b in time_bins:
                key = (b.disease_key, b.geo_key, b.period_start.isoformat())
                bin_map[key] = b

        base_map: Dict[Tuple[str, str, str], BaselineEstimate] = {}
        if baselines:
            for base in baselines:
                key = (base.disease_key, base.geo_key, base.target_period_start.isoformat())
                base_map[key] = base

        doc_map: Dict[UUID, Union[Document, str]] = {}
        if documents:
            for d in documents:
                doc_map[d.document_id] = d
        # Also include any previously registered documents
        doc_map.update(self.generator.documents_map)

        dossiers: List[ExplainabilityDossier] = []
        total_spans = 0
        valid_spans = 0
        invalid_spans = 0
        complete_alerts = 0
        incomplete_alerts = 0
        total_nodes = 0
        total_edges = 0

        # Sort alerts deterministically by (composite_score desc, period_start desc, disease_key, geo_key)
        sorted_alerts = sorted(
            alerts,
            key=lambda a: (-a.composite_score, -a.period_start.timestamp(), a.disease_key, a.geo_key)
        )

        for alert in sorted_alerts:
            sig = sig_map.get(alert.signal_id)
            lookup_key = (alert.disease_key, alert.geo_key, alert.period_start.isoformat())
            tb = bin_map.get(lookup_key)
            base = base_map.get(lookup_key)

            supporting_fe = [
                fused_map[fid] for fid in alert.supporting_fused_event_ids if fid in fused_map
            ]

            dossier = self.generator.create_dossier(
                alert=alert,
                signal=sig,
                fused_events=supporting_fe,
                time_bin=tb,
                baseline=base,
                documents_map=doc_map,
            )
            dossiers.append(dossier)

            if dossier.provenance_complete:
                complete_alerts += 1
            else:
                incomplete_alerts += 1

            for span in dossier.reconstructed_evidence:
                total_spans += 1
                if span.is_valid:
                    valid_spans += 1
                else:
                    invalid_spans += 1

            total_nodes += len(dossier.provenance_graph.nodes)
            total_edges += len(dossier.provenance_graph.edges)

        n = len(dossiers)
        avg_nodes = round(total_nodes / n, 2) if n > 0 else 0.0
        avg_edges = round(total_edges / n, 2) if n > 0 else 0.0
        elapsed = round(time.time() - t0, 3)

        report = ExplainabilityBatchReport(
            total_alerts_processed=n,
            provenance_complete_alerts_count=complete_alerts,
            provenance_incomplete_alerts_count=incomplete_alerts,
            total_evidence_spans_reconstructed=total_spans,
            valid_evidence_spans_count=valid_spans,
            invalid_evidence_spans_count=invalid_spans,
            total_audit_trails_generated=n,
            total_provenance_graphs_generated=n,
            average_nodes_per_graph=avg_nodes,
            average_edges_per_graph=avg_edges,
            elapsed_seconds=elapsed,
        )

        # Serialize outputs deterministically
        run_dir = self.output_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "dossiers.json").write_text(
            json.dumps([d.model_dump(mode="json") for d in dossiers], indent=2),
            encoding="utf-8",
        )
        (run_dir / "audit_trails.json").write_text(
            json.dumps([d.audit_trail.model_dump(mode="json") for d in dossiers], indent=2),
            encoding="utf-8",
        )
        (run_dir / "explainability_batch_report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Summary for operators
        summary_items = []
        for d in dossiers[:15]:
            summary_items.append({
                "alert_id": str(d.alert_id),
                "disease": d.disease_key,
                "geo": d.geo_key,
                "tier": d.alert_tier.value.upper(),
                "score": d.composite_score,
                "summary": d.executive_summary,
                "checksum": d.audit_trail.audit_checksum[:16],
                "provenance_complete": d.provenance_complete,
                "spans_reconstructed": len(d.reconstructed_evidence),
            })

        (run_dir / "provenance_summary.json").write_text(
            json.dumps(
                {
                    "total_dossiers": n,
                    "complete_dossiers": complete_alerts,
                    "top_actionable_dossiers": summary_items,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        return report, dossiers

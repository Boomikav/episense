"""
Batch Processing Engine for EpiSense Event Fusion (Phase 7).
Transforms Phase 6 NLP outputs into canonical FusedEvents across benchmark and background corpora.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, Field

from episense.schemas.nlp import NLPOutput
from episense.schemas.event import EventCandidate, FusedEvent
from episense.schemas.base import utc_now
from episense.events.builder import EventCandidateBuilder
from episense.fusion.engine import EventFusionEngine
from episense.nlp.pipeline import NLPPipeline
from episense.logging import get_logger

logger = get_logger("events.batch")


class EventBatchReport(BaseModel):
    """
    Deterministic summary report for an event fusion batch processing run.
    """
    total_documents_processed: int = Field(ge=0)
    total_candidates_extracted: int = Field(ge=0)
    total_fused_events: int = Field(ge=0)
    multi_observation_event_count: int = Field(ge=0)
    single_observation_event_count: int = Field(ge=0)
    conflicting_quantity_event_count: int = Field(ge=0)
    average_observations_per_event: float = Field(ge=0.0)
    elapsed_seconds: float = Field(ge=0.0)
    fusion_window_days: int = 7
    pipeline_version: str = "1.0.0"
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class EventBatchRunner:
    """
    Coordinates batch extraction of event candidates and cross-document fusion.
    """

    def __init__(
        self,
        output_dir: str = "data/events",
        fusion_window_days: int = 7,
        nlp_pipeline: Optional[NLPPipeline] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fusion_window_days = fusion_window_days
        self.candidate_builder = EventCandidateBuilder()
        self.fusion_engine = EventFusionEngine(window_days=fusion_window_days)
        self.nlp_pipeline = nlp_pipeline or NLPPipeline(enable_cache=True)

    def process_corpus(
        self, corpus_paths: List[Union[str, Path]], run_name: str = "corpus_fusion"
    ) -> Tuple[EventBatchReport, List[FusedEvent], List[EventCandidate]]:
        """
        Loads documents from corpus manifests, extracts NLP representations,
        builds candidates, and fuses them into canonical events.
        """
        start_time = time.time()
        all_candidates: List[EventCandidate] = []
        doc_count = 0

        for path in corpus_paths:
            p = Path(path)
            if not p.exists():
                logger.warning(f"Corpus path not found: {p}")
                continue

            data = json.loads(p.read_text(encoding="utf-8"))
            documents = data.get("documents", [])

            for doc_entry in documents:
                doc_obj = doc_entry.get("document", doc_entry)
                doc_id_str = doc_obj.get("document_id")
                if not doc_id_str:
                    continue

                doc_id = UUID(doc_id_str)
                source_id = doc_obj.get("source_id", "unknown_source")
                pub_time_str = doc_obj.get("publication_timestamp")
                pub_time = None
                if pub_time_str:
                    try:
                        from datetime import datetime
                        pub_time = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
                    except Exception:
                        pub_time = None

                # Load raw text for offset invariant check
                raw_file = Path("data/raw") / f"{doc_id}.txt"
                raw_text = raw_file.read_text(encoding="utf-8") if raw_file.exists() else None

                # Process document with NLP pipeline
                nlp_output = self.nlp_pipeline.process_document(doc_id)
                doc_count += 1

                # Build event candidates
                candidates = self.candidate_builder.build_candidates(
                    nlp_output=nlp_output,
                    source_id=source_id,
                    publication_time=pub_time,
                    raw_text=raw_text,
                )
                all_candidates.extend(candidates)

        # Cross-document fusion
        fused_events = self.fusion_engine.fuse(all_candidates)

        elapsed = time.time() - start_time

        # Compute summary metrics
        multi_obs = sum(1 for fe in fused_events if fe.supporting_observation_count > 1)
        single_obs = sum(1 for fe in fused_events if fe.supporting_observation_count == 1)
        conflicts = sum(1 for fe in fused_events if fe.has_conflicts)
        avg_obs = len(all_candidates) / len(fused_events) if fused_events else 0.0

        report = EventBatchReport(
            total_documents_processed=doc_count,
            total_candidates_extracted=len(all_candidates),
            total_fused_events=len(fused_events),
            multi_observation_event_count=multi_obs,
            single_observation_event_count=single_obs,
            conflicting_quantity_event_count=conflicts,
            average_observations_per_event=round(avg_obs, 2),
            elapsed_seconds=round(elapsed, 2),
            fusion_window_days=self.fusion_window_days,
        )

        # Serialize outputs
        run_output_dir = self.output_dir / f"{run_name}_{int(start_time)}"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        report_path = run_output_dir / "batch_fusion_report.json"
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        events_path = run_output_dir / "fused_events.json"
        events_json = json.dumps([fe.model_dump(mode="json") for fe in fused_events], indent=2)
        events_path.write_text(events_json, encoding="utf-8")

        return report, fused_events, all_candidates

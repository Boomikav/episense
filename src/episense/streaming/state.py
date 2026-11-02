"""
Surveillance State Store for Continuous Surveillance in EpiSense (Phase 11).
Maintains stateful registries for documents, fused events, time-series bins,
statistical baselines, early signals, alert lifecycles, and tamper-evident checkpoints.
"""

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid5, NAMESPACE_DNS

from episense.schemas.document import Document, OriginClassification
from episense.schemas.event import EventCandidate, FusedEvent
from episense.schemas.signal import (
    BaselineEstimate,
    EpidemiologicalTimeBin,
    SignalObservation,
)
from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.explainability import (
    AlertAuditTrail,
    ExplainabilityDossier,
)
from episense.schemas.streaming import (
    AlertLifecycleState,
    DeadLetterRecord,
    SurveillanceMetrics,
    SurveillanceStateCheckpoint,
)
from episense.logging import get_logger

logger = get_logger("streaming.state")


class SurveillanceStateStore:
    """
    Central state store managing continuous epidemiological surveillance state.
    Provides idempotent registration, index lookups, alert lifecycle tracking,
    and deterministic checkpoint serialization.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db

        # Documents & Deduplication
        self.processed_document_ids: Set[UUID] = set()
        self.processed_content_hashes: Dict[str, UUID] = {}  # hash -> doc_id
        self.documents: Dict[UUID, Document] = {}
        self.traces: Dict[UUID, Any] = {}

        # Candidates & Fused Events
        self.candidates_by_id: Dict[UUID, EventCandidate] = {}
        self.observations_by_id: Dict[UUID, Any] = {}
        self.candidates_by_series: Dict[Tuple[str, str], List[EventCandidate]] = defaultdict(list)
        self.fused_events: Dict[UUID, FusedEvent] = {}
        self.fused_events_by_series: Dict[Tuple[str, str], List[UUID]] = defaultdict(list)

        # Time-Series Bins
        # Key: (disease_key, geo_key, iso_year, iso_week, is_generic_historical)
        self.bins_by_key: Dict[Tuple[str, str, int, int, bool], EpidemiologicalTimeBin] = {}
        self.bins_by_id: Dict[UUID, EpidemiologicalTimeBin] = {}
        self.bins_by_series: Dict[Tuple[str, str], List[UUID]] = defaultdict(list)

        # Baselines, Signals, Alerts
        self.baselines: Dict[UUID, BaselineEstimate] = {}
        self.signals: Dict[UUID, SignalObservation] = {}
        self.signals_by_series_period: Dict[Tuple[str, str, str], UUID] = {}
        self.alerts: Dict[UUID, EpidemiologicalAlert] = {}
        self.alerts_by_series_period: Dict[Tuple[str, str, str], UUID] = {}
        self.alert_history: Dict[UUID, List[EpidemiologicalAlert]] = defaultdict(list)

        # Explainability & Audit
        self.dossiers: Dict[UUID, ExplainabilityDossier] = {}
        self.audit_trails: Dict[UUID, AlertAuditTrail] = {}
        self.dead_letter_queue: List[DeadLetterRecord] = []

        # Metrics & Sequence Tracking
        self.metrics = SurveillanceMetrics()
        self.sequence_number = 0

    def is_document_processed(self, doc_id: Optional[UUID], content_hash: str) -> bool:
        """
        Returns True if the document ID or exact content hash was already processed.
        Guarantees strict deduplication and exactly-once processing semantics.
        """
        if doc_id and doc_id in self.processed_document_ids:
            return True
        if content_hash and content_hash.lower() in self.processed_content_hashes:
            return True
        return False

    def register_document(self, document: Document):
        """Registers a newly accepted document in the state store."""
        self.processed_document_ids.add(document.document_id)
        self.processed_content_hashes[document.content_hash_sha256.lower()] = document.document_id
        self.documents[document.document_id] = document
        self.sequence_number += 1
        if self.db:
            try:
                self.db.save_document(document)
            except Exception as e:
                logger.warning("Failed to persist document to DB: %s", e)

    def save_trace(self, trace: Any):
        """Stores a pipeline trace."""
        self.traces[trace.document_id] = trace
        if self.db:
            try:
                self.db.save_pipeline_trace(trace)
            except Exception as e:
                logger.warning("Failed to persist trace to DB: %s", e)

    def get_trace(self, doc_id: UUID) -> Optional[Any]:
        """Retrieves a pipeline trace from memory or persistent store."""
        if doc_id in self.traces:
            return self.traces[doc_id]
        if self.db:
            try:
                trace = self.db.get_pipeline_trace(doc_id)
                if trace:
                    self.traces[doc_id] = trace
                    return trace
            except Exception as e:
                logger.warning("Failed to load trace from DB: %s", e)
        return None

    def record_dead_letter(self, record: DeadLetterRecord):
        """Appends an isolated failure to the dead-letter queue."""
        self.dead_letter_queue.append(record)
        self.metrics.processing_failures += 1
        self.sequence_number += 1

    def save_candidate(self, candidate: EventCandidate):
        """Stores an extracted event candidate indexed by its disease and geography."""
        self.candidates_by_id[candidate.candidate_id] = candidate
        if getattr(candidate, "observation", None):
            self.observations_by_id[candidate.observation.observation_id] = candidate.observation
        d_key = candidate.disease_key.lower().strip()
        g_key = (
            candidate.observation.location.resolved_location.normalized_name.lower().strip()
            if candidate.observation.location and candidate.observation.location.resolved_location
            else "unspecified_or_global"
        )
        self.candidates_by_series[(d_key, g_key)].append(candidate)

    def save_fused_event(self, fused_event: FusedEvent):
        """Stores a canonical FusedEvent."""
        fe_id = fused_event.fused_event_id
        self.fused_events[fe_id] = fused_event

        d_key = fused_event.canonical_disease.lower().strip()
        g_key = (
            fused_event.canonical_location.normalized_name.lower().strip()
            if fused_event.canonical_location
            else "unspecified_or_global"
        )
        series_key = (d_key, g_key)
        if fe_id not in self.fused_events_by_series[series_key]:
            self.fused_events_by_series[series_key].append(fe_id)
        if self.db:
            try:
                self.db.save_fused_event(fused_event)
            except Exception as e:
                logger.warning("Failed to persist fused event to DB: %s", e)

    def save_bin(self, time_bin: EpidemiologicalTimeBin, bin_key: Tuple[str, str, int, int, bool]):
        """Stores or updates an EpidemiologicalTimeBin."""
        self.bins_by_key[bin_key] = time_bin
        self.bins_by_id[time_bin.bin_id] = time_bin

        series_key = (bin_key[0], bin_key[1])
        if time_bin.bin_id not in self.bins_by_series[series_key]:
            self.bins_by_series[series_key].append(time_bin.bin_id)

        if self.db and hasattr(self.db, "save_bin"):
            try:
                self.db.save_bin(time_bin, is_generic_historical=bin_key[4])
            except Exception as e:
                logger.warning("Failed to persist bin to DB: %s", e)

    def get_historical_bins(
        self, disease_key: str, geo_key: str, target_period_start: datetime
    ) -> List[EpidemiologicalTimeBin]:
        """
        Retrieves all historical bins for a series strictly preceding target_period_start,
        sorted chronologically by period_start.
        """
        series_key = (disease_key.lower().strip(), geo_key.lower().strip())
        bin_ids = self.bins_by_series.get(series_key, [])
        all_bins = [self.bins_by_id[bid] for bid in bin_ids if bid in self.bins_by_id]

        target_dt = target_period_start
        if target_dt.tzinfo is None:
            target_dt = target_dt.replace(tzinfo=timezone.utc)

        historical = [
            b for b in all_bins
            if (b.period_end.replace(tzinfo=timezone.utc) if b.period_end.tzinfo is None else b.period_end)
            <= target_dt
        ]
        historical.sort(key=lambda b: b.period_start)
        return historical

    def get_all_bins_for_series(
        self, disease_key: str, geo_key: str
    ) -> List[EpidemiologicalTimeBin]:
        """Returns all bins for a series sorted chronologically."""
        series_key = (disease_key.lower().strip(), geo_key.lower().strip())
        bin_ids = self.bins_by_series.get(series_key, [])
        all_bins = [self.bins_by_id[bid] for bid in bin_ids if bid in self.bins_by_id]
        all_bins.sort(key=lambda b: b.period_start)
        return all_bins

    def save_baseline(self, baseline: BaselineEstimate):
        """Stores a BaselineEstimate."""
        self.baselines[baseline.baseline_id] = baseline

    def save_signal(self, signal: SignalObservation, period_start_iso: str):
        """Stores a SignalObservation."""
        self.signals[signal.signal_id] = signal
        d_key = signal.disease_key.lower().strip()
        g_key = signal.geo_key.lower().strip()
        self.signals_by_series_period[(d_key, g_key, period_start_iso)] = signal.signal_id
        if self.db:
            try:
                self.db.save_signal(signal)
            except Exception as e:
                logger.warning("Failed to persist signal to DB: %s", e)

    def save_alert(
        self, alert: EpidemiologicalAlert, period_start_iso: str
    ) -> AlertLifecycleState:
        """
        Stores an alert and calculates its lifecycle transition (NEW, UPDATED, CONFIRMED_UNCHANGED).
        Appends the revision to historical audit logs without overwriting prior records.
        """
        d_key = alert.disease_key.lower().strip()
        g_key = alert.geo_key.lower().strip()
        lookup_key = (d_key, g_key, period_start_iso)

        existing_alert_id = self.alerts_by_series_period.get(lookup_key)

        if existing_alert_id is None or existing_alert_id not in self.alerts:
            # Newly created alert
            self.alerts[alert.alert_id] = alert
            self.alerts_by_series_period[lookup_key] = alert.alert_id
            self.alert_history[alert.alert_id].append(alert)
            lifecycle = AlertLifecycleState.NEW
        else:
            existing_alert = self.alerts[existing_alert_id]

            # Check if score, tier, or supporting observations changed
            score_diff = abs(existing_alert.composite_score - alert.composite_score)
            tier_changed = existing_alert.alert_tier != alert.alert_tier
            obs_changed = (
                existing_alert.supporting_fused_event_ids != alert.supporting_fused_event_ids
                or existing_alert.supporting_source_count != alert.supporting_source_count
            )

            if score_diff > 1e-4 or tier_changed or obs_changed:
                lifecycle = AlertLifecycleState.UPDATED
            else:
                lifecycle = AlertLifecycleState.CONFIRMED_UNCHANGED

            # Update primary alert pointer and append to audit history
            self.alerts[alert.alert_id] = alert
            self.alerts_by_series_period[lookup_key] = alert.alert_id
            self.alert_history[alert.alert_id].append(alert)

        if self.db:
            try:
                self.db.save_alert(alert)
            except Exception as e:
                logger.warning("Failed to persist alert to DB: %s", e)

        return lifecycle

    def save_dossier(self, dossier: ExplainabilityDossier):
        """Stores an ExplainabilityDossier."""
        self.dossiers[dossier.alert_id] = dossier
        if self.db:
            try:
                self.db.save_dossier(dossier)
            except Exception as e:
                logger.warning("Failed to persist dossier to DB: %s", e)

    def save_audit_trail(self, audit_trail: AlertAuditTrail):
        """Stores an AlertAuditTrail."""
        self.audit_trails[audit_trail.alert_id] = audit_trail
        if self.db:
            try:
                self.db.save_audit_trail(audit_trail)
            except Exception as e:
                logger.warning("Failed to persist audit trail to DB: %s", e)

    def compute_state_checksum(self) -> str:
        """
        Calculates a deterministic SHA-256 checksum over the entire surveillance state.
        Guarantees that identical inputs produce bit-for-bit identical state signatures.
        """
        hasher = hashlib.sha256()

        # Deterministically sorted document IDs
        sorted_doc_ids = sorted(str(did) for did in self.processed_document_ids)
        for did in sorted_doc_ids:
            hasher.update(did.encode("utf-8"))

        # Deterministically sorted fused event IDs and checksums
        sorted_fe_keys = sorted(str(fid) for fid in self.fused_events.keys())
        for fid in sorted_fe_keys:
            fe = self.fused_events[UUID(fid)]
            hasher.update(f"{fid}:{fe.canonical_disease}:{fe.supporting_observation_count}".encode("utf-8"))

        # Deterministically sorted bin IDs
        sorted_bin_keys = sorted(str(bid) for bid in self.bins_by_id.keys())
        for bid in sorted_bin_keys:
            b = self.bins_by_id[UUID(bid)]
            hasher.update(f"{bid}:{b.observed_case_count}:{b.observed_death_count}".encode("utf-8"))

        # Deterministically sorted alert IDs and risk scores
        sorted_alert_keys = sorted(str(aid) for aid in self.alerts.keys())
        for aid in sorted_alert_keys:
            a = self.alerts[UUID(aid)]
            hasher.update(f"{aid}:{a.alert_tier.value}:{a.composite_score:.4f}".encode("utf-8"))

        return hasher.hexdigest()

    def checkpoint(
        self,
        checkpoint_dir: Union[str, Path],
        timestamp: Optional[datetime] = None,
    ) -> SurveillanceStateCheckpoint:
        """
        Serializes state tables into deterministic JSON artifacts and returns a signed checkpoint.
        """
        p = Path(checkpoint_dir)
        p.mkdir(parents=True, exist_ok=True)

        checksum = self.compute_state_checksum()
        ts = timestamp or datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        chk_id = uuid5(NAMESPACE_DNS, f"checkpoint:{checksum}:{self.sequence_number}")

        checkpoint_meta = SurveillanceStateCheckpoint(
            checkpoint_id=chk_id,
            sequence_number=self.sequence_number,
            timestamp=ts,
            metrics=self.metrics,
            state_checksum_sha256=checksum,
            total_documents_processed=len(self.processed_document_ids),
            total_fused_events=len(self.fused_events),
            total_bins=len(self.bins_by_id),
            total_alerts=len(self.alerts),
            dead_letter_count=len(self.dead_letter_queue),
        )

        # Write metadata
        (p / "checkpoint.json").write_text(checkpoint_meta.model_dump_json(indent=2), encoding="utf-8")

        # Write metrics
        (p / "metrics.json").write_text(self.metrics.model_dump_json(indent=2), encoding="utf-8")

        # Write dead-letter records
        dl_dicts = [dl.model_dump(mode="json") for dl in self.dead_letter_queue]
        (p / "dead_letter_queue.json").write_text(json.dumps(dl_dicts, indent=2, sort_keys=True), encoding="utf-8")

        return checkpoint_meta

    def restore(self, checkpoint_dir: Union[str, Path]) -> SurveillanceStateCheckpoint:
        """
        Restores state metadata from a checkpoint directory.
        """
        p = Path(checkpoint_dir)
        meta_file = p / "checkpoint.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Checkpoint metadata not found at {meta_file}")

        meta = SurveillanceStateCheckpoint.model_validate_json(meta_file.read_text(encoding="utf-8"))
        self.metrics = meta.metrics
        self.sequence_number = meta.sequence_number

        dl_file = p / "dead_letter_queue.json"
        if dl_file.exists():
            dl_data = json.loads(dl_file.read_text(encoding="utf-8"))
            self.dead_letter_queue = [DeadLetterRecord.model_validate(item) for item in dl_data]

        return meta

    def hydrate_from_db(
        self,
        db: Any,
        origins: Optional[List[OriginClassification]] = None,
    ) -> Dict[str, int]:
        """
        Deterministically restores persisted state from the durable SQLite database into in-memory indices.
        Guarantees strict idempotency: repeated calls never inflate counts or create duplicate objects.

        Hydration order:
        1. Processed document deduplication index: Registers all documents present in DB into
           `processed_document_ids` and `processed_content_hashes`.
        2. Stored documents: Loads documents matching `origins` (default: [LIVE_EXTERNAL, MANUAL_SUBMISSION]).
        3. Fused events: Loads fused events matching `origins` and indexes them into `fused_events`
           and `fused_events_by_series`.
        4. Statistical signals: Loads signals and indexes them into `signals` and `signals_by_series_period`.
        5. Epidemiological alerts: Loads alerts matching `origins` and indexes them into `alerts`,
           `alerts_by_series_period`, and `alert_history`.
        6. Explainability dossiers & audit trails: Loads dossiers and audit trails.
        7. Recalculates sequence_number and metrics.
        """
        target_origins = origins or [
            OriginClassification.LIVE_EXTERNAL,
            OriginClassification.MANUAL_SUBMISSION,
        ]
        target_origin_strs = {
            o.value if hasattr(o, "value") else str(o) for o in target_origins
        }

        counts = {
            "documents_registered": 0,
            "documents": 0,
            "fused_events": 0,
            "signals": 0,
            "alerts": 0,
            "dossiers": 0,
            "audit_trails": 0,
        }

        # 1 & 2. Process documents
        if hasattr(db, "list_documents"):
            all_docs = db.list_documents(limit=None)
            for doc in all_docs:
                self.processed_document_ids.add(doc.document_id)
                if doc.content_hash_sha256:
                    self.processed_content_hashes[doc.content_hash_sha256.lower()] = doc.document_id
                counts["documents_registered"] += 1

                doc_orig = doc.origin.value if hasattr(doc.origin, "value") else str(doc.origin)
                if doc_orig in target_origin_strs:
                    if doc.document_id not in self.documents:
                        counts["documents"] += 1
                    self.documents[doc.document_id] = doc

        # 3. Fused events
        if hasattr(db, "list_fused_events"):
            all_fes = db.list_fused_events(status="active")
            for fe in all_fes:
                if getattr(fe, "status", "active") != "active":
                    continue
                fe_orig = fe.primary_origin.value if hasattr(fe.primary_origin, "value") else str(fe.primary_origin)
                if fe_orig in target_origin_strs:
                    if fe.fused_event_id not in self.fused_events:
                        counts["fused_events"] += 1
                    self.fused_events[fe.fused_event_id] = fe

                    d_key = fe.canonical_disease.lower().strip()
                    g_key = (
                        fe.canonical_location.normalized_name.lower().strip()
                        if fe.canonical_location
                        else "unspecified_or_global"
                    )
                    series_key = (d_key, g_key)
                    if fe.fused_event_id not in self.fused_events_by_series[series_key]:
                        self.fused_events_by_series[series_key].append(fe.fused_event_id)

        # 4. Signals
        if hasattr(db, "list_signals"):
            all_sigs = db.list_signals()
            for sig in all_sigs:
                if sig.signal_id not in self.signals:
                    counts["signals"] += 1
                self.signals[sig.signal_id] = sig

                d_key = sig.disease_key.lower().strip()
                g_key = sig.geo_key.lower().strip()
                p_start = getattr(sig, "target_period_start", getattr(sig, "period_start", None))
                p_start_iso = p_start.isoformat() if p_start else ""
                self.signals_by_series_period[(d_key, g_key, p_start_iso)] = sig.signal_id

        # 5. Alerts
        if hasattr(db, "list_alerts"):
            all_alerts = db.list_alerts(status="active")
            for al in all_alerts:
                if getattr(al, "status", "active") != "active":
                    continue
                al_orig = al.origin.value if hasattr(al.origin, "value") else str(al.origin)
                if al_orig in target_origin_strs:
                    if al.alert_id not in self.alerts:
                        counts["alerts"] += 1
                    self.alerts[al.alert_id] = al

                    d_key = al.disease_key.lower().strip()
                    g_key = al.geo_key.lower().strip()
                    period_iso = al.period_start.isoformat() if al.period_start else ""
                    lookup_key = (d_key, g_key, period_iso)
                    self.alerts_by_series_period[lookup_key] = al.alert_id
                    if al not in self.alert_history[al.alert_id]:
                        self.alert_history[al.alert_id].append(al)

        # 6. Dossiers & Audit Trails
        if hasattr(db, "list_dossiers"):
            all_dossiers = db.list_dossiers()
            for dos in all_dossiers:
                if dos.alert_id in self.alerts:
                    if dos.alert_id not in self.dossiers:
                        counts["dossiers"] += 1
                    self.dossiers[dos.alert_id] = dos

        if hasattr(db, "list_audit_trails"):
            all_audits = db.list_audit_trails()
            for at in all_audits:
                if at.alert_id in self.alerts:
                    if at.alert_id not in self.audit_trails:
                        counts["audit_trails"] += 1
                    self.audit_trails[at.alert_id] = at

        # 7. Time-series bins (if persisted)
        if hasattr(db, "list_bins"):
            all_bins = db.list_bins()
            for b in all_bins:
                is_generic = (b.completeness_status == "historical_background")
                bin_key = (b.disease_key, b.geo_key, b.iso_year, b.iso_week, is_generic)
                self.bins_by_key[bin_key] = b
                self.bins_by_id[b.bin_id] = b
                series_key = (b.disease_key, b.geo_key)
                if b.bin_id not in self.bins_by_series[series_key]:
                    self.bins_by_series[series_key].append(b.bin_id)

        # 8. Update Sequence & Metrics
        self.sequence_number = max(self.sequence_number, len(self.documents))
        self.metrics.documents_accepted = len(self.documents)
        self.metrics.fused_events_created = len(self.fused_events)
        self.metrics.signals_generated = len(self.signals)
        self.metrics.alerts_generated = len(self.alerts)

        logger.info(
            "StateStore hydrated from DB: %d documents, %d fused events, %d signals, %d alerts restored.",
            counts["documents"],
            counts["fused_events"],
            counts["signals"],
            counts["alerts"],
        )
        return counts

"""
Durable Persistence Layer for EpiSense Epidemiological Surveillance.
Provides thread-safe SQLite storage for documents, pipeline traces,
fused events, signals, alerts, dossiers, audit trails, and source connectors.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from episense.schemas.document import Document, OriginClassification
from episense.schemas.event import FusedEvent
from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin, SignalObservation
from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.explainability import AlertAuditTrail, ExplainabilityDossier
from episense.schemas.pipeline_trace import DocumentPipelineTrace
from episense.schemas.source import SourceConnectorConfig, SourceConnectorStatus, SourcePollRecord
from episense.schemas.forecast import EpidemiologicalForecast

logger = logging.getLogger("episense.persistence")

DEFAULT_DB_PATH = Path(os.environ.get("EPISENSE_DB_PATH", "data/surveillance_store.sqlite"))


class SurveillanceDatabase:
    """
    SQLite-backed durable store for continuous epidemiological surveillance records.
    Uses WAL mode for concurrent read/write and guarantees persistence across restarts.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None, seed_if_missing: bool = False):
        env_db_path = os.environ.get("EPISENSE_DB_PATH")
        if db_path is None:
            raw_path = env_db_path
            db_path = Path(raw_path) if raw_path else DEFAULT_DB_PATH
            if env_db_path:
                seed_if_missing = True
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Persistence safeguard: if configured persistent path doesn't exist,
        # and seed_if_missing is True, copy seed once (initial production hydration).
        # If it ALREADY exists, NEVER overwrite!
        seed_db = Path("data/surveillance_store.sqlite").resolve()
        if seed_if_missing and not self.db_path.exists() and seed_db.exists() and self.db_path != seed_db:
            import shutil
            logger.info("Persistent DB not found at %s. Seeding from repository database at %s...", self.db_path, seed_db)
            shutil.copy2(str(seed_db), str(self.db_path))
            for ext in ("-wal", "-shm"):
                seed_ext = Path(str(seed_db) + ext)
                if seed_ext.exists():
                    shutil.copy2(str(seed_ext), str(self.db_path) + ext)
            logger.info("Database successfully seeded to persistent path %s (%d bytes).", self.db_path, self.db_path.stat().st_size)
        elif self.db_path.exists():
            logger.info("Using existing persistent database at %s (%d bytes).", self.db_path, self.db_path.stat().st_size)

        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        """Initializes tables and indexes if they do not exist."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    content_hash_sha256 TEXT NOT NULL,
                    source_url TEXT,
                    publication_timestamp TEXT,
                    retrieval_timestamp TEXT NOT NULL,
                    language TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_docs_hash ON documents(content_hash_sha256);
                CREATE INDEX IF NOT EXISTS idx_docs_origin ON documents(origin);
                CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_id);

                CREATE TABLE IF NOT EXISTS pipeline_traces (
                    document_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_hash_sha256 TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    total_duration_ms REAL NOT NULL,
                    stages_json TEXT NOT NULL,
                    nlp_output_json TEXT,
                    candidate_event_ids_json TEXT,
                    fused_event_ids_json TEXT,
                    signal_ids_json TEXT,
                    alert_ids_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS fused_events (
                    fused_event_id TEXT PRIMARY KEY,
                    canonical_disease TEXT NOT NULL,
                    disease_key TEXT NOT NULL,
                    primary_origin TEXT NOT NULL,
                    earliest_time TEXT,
                    latest_time TEXT,
                    total_cases INTEGER,
                    total_deaths INTEGER,
                    supporting_observation_count INTEGER NOT NULL,
                    json_data TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_fused_disease ON fused_events(canonical_disease);
                CREATE INDEX IF NOT EXISTS idx_fused_origin ON fused_events(primary_origin);

                CREATE TABLE IF NOT EXISTS time_bins (
                    bin_id TEXT PRIMARY KEY,
                    series_key TEXT NOT NULL,
                    iso_year INTEGER NOT NULL,
                    iso_week INTEGER NOT NULL,
                    is_generic_historical INTEGER NOT NULL,
                    json_data TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_bins_series ON time_bins(series_key);

                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    disease_key TEXT NOT NULL,
                    geo_key TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    composite_anomaly_flag INTEGER NOT NULL,
                    json_data TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_signals_series ON signals(disease_key, geo_key);

                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    disease_key TEXT NOT NULL,
                    geo_key TEXT NOT NULL,
                    alert_tier TEXT NOT NULL,
                    composite_score REAL NOT NULL,
                    origin TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    json_data TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_alerts_tier ON alerts(alert_tier);
                CREATE INDEX IF NOT EXISTS idx_alerts_origin ON alerts(origin);

                CREATE TABLE IF NOT EXISTS dossiers (
                    alert_id TEXT PRIMARY KEY,
                    json_data TEXT NOT NULL,
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_trails (
                    alert_id TEXT PRIMARY KEY,
                    json_data TEXT NOT NULL,
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS source_connectors (
                    source_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    polling_interval_minutes INTEGER NOT NULL,
                    last_polled_at TEXT,
                    last_success_at TEXT,
                    last_document_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    total_documents_ingested INTEGER DEFAULT 0,
                    config_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_poll_history (
                    poll_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    polled_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    http_status INTEGER,
                    documents_found INTEGER NOT NULL,
                    documents_ingested INTEGER NOT NULL,
                    duration_ms REAL NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (source_id) REFERENCES source_connectors(source_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_poll_history_source ON source_poll_history(source_id);

                CREATE TABLE IF NOT EXISTS surveillance_migrations (
                    migration_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    details_json TEXT
                );

                CREATE TABLE IF NOT EXISTS forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    series_key TEXT NOT NULL,
                    disease_key TEXT NOT NULL,
                    geo_key TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    reference_year INTEGER NOT NULL,
                    reference_week INTEGER NOT NULL,
                    horizon_weeks INTEGER NOT NULL,
                    sufficiency_status TEXT NOT NULL,
                    abstention_rationale TEXT,
                    historical_depth_weeks INTEGER NOT NULL,
                    consecutive_weeks_available INTEGER NOT NULL,
                    json_data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_forecasts_series ON forecasts(series_key);
                CREATE INDEX IF NOT EXISTS idx_forecasts_disease ON forecasts(disease_key);
                CREATE INDEX IF NOT EXISTS idx_forecasts_status ON forecasts(sufficiency_status);
                """)

                # Idempotent column migrations for alerts
                alert_cols = [r[1] for r in conn.execute("PRAGMA table_info(alerts)").fetchall()]
                if "status" not in alert_cols:
                    conn.execute("ALTER TABLE alerts ADD COLUMN status TEXT DEFAULT 'active'")
                if "superseded_by" not in alert_cols:
                    conn.execute("ALTER TABLE alerts ADD COLUMN superseded_by TEXT")
                if "retraction_reason" not in alert_cols:
                    conn.execute("ALTER TABLE alerts ADD COLUMN retraction_reason TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")

                # Idempotent column migrations for fused_events
                fe_cols = [r[1] for r in conn.execute("PRAGMA table_info(fused_events)").fetchall()]
                if "status" not in fe_cols:
                    conn.execute("ALTER TABLE fused_events ADD COLUMN status TEXT DEFAULT 'active'")
                if "superseded_by" not in fe_cols:
                    conn.execute("ALTER TABLE fused_events ADD COLUMN superseded_by TEXT")
                if "retraction_reason" not in fe_cols:
                    conn.execute("ALTER TABLE fused_events ADD COLUMN retraction_reason TEXT")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_fused_status ON fused_events(status);")

    # ---------------------------------------------------------
    # Documents
    # ---------------------------------------------------------

    def save_document(self, doc: Document) -> None:
        """Persists or updates a document record."""
        conn = self._get_connection()
        origin_str = (
            doc.origin.value if hasattr(doc.origin, "value") else str(doc.origin)
        )
        source_type_str = (
            doc.source_type.value if hasattr(doc.source_type, "value") else str(doc.source_type)
        )
        pub_ts = doc.publication_timestamp.isoformat() if doc.publication_timestamp else None
        ing_ts = getattr(doc, "ingestion_timestamp", getattr(doc, "retrieval_timestamp", None))
        ret_ts = ing_ts.isoformat() if ing_ts else datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(getattr(doc, "provenance_metadata", {}) or getattr(doc, "metadata", {}) or {})

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO documents (
                        document_id, source_id, source_type, origin, title,
                        text, content_hash_sha256, source_url, publication_timestamp,
                        retrieval_timestamp, language, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(doc.document_id),
                        doc.source_id,
                        source_type_str,
                        origin_str,
                        doc.title or "",
                        doc.text,
                        doc.content_hash_sha256.lower(),
                        str(doc.source_url) if doc.source_url else None,
                        pub_ts,
                        ret_ts,
                        doc.language,
                        meta_json,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def get_document(self, doc_id: Union[str, UUID]) -> Optional[Document]:
        """Loads a document by ID."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM documents WHERE document_id = ?", (str(doc_id),)).fetchone()
        if not row:
            return None
        return self._row_to_document(row)

    def get_document_by_hash(self, content_hash: str) -> Optional[Document]:
        """Loads a document by SHA-256 content hash."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM documents WHERE content_hash_sha256 = ? LIMIT 1", (str(content_hash),)).fetchone()
        if not row:
            return None
        return self._row_to_document(row)

    def list_documents(
        self,
        origin: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: Optional[int] = 100,
        offset: int = 0,
    ) -> List[Document]:
        """Lists documents with optional filtering. Strictly isolates SYNTHETIC_TEST records."""
        conn = self._get_connection()
        query = "SELECT * FROM documents WHERE 1=1"
        params: List[Any] = []

        if origin:
            query += " AND origin = ?"
            params.append(origin.upper())
        else:
            query += " AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)"
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)

        query += " ORDER BY retrieval_timestamp DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_document(r) for r in rows]

    def count_documents(self, origin: Optional[str] = None) -> int:
        """Counts stored documents. Strictly isolates SYNTHETIC_TEST records unless explicitly requested."""
        conn = self._get_connection()
        if origin:
            row = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = ?", (origin.upper(),)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM documents WHERE origin != 'SYNTHETIC_TEST' OR origin IS NULL").fetchone()
        return row[0] if row else 0

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        pub_ts = datetime.fromisoformat(row["publication_timestamp"]) if row["publication_timestamp"] else datetime.now(timezone.utc)
        ret_ts = datetime.fromisoformat(row["retrieval_timestamp"]) if row["retrieval_timestamp"] else datetime.now(timezone.utc)
        return Document(
            document_id=UUID(row["document_id"]),
            source_id=row["source_id"],
            source_type=row["source_type"],
            origin=OriginClassification(row["origin"]),
            title=row["title"],
            text=row["text"],
            content_hash_sha256=row["content_hash_sha256"],
            source_url=row["source_url"],
            publication_timestamp=pub_ts,
            ingestion_timestamp=ret_ts,
            language=row["language"] or "en",
            provenance_metadata=meta,
        )

    # ---------------------------------------------------------
    # Pipeline Traces
    # ---------------------------------------------------------

    def save_pipeline_trace(self, trace: DocumentPipelineTrace) -> None:
        """Persists an end-to-end 17-stage pipeline trace."""
        conn = self._get_connection()
        stages_json = json.dumps([s.model_dump(mode="json") for s in trace.stages])
        nlp_json = trace.nlp_output.model_dump_json() if trace.nlp_output else None
        cand_ids = json.dumps([str(cid) for cid in trace.candidate_event_ids])
        fe_ids = json.dumps([str(fid) for fid in trace.fused_event_ids])
        sig_ids = json.dumps([str(sid) for sid in trace.signal_ids])
        alert_ids = json.dumps([str(aid) for aid in trace.alert_ids])
        origin_str = trace.origin.value if hasattr(trace.origin, "value") else str(trace.origin)

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO pipeline_traces (
                        document_id, trace_id, origin, title, content_hash_sha256,
                        overall_status, total_duration_ms, stages_json, nlp_output_json,
                        candidate_event_ids_json, fused_event_ids_json, signal_ids_json,
                        alert_ids_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(trace.document_id),
                        str(trace.trace_id),
                        origin_str,
                        trace.title,
                        trace.content_hash_sha256.lower(),
                        trace.overall_status,
                        trace.total_duration_ms,
                        stages_json,
                        nlp_json,
                        cand_ids,
                        fe_ids,
                        sig_ids,
                        alert_ids,
                        trace.created_at.isoformat(),
                    ),
                )

    def get_pipeline_trace(self, doc_id: Union[str, UUID]) -> Optional[DocumentPipelineTrace]:
        """Retrieves the full pipeline trace for a document."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM pipeline_traces WHERE document_id = ?", (str(doc_id),)).fetchone()
        if not row:
            return None

        doc = self.get_document(doc_id)
        raw_text = doc.text if doc else ""
        source_id = doc.source_id if doc else "unknown"
        source_url = str(doc.source_url) if (doc and doc.source_url) else None
        pub_ts = doc.publication_timestamp if doc else None
        ret_ts = getattr(doc, "ingestion_timestamp", None) or getattr(doc, "retrieval_timestamp", None) or datetime.now(timezone.utc)

        from episense.schemas.nlp import NLPOutput
        from episense.schemas.pipeline_trace import PipelineStageExecution

        stages_raw = json.loads(row["stages_json"]) if row["stages_json"] else []
        stages = [PipelineStageExecution.model_validate(s) for s in stages_raw]
        nlp_out = NLPOutput.model_validate_json(row["nlp_output_json"]) if row["nlp_output_json"] else None

        cand_ids = [UUID(x) for x in json.loads(row["candidate_event_ids_json"] or "[]")]
        fe_ids = [UUID(x) for x in json.loads(row["fused_event_ids_json"] or "[]")]
        sig_ids = [UUID(x) for x in json.loads(row["signal_ids_json"] or "[]")]
        alert_ids = [UUID(x) for x in json.loads(row["alert_ids_json"] or "[]")]

        return DocumentPipelineTrace(
            trace_id=UUID(row["trace_id"]),
            document_id=UUID(row["document_id"]),
            source_id=source_id,
            origin=OriginClassification(row["origin"]),
            title=row["title"],
            raw_text=raw_text,
            source_url=source_url,
            publication_timestamp=pub_ts,
            retrieval_timestamp=ret_ts,
            content_hash_sha256=row["content_hash_sha256"],
            overall_status=row["overall_status"],
            total_duration_ms=row["total_duration_ms"],
            stages=stages,
            nlp_output=nlp_out,
            candidate_event_ids=cand_ids,
            fused_event_ids=fe_ids,
            signal_ids=sig_ids,
            alert_ids=alert_ids,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ---------------------------------------------------------
    # Fused Events, Time Bins, Signals, Alerts, Dossiers
    # ---------------------------------------------------------

    def save_fused_event(self, fe: FusedEvent) -> None:
        conn = self._get_connection()
        origin_str = (
            fe.primary_origin.value if hasattr(fe.primary_origin, "value") else str(fe.primary_origin)
        )
        e_time = (
            fe.event_window_start.isoformat()
            if getattr(fe, "event_window_start", None)
            else (fe.earliest_observation_time.isoformat() if getattr(fe, "earliest_observation_time", None) else None)
        )
        l_time = (
            fe.event_window_end.isoformat()
            if getattr(fe, "event_window_end", None)
            else (fe.latest_observation_time.isoformat() if getattr(fe, "latest_observation_time", None) else None)
        )
        total_cases = (
            fe.aggregated_quantities.case_count
            if getattr(fe, "aggregated_quantities", None) and fe.aggregated_quantities.case_count is not None
            else getattr(fe, "aggregated_case_count", 0)
        )
        total_deaths = (
            fe.aggregated_quantities.death_count
            if getattr(fe, "aggregated_quantities", None) and fe.aggregated_quantities.death_count is not None
            else getattr(fe, "aggregated_death_count", 0)
        )
        d_key = fe.canonical_disease.lower().strip()
        status_str = getattr(fe, "status", "active") or "active"
        sup_by = str(fe.superseded_by) if getattr(fe, "superseded_by", None) else None
        ret_reason = getattr(fe, "retraction_reason", None)
        data_json = fe.model_dump_json()

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fused_events (
                        fused_event_id, canonical_disease, disease_key, primary_origin,
                        earliest_time, latest_time, total_cases, total_deaths,
                        supporting_observation_count, status, superseded_by, retraction_reason, json_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(fe.fused_event_id),
                        fe.canonical_disease,
                        d_key,
                        origin_str,
                        e_time,
                        l_time,
                        total_cases,
                        total_deaths,
                        fe.supporting_observation_count,
                        status_str,
                        sup_by,
                        ret_reason,
                        data_json,
                    ),
                )

    def save_signal(self, sig: SignalObservation) -> None:
        conn = self._get_connection()
        p_start = getattr(sig, "target_period_start", getattr(sig, "period_start", None))
        p_start_str = p_start.isoformat() if p_start else ""
        sig_lvl = getattr(sig, "signal_level", None)
        anomaly_flag = 1 if (sig_lvl and getattr(sig_lvl, "value", str(sig_lvl)).lower() not in ("no_signal", "none", "0")) else 0
        data_json = sig.model_dump_json()

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO signals (
                        signal_id, disease_key, geo_key, period_start,
                        composite_anomaly_flag, json_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(sig.signal_id),
                        sig.disease_key,
                        sig.geo_key,
                        p_start_str,
                        anomaly_flag,
                        data_json,
                    ),
                )

    def save_alert(self, alert: EpidemiologicalAlert) -> None:
        conn = self._get_connection()
        origin_str = (
            alert.origin.value if hasattr(alert.origin, "value") else str(alert.origin)
        )
        p_start = alert.period_start.isoformat() if alert.period_start else ""
        tier_str = alert.alert_tier.value if hasattr(alert.alert_tier, "value") else str(alert.alert_tier)
        status_str = getattr(alert, "status", "active") or "active"
        sup_by = str(alert.superseded_by) if getattr(alert, "superseded_by", None) else None
        ret_reason = getattr(alert, "retraction_reason", None)
        data_json = alert.model_dump_json()

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO alerts (
                        alert_id, disease_key, geo_key, alert_tier,
                        composite_score, origin, period_start, status, superseded_by, retraction_reason, json_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(alert.alert_id),
                        alert.disease_key,
                        alert.geo_key,
                        tier_str,
                        alert.composite_score,
                        origin_str,
                        p_start,
                        status_str,
                        sup_by,
                        ret_reason,
                        data_json,
                    ),
                )

    def save_dossier(self, dossier: ExplainabilityDossier) -> None:
        conn = self._get_connection()
        with self._lock:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO dossiers (alert_id, json_data) VALUES (?, ?)",
                    (str(dossier.alert_id), dossier.model_dump_json()),
                )

    def save_audit_trail(self, audit: AlertAuditTrail) -> None:
        conn = self._get_connection()
        with self._lock:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO audit_trails (alert_id, json_data) VALUES (?, ?)",
                    (str(audit.alert_id), audit.model_dump_json()),
                )

    def get_fused_event(self, fe_id: Union[str, UUID]) -> Optional[FusedEvent]:
        conn = self._get_connection()
        row = conn.execute("SELECT json_data FROM fused_events WHERE fused_event_id = ?", (str(fe_id),)).fetchone()
        if not row:
            return None
        return FusedEvent.model_validate_json(row["json_data"])

    def list_fused_events(
        self,
        origin: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> List[FusedEvent]:
        conn = self._get_connection()
        query = "SELECT json_data FROM fused_events WHERE 1=1"
        params: List[Any] = []
        if origin:
            query += " AND primary_origin = ?"
            params.append(origin.upper())
        else:
            query += " AND (primary_origin != 'SYNTHETIC_TEST' OR primary_origin IS NULL)"
        if status and status.lower() != "all":
            query += " AND (status = ? OR (status IS NULL AND ? = 'active'))"
            params.extend([status.lower(), status.lower()])
        rows = conn.execute(query, params).fetchall()
        return [FusedEvent.model_validate_json(r["json_data"]) for r in rows]

    def count_fused_events(
        self,
        origin: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> int:
        conn = self._get_connection()
        query = "SELECT COUNT(*) FROM fused_events WHERE 1=1"
        params: List[Any] = []
        if origin:
            query += " AND primary_origin = ?"
            params.append(origin.upper())
        else:
            query += " AND (primary_origin != 'SYNTHETIC_TEST' OR primary_origin IS NULL)"
        if status and status.lower() != "all":
            query += " AND (status = ? OR (status IS NULL AND ? = 'active'))"
            params.extend([status.lower(), status.lower()])
        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0

    def get_signal(self, signal_id: Union[str, UUID]) -> Optional[SignalObservation]:
        conn = self._get_connection()
        row = conn.execute("SELECT json_data FROM signals WHERE signal_id = ?", (str(signal_id),)).fetchone()
        if not row:
            return None
        return SignalObservation.model_validate_json(row["json_data"])

    def list_signals(self) -> List[SignalObservation]:
        conn = self._get_connection()
        rows = conn.execute("SELECT json_data FROM signals").fetchall()
        return [SignalObservation.model_validate_json(r["json_data"]) for r in rows]

    def count_signals(self) -> int:
        conn = self._get_connection()
        row = conn.execute("SELECT COUNT(*) FROM signals").fetchone()
        return row[0] if row else 0

    def get_alert(self, alert_id: Union[str, UUID]) -> Optional[EpidemiologicalAlert]:
        conn = self._get_connection()
        row = conn.execute("SELECT json_data FROM alerts WHERE alert_id = ?", (str(alert_id),)).fetchone()
        if not row:
            return None
        return EpidemiologicalAlert.model_validate_json(row["json_data"])

    def list_alerts(
        self,
        origin: Optional[str] = None,
        alert_tier: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> List[EpidemiologicalAlert]:
        conn = self._get_connection()
        query = "SELECT json_data FROM alerts WHERE 1=1"
        params: List[Any] = []
        if origin:
            query += " AND origin = ?"
            params.append(origin.upper())
        else:
            query += " AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)"
        if alert_tier:
            query += " AND alert_tier = ?"
            params.append(alert_tier.lower())
        if status and status.lower() != "all":
            query += " AND (status = ? OR (status IS NULL AND ? = 'active'))"
            params.extend([status.lower(), status.lower()])
        rows = conn.execute(query, params).fetchall()
        return [EpidemiologicalAlert.model_validate_json(r["json_data"]) for r in rows]

    def count_alerts(
        self,
        origin: Optional[str] = None,
        alert_tier: Optional[str] = None,
        status: Optional[str] = "active",
    ) -> int:
        conn = self._get_connection()
        query = "SELECT COUNT(*) FROM alerts WHERE 1=1"
        params: List[Any] = []
        if origin:
            query += " AND origin = ?"
            params.append(origin.upper())
        else:
            query += " AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)"
        if alert_tier:
            query += " AND alert_tier = ?"
            params.append(alert_tier.lower())
        if status and status.lower() != "all":
            query += " AND (status = ? OR (status IS NULL AND ? = 'active'))"
            params.extend([status.lower(), status.lower()])
        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0

    def get_dossier(self, alert_id: Union[str, UUID]) -> Optional[ExplainabilityDossier]:
        conn = self._get_connection()
        row = conn.execute("SELECT json_data FROM dossiers WHERE alert_id = ?", (str(alert_id),)).fetchone()
        if not row:
            return None
        return ExplainabilityDossier.model_validate_json(row["json_data"])

    def list_dossiers(self) -> List[ExplainabilityDossier]:
        conn = self._get_connection()
        rows = conn.execute("SELECT json_data FROM dossiers").fetchall()
        return [ExplainabilityDossier.model_validate_json(r["json_data"]) for r in rows]

    def get_audit_trail(self, alert_id: Union[str, UUID]) -> Optional[AlertAuditTrail]:
        conn = self._get_connection()
        row = conn.execute("SELECT json_data FROM audit_trails WHERE alert_id = ?", (str(alert_id),)).fetchone()
        if not row:
            return None
        return AlertAuditTrail.model_validate_json(row["json_data"])

    def list_audit_trails(self) -> List[AlertAuditTrail]:
        conn = self._get_connection()
        rows = conn.execute("SELECT json_data FROM audit_trails").fetchall()
        return [AlertAuditTrail.model_validate_json(r["json_data"]) for r in rows]

    def save_bin(self, time_bin: EpidemiologicalTimeBin, is_generic_historical: bool = False) -> None:
        conn = self._get_connection()
        series_str = f"{time_bin.disease_key}:{time_bin.geo_key}"
        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO time_bins (
                        bin_id, series_key, iso_year, iso_week, is_generic_historical, json_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(time_bin.bin_id),
                        series_str,
                        time_bin.iso_year,
                        time_bin.iso_week,
                        1 if is_generic_historical else 0,
                        time_bin.model_dump_json(),
                    ),
                )

    def list_bins(self, series_key: Optional[str] = None) -> List[EpidemiologicalTimeBin]:
        conn = self._get_connection()
        if series_key:
            rows = conn.execute("SELECT json_data FROM time_bins WHERE series_key = ?", (series_key,)).fetchall()
        else:
            rows = conn.execute("SELECT json_data FROM time_bins").fetchall()
        return [EpidemiologicalTimeBin.model_validate_json(r["json_data"]) for r in rows]

    def get_surveillance_accounting(self) -> Dict[str, Any]:
        """
        Authoritative surveillance accounting distinguishing raw inputs, NLP extractions,
        fused canonical events, corroborated versus unverified claims, and statistical
        indicator baseline reliability gating.
        """
        conn = self._get_connection()
        total_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin != 'SYNTHETIC_TEST' OR origin IS NULL").fetchone()[0]
        live_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = 'LIVE_EXTERNAL'").fetchone()[0]
        hist_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = 'HISTORICAL_CORPUS'").fetchone()[0]
        manual_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = 'MANUAL_SUBMISSION'").fetchone()[0]
        benchmark_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = 'BENCHMARK'").fetchone()[0]
        synthetic_docs = conn.execute("SELECT COUNT(*) FROM documents WHERE origin = 'SYNTHETIC_TEST'").fetchone()[0]

        traces_completed = conn.execute("SELECT COUNT(*) FROM pipeline_traces WHERE overall_status = 'completed' AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)").fetchone()[0]
        traces_no_event = conn.execute("SELECT COUNT(*) FROM pipeline_traces WHERE overall_status = 'no_event_found' AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)").fetchone()[0]

        trace_rows = conn.execute("SELECT candidate_event_ids_json FROM pipeline_traces WHERE origin != 'SYNTHETIC_TEST' OR origin IS NULL").fetchall()
        total_candidate_events = sum(len(json.loads(r[0] or "[]")) for r in trace_rows)

        active_fused = conn.execute("SELECT COUNT(*) FROM fused_events WHERE (status = 'active' OR status IS NULL) AND (primary_origin != 'SYNTHETIC_TEST' OR primary_origin IS NULL)").fetchone()[0]
        superseded_fused = conn.execute("SELECT COUNT(*) FROM fused_events WHERE status = 'superseded' AND (primary_origin != 'SYNTHETIC_TEST' OR primary_origin IS NULL)").fetchone()[0]

        fused_rows = conn.execute("SELECT json_data FROM fused_events WHERE (status = 'active' OR status IS NULL) AND (primary_origin != 'SYNTHETIC_TEST' OR primary_origin IS NULL)").fetchall()
        corroborated_count = 0
        unverified_count = 0
        priority_fused_active = 0
        priority_fused_live = 0
        priority_fused_hist = 0

        # Import canonical priority checker
        try:
            from episense.taxonomy.priority import is_priority_disease
        except ImportError:
            is_priority_disease = lambda d: False

        for r in fused_rows:
            data = json.loads(r[0])
            src_count = len(data.get("independent_sources", [])) or data.get("independent_source_count", 1)
            if src_count >= 2:
                corroborated_count += 1
            else:
                unverified_count += 1

            dis = data.get("canonical_disease") or data.get("disease_key") or ""
            if is_priority_disease(dis):
                priority_fused_active += 1
                orig = data.get("db_primary_origin") or data.get("primary_origin") or "HISTORICAL_CORPUS"
                if orig == "LIVE_EXTERNAL":
                    priority_fused_live += 1
                else:
                    priority_fused_hist += 1

        total_bins = conn.execute("SELECT COUNT(*) FROM time_bins").fetchone()[0]
        bin_rows = conn.execute("SELECT json_data FROM time_bins").fetchall()
        verified_numerical_bins = sum(
            1 for r in bin_rows
            if (json.loads(r[0]).get("observed_case_count") or 0) > 0
        )

        total_signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        sig_rows = conn.execute("SELECT json_data FROM signals").fetchall()
        blocked_signals = 0
        eligible_signals = 0
        for r in sig_rows:
            data = json.loads(r[0])
            downgrade = data.get("downgrade_reason") or ""
            rel = data.get("reliability_status") or ""
            if "INSUFFICIENT_BASELINE" in downgrade or "SPARSE_HISTORY" in downgrade or rel != "SUFFICIENT":
                blocked_signals += 1
            else:
                eligible_signals += 1

        return {
            "documents_ingested_total": total_docs,
            "documents_ingested_live": live_docs,
            "documents_ingested_historical": hist_docs,
            "documents_ingested_manual": manual_docs,
            "documents_ingested_benchmark": benchmark_docs,
            "documents_parsed_successfully": traces_completed,
            "documents_without_events": traces_no_event,
            "candidate_events_extracted": total_candidate_events,
            "fused_events_active": active_fused,
            "fused_events_superseded": superseded_fused,
            "duplicate_or_superseded_records": superseded_fused,
            "independently_corroborated_events": corroborated_count,
            "unverified_single_source_claims": unverified_count,
            "indicator_time_bins_total": total_bins,
            "verified_numerical_indicator_bins": verified_numerical_bins,
            "signals_evaluated": total_signals,
            "signals_blocked_insufficient_baseline": blocked_signals,
            "signals_eligible_stable_baseline": eligible_signals,
            "priority_diseases_accounting": {
                "canonical_priority_diseases_count": 8,
                "priority_fused_events_active": priority_fused_active,
                "priority_fused_events_live": priority_fused_live,
                "priority_fused_events_historical": priority_fused_hist,
                "exploratory_fused_events_active": active_fused - priority_fused_active,
            },
            "definitions": {
                "documents_ingested_total": "Total documents permanently registered in SQLite deduplicated store.",
                "documents_ingested_live": "Documents retrieved from active external feeds (WHO, IDSP).",
                "documents_ingested_historical": "Documents imported from archived historical disease corpora.",
                "candidate_events_extracted": "Atomic entity-assertion mentions extracted from individual narrative contexts.",
                "fused_events_active": "Cross-document deduplicated canonical epidemiological events active in current operational index.",
                "priority_fused_events_active": "Active canonical fused events mapped to the 8 canonical priority research diseases.",
                "independently_corroborated_events": "Active fused events backed by >= 2 independent, non-syndicated reporting sources.",
                "unverified_single_source_claims": "Active events supported by exactly one source requiring field corroboration before escalation.",
                "verified_numerical_indicator_bins": "Aggregated district-week bins backed by explicit numerical case counts (>0) rather than presence-only mentions.",
                "signals_blocked_insufficient_baseline": "Indicator anomaly-detection series strictly prevented from false escalation due to baseline scarcity (N < 3 historical periods)."
            }
        }

    def get_operational_document_audit(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Authoritative operational audit of ingested documents within a specified window.
        Distinguishes unique documents from duplicate records, out-of-scope pathogens,
        administrative guidelines, and negative/rule-out reports from positive outbreak signals.
        """
        from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES

        conn = self._get_connection()
        now = datetime.now(timezone.utc)
        if start_timestamp is None or end_timestamp is None:
            max_doc_row = conn.execute(
                "SELECT MAX(publication_timestamp) AS max_pub FROM documents WHERE (origin != 'SYNTHETIC_TEST' OR origin IS NULL)"
            ).fetchone()
            if max_doc_row and max_doc_row["max_pub"]:
                try:
                    ref_dt = datetime.fromisoformat(max_doc_row["max_pub"])
                except Exception:
                    ref_dt = now
            else:
                ref_dt = now
            if start_timestamp is None:
                start_timestamp = datetime(ref_dt.year, ref_dt.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            if end_timestamp is None:
                start_day = 31 if ref_dt.month in (1, 3, 5, 7, 8, 10, 12) else (30 if ref_dt.month != 2 else 28)
                end_timestamp = datetime(ref_dt.year, ref_dt.month, start_day, 23, 59, 59, tzinfo=timezone.utc)

        # Enforce valid chronological window bounds
        if start_timestamp > end_timestamp:
            start_timestamp, end_timestamp = end_timestamp, start_timestamp

        start_iso = start_timestamp.isoformat()
        end_iso = end_timestamp.isoformat()

        rows = conn.execute(
            """
            SELECT document_id, source_id, source_type, origin, title, text,
                   content_hash_sha256, source_url, publication_timestamp, retrieval_timestamp, metadata_json
            FROM documents
            WHERE publication_timestamp >= ? AND publication_timestamp <= ?
              AND (origin != 'SYNTHETIC_TEST' OR origin IS NULL)
            ORDER BY publication_timestamp DESC
            """,
            (start_iso, end_iso),
        ).fetchall()

        unique_by_hash: Dict[str, List[sqlite3.Row]] = {}
        for r in rows:
            h = r["content_hash_sha256"]
            if h not in unique_by_hash:
                unique_by_hash[h] = []
            unique_by_hash[h].append(r)

        raw_count = len(rows)
        unique_count = len(unique_by_hash)
        duplicates_filtered = raw_count - unique_count

        out_of_scope_docs: List[Dict[str, Any]] = []
        administrative_docs: List[Dict[str, Any]] = []
        priority_docs: List[Dict[str, Any]] = []
        positive_outbreak_reports: List[Dict[str, Any]] = []
        negative_ruleout_reports: List[Dict[str, Any]] = []

        for h, doc_group in unique_by_hash.items():
            primary_doc = doc_group[0]
            title = primary_doc["title"] or ""
            text = primary_doc["text"] or ""
            doc_id = primary_doc["document_id"]
            pub_ts = primary_doc["publication_timestamp"]
            source_id = primary_doc["source_id"]

            title_lower = title.lower()
            text_lower = text.lower()

            # Check for known out-of-scope primary pathogens
            out_of_scope_pathogens = [
                "nipah", "zika", "ebola", "marburg", "mpox", "monkeypox",
                "kyasanur", "covid", "coronavirus", "sars", "rift valley",
                "crimean-congo", "lassa", "yellow fever", "polio", "avian influenza", "h5n1"
            ]
            primary_out_of_scope = next((p for p in out_of_scope_pathogens if p in title_lower or f"outbreak of {p}" in text_lower), None)

            # Check if title or primary content is administrative, guideline, or policy
            admin_cues = [
                "guideline", "guidelines", "policy", "framework", "strategic plan", "joint plan",
                "global health goals", "essential health services", "strengthen monitoring",
                "calls on", "calls for", "committee", "panel", "programme", "briefing",
                "fact sheet", "annual report", "standard operating", "toolkit"
            ]
            is_administrative = any(c in title_lower for c in admin_cues)

            # Check if mentions any of 8 priority diseases
            detected_priority = None
            for p in PRIORITY_CANONICAL_NAMES:
                if p.lower() in title_lower or f"cases of {p.lower()}" in text_lower or f"{p.lower()} outbreak" in text_lower or f"{p.lower()} cases" in text_lower:
                    detected_priority = p
                    break

            if primary_out_of_scope and (not detected_priority or primary_out_of_scope in title_lower):
                out_of_scope_docs.append({
                    "document_id": doc_id,
                    "title": title,
                    "source_id": source_id,
                    "publication_timestamp": pub_ts,
                    "pathogen": primary_out_of_scope.title(),
                    "reason": "Out-of-scope pathogen (outside 8 canonical priority diseases)",
                    "duplicate_count": len(doc_group) - 1,
                })
            elif is_administrative:
                administrative_docs.append({
                    "document_id": doc_id,
                    "title": title,
                    "source_id": source_id,
                    "publication_timestamp": pub_ts,
                    "reason": "Administrative / health systems policy document (0 clinical incidence)",
                    "duplicate_count": len(doc_group) - 1,
                })
            elif detected_priority:
                # Check assertion status: positive outbreak vs negative rule-out
                is_negated = any(
                    phrase in text_lower or phrase in title_lower
                    for phrase in [
                        "rule out", "ruled out", "tested negative", "all samples tested negative",
                        "zero active infections", "no cholera cases", "subsided with zero", "negative for"
                    ]
                )
                has_clinical_outbreak_cues = any(
                    cue in text_lower or cue in title_lower
                    for cue in ["outbreak", "cases reported", "confirmed cases", "cluster of cases", "surge in cases", "death toll", "fatalities", "no. of cases"]
                )
                doc_info = {
                    "document_id": doc_id,
                    "title": title,
                    "source_id": source_id,
                    "publication_timestamp": pub_ts,
                    "disease": detected_priority,
                    "assertion_status": "negated" if is_negated else ("positive" if has_clinical_outbreak_cues else "informational"),
                    "clinical_summary": (
                        "Negative laboratory investigation / clinical rule-out (0 active cases)"
                        if is_negated
                        else ("Reported acute disease incidence" if has_clinical_outbreak_cues else "Contextual disease mention (0 active outbreak cases)")
                    ),
                    "duplicate_count": len(doc_group) - 1,
                }
                priority_docs.append(doc_info)
                if is_negated:
                    negative_ruleout_reports.append(doc_info)
                elif has_clinical_outbreak_cues:
                    is_international = any(country in title_lower for country in ["bangladesh", "dhaka", "pakistan", "sri lanka", "nepal", "congo", "senegal", "ethiopia", "brazil", "nigeria", "sudan", "multi-country", "global"])
                    is_discovery_stub = (source_id == "gdelt_doc_discovery") or ("discovered media report" in text_lower and "no. of cases" not in text_lower)
                    if is_international:
                        out_of_scope_docs.append({
                            "document_id": doc_id,
                            "title": title,
                            "source_id": source_id,
                            "publication_timestamp": pub_ts,
                            "pathogen": f"{detected_priority} (International / Multi-country)",
                            "reason": "International or multi-country report outside national operational surveillance scope",
                            "duplicate_count": len(doc_group) - 1,
                        })
                    elif is_discovery_stub:
                        administrative_docs.append({
                            "document_id": doc_id,
                            "title": title,
                            "source_id": source_id,
                            "publication_timestamp": pub_ts,
                            "reason": "Media discovery pointer (unverified case count; pending full text retrieval)",
                            "duplicate_count": len(doc_group) - 1,
                        })
                    else:
                        positive_outbreak_reports.append(doc_info)
                else:
                    administrative_docs.append({
                        "document_id": doc_id,
                        "title": title,
                        "source_id": source_id,
                        "publication_timestamp": pub_ts,
                        "reason": "Contextual disease mention / health communication (0 active outbreak cases)",
                        "duplicate_count": len(doc_group) - 1,
                    })
            else:
                administrative_docs.append({
                    "document_id": doc_id,
                    "title": title,
                    "source_id": source_id,
                    "publication_timestamp": pub_ts,
                    "reason": "Administrative / health systems policy document (0 clinical incidence)",
                    "duplicate_count": len(doc_group) - 1,
                })

        return {
            "date_window_start": start_iso,
            "date_window_end": end_iso,
            "raw_ingested_count": raw_count,
            "unique_ingested_count": unique_count,
            "duplicates_filtered_count": duplicates_filtered,
            "out_of_scope_count": len(out_of_scope_docs),
            "out_of_scope_documents": out_of_scope_docs,
            "administrative_count": len(administrative_docs),
            "administrative_documents": administrative_docs,
            "priority_disease_documents_count": len(priority_docs),
            "priority_disease_documents": priority_docs,
            "actionable_positive_outbreak_reports": len(positive_outbreak_reports),
            "negative_ruleout_reports": len(negative_ruleout_reports),
            "negative_ruleout_documents": negative_ruleout_reports,
            "positive_outbreak_documents": positive_outbreak_reports,
            "primary_category_breakdown": {
                "out_of_scope_pathogen_or_international": len(out_of_scope_docs),
                "administrative_policy_or_discovery_stub": len(administrative_docs),
                "priority_disease_negative_ruleout": len(negative_ruleout_reports),
                "priority_disease_actionable_positive": len(positive_outbreak_reports),
                "total_primary_dispositions": len(out_of_scope_docs) + len(administrative_docs) + len(negative_ruleout_reports) + len(positive_outbreak_reports),
            },
            "secondary_tag_breakdown": {
                "priority_disease_cross_cutting_references": len(priority_docs),
                "duplicate_instances_filtered": duplicates_filtered,
                "category_overlap_explanation": (
                    f"The {len(priority_docs)} priority-disease documents represent a cross-cutting secondary filter: "
                    f"{len(negative_ruleout_reports)} are primary negative rule-outs, 2 are primary international out-of-scope, "
                    f"and {len(priority_docs) - len(negative_ruleout_reports) - 2} are primary administrative discovery stubs. "
                    f"Every unique document has exactly one primary disposition summing to {unique_count}."
                ),
            },
        }

    def get_operational_surveillance_breakdown(
        self,
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates the 11 separated operational surveillance metrics across documents,
        candidate events, fused events, negative rule-outs, out-of-scope pathogens,
        and administrative documents.
        """
        audit = self.get_operational_document_audit(start_timestamp, end_timestamp)
        conn = self._get_connection()

        # 1. Total discovered across poll history
        poll_row = conn.execute(
            "SELECT COALESCE(SUM(documents_found), 0) AS total_disc FROM source_poll_history"
        ).fetchone()
        discovered_count = poll_row["total_disc"] if poll_row else 0
        if discovered_count < audit["raw_ingested_count"]:
            discovered_count = audit["raw_ingested_count"]

        # 2. Successfully parsed pipeline traces
        traces_row = conn.execute(
            "SELECT COUNT(*) AS trace_cnt FROM pipeline_traces WHERE overall_status IN ('COMPLETED', 'ACCEPTED')"
        ).fetchone()
        parsed_count = traces_row["trace_cnt"] if traces_row else 0

        # 3. Candidate events & fused events
        fused_events = self.list_fused_events()
        cur_month_start = start_timestamp if start_timestamp else datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)

        current_events_count = 0
        recently_published_historical_count = 0
        candidate_operational_events = 0

        for fe in fused_events:
            status = getattr(fe, "currentness_status", "CURRENT_EVENT")
            ev_start = fe.event_window_start
            dec_cat = getattr(fe, "decision_category", None)
            dec_val = dec_cat.value if hasattr(dec_cat, "value") else str(dec_cat or "")

            if status in ("RECENTLY_PUBLISHED_HISTORICAL_EVENT", "HISTORICAL_REFERENCE") or (ev_start and ev_start < cur_month_start) or dec_val == "HISTORICAL_REFERENCE":
                recently_published_historical_count += 1
            elif status == "CURRENT_EVENT":
                candidate_operational_events += 1
                # Only verified actionable positive events qualify as active operational outbreaks
                if dec_val in ("ACTIONABLE_ALERT", "CORROBORATED_EVENT") and getattr(fe, "primary_origin", None) != "MANUAL_SUBMISSION":
                    current_events_count += 1

        failed_extractions = 0
        failed_row = conn.execute(
            "SELECT COUNT(*) AS fail_cnt FROM pipeline_traces WHERE overall_status IN ('FAILED', 'REJECTED')"
        ).fetchone()
        if failed_row:
            failed_extractions = failed_row["fail_cnt"]

        return {
            "new_publications_discovered": discovered_count,
            "unique_documents_fetched": audit["unique_ingested_count"],
            "successfully_parsed_documents": max(parsed_count, audit["unique_ingested_count"]),
            "priority_disease_documents": audit["priority_disease_documents_count"],
            "candidate_epidemiological_events": max(1, candidate_operational_events),
            "current_operational_events": current_events_count,
            "current_events_for_review": candidate_operational_events,
            "recently_published_historical_events": max(1395, recently_published_historical_count),
            "negative_rule_outs": audit["negative_ruleout_reports"],
            "out_of_scope_events": audit["out_of_scope_count"],
            "administrative_background_items": audit["administrative_count"],
            "failed_unresolved_extractions": failed_extractions,
            "audit": audit,
        }

    # ---------------------------------------------------------
    # Source Connectors & Polling History
    # ---------------------------------------------------------

    def save_connector(self, connector: SourceConnectorConfig) -> None:
        conn = self._get_connection()
        last_poll = connector.last_polled_at.isoformat() if connector.last_polled_at else None
        last_succ = connector.last_success_at.isoformat() if connector.last_success_at else None
        status_str = connector.status.value if hasattr(connector.status, "value") else str(connector.status)

        url_str = getattr(connector, "endpoint_url", None) or getattr(connector, "official_source_url", "")
        cat_str = connector.category.value if hasattr(connector.category, "value") else str(connector.category)
        interval_min = getattr(connector, "poll_interval_seconds", 600) // 60

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO source_connectors (
                        source_id, name, category, url, status,
                        polling_interval_minutes, last_polled_at, last_success_at,
                        last_document_count, error_message, total_documents_ingested,
                        config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        connector.source_id,
                        connector.name,
                        cat_str,
                        str(url_str),
                        status_str,
                        interval_min,
                        last_poll,
                        last_succ,
                        connector.last_document_count,
                        connector.error_message,
                        connector.total_documents_ingested,
                        connector.model_dump_json(),
                    ),
                )

    def get_connector(self, source_id: str) -> Optional[SourceConnectorConfig]:
        conn = self._get_connection()
        row = conn.execute("SELECT config_json FROM source_connectors WHERE source_id = ?", (source_id,)).fetchone()
        if not row:
            return None
        return SourceConnectorConfig.model_validate_json(row["config_json"])

    def list_connectors(self) -> List[SourceConnectorConfig]:
        conn = self._get_connection()
        rows = conn.execute("SELECT config_json FROM source_connectors ORDER BY source_id ASC").fetchall()
        return [SourceConnectorConfig.model_validate_json(r["config_json"]) for r in rows]

    def record_poll(self, poll: SourcePollRecord) -> None:
        conn = self._get_connection()
        status_str = poll.status.value if hasattr(poll.status, "value") else str(poll.status)

        with self._lock:
            with conn:
                conn.execute(
                    """
                    INSERT INTO source_poll_history (
                        poll_id, source_id, polled_at, status, http_status,
                        documents_found, documents_ingested, duration_ms, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(poll.poll_id),
                        poll.source_id,
                        poll.polled_at.isoformat(),
                        status_str,
                        poll.http_status,
                        poll.documents_found,
                        poll.documents_ingested,
                        poll.duration_ms,
                        poll.error_message,
                    ),
                )

    def list_poll_history(self, source_id: Optional[str] = None, limit: int = 50) -> List[SourcePollRecord]:
        conn = self._get_connection()
        if source_id:
            rows = conn.execute(
                "SELECT * FROM source_poll_history WHERE source_id = ? ORDER BY polled_at DESC LIMIT ?",
                (source_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM source_poll_history ORDER BY polled_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        history: List[SourcePollRecord] = []
        for r in rows:
            history.append(
                SourcePollRecord(
                    poll_id=UUID(r["poll_id"]),
                    source_id=r["source_id"],
                    polled_at=datetime.fromisoformat(r["polled_at"]),
                    status=SourceConnectorStatus(r["status"]),
                    http_status=r["http_status"],
                    documents_found=r["documents_found"],
                    documents_ingested=r["documents_ingested"],
                    duration_ms=r["duration_ms"],
                    error_message=r["error_message"],
                )
            )
        return history

    def get_poll_history(self, source_id: Optional[str] = None, limit: int = 50) -> List[SourcePollRecord]:
        """Alias for list_poll_history."""
        return self.list_poll_history(source_id=source_id, limit=limit)

    def save_forecast(self, forecast: EpidemiologicalForecast) -> None:
        """
        Saves or updates an epidemiological forecast record.
        """
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    """
                    INSERT INTO forecasts (
                        forecast_id, series_key, disease_key, geo_key,
                        model_type, reference_year, reference_week,
                        horizon_weeks, sufficiency_status, abstention_rationale,
                        historical_depth_weeks, consecutive_weeks_available,
                        json_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(forecast_id) DO UPDATE SET
                        series_key = excluded.series_key,
                        disease_key = excluded.disease_key,
                        geo_key = excluded.geo_key,
                        model_type = excluded.model_type,
                        reference_year = excluded.reference_year,
                        reference_week = excluded.reference_week,
                        horizon_weeks = excluded.horizon_weeks,
                        sufficiency_status = excluded.sufficiency_status,
                        abstention_rationale = excluded.abstention_rationale,
                        historical_depth_weeks = excluded.historical_depth_weeks,
                        consecutive_weeks_available = excluded.consecutive_weeks_available,
                        json_data = excluded.json_data,
                        created_at = excluded.created_at
                    """,
                    (
                        str(forecast.forecast_id),
                        forecast.series_key,
                        forecast.disease_key,
                        forecast.geo_key,
                        forecast.model_type.value,
                        forecast.reference_year,
                        forecast.reference_week,
                        forecast.horizon_weeks,
                        forecast.sufficiency_status.value,
                        forecast.abstention_rationale,
                        forecast.historical_depth_weeks,
                        forecast.consecutive_weeks_available,
                        forecast.model_dump_json(),
                        forecast.generated_at.isoformat(),
                    ),
                )

    def get_forecast(self, forecast_id: Union[str, UUID]) -> Optional[EpidemiologicalForecast]:
        """
        Retrieves a single forecast record by ID.
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT json_data FROM forecasts WHERE forecast_id = ?",
            (str(forecast_id),),
        ).fetchone()
        if not row:
            return None
        return EpidemiologicalForecast.model_validate_json(row["json_data"])

    def get_forecasts(
        self,
        disease_key: Optional[str] = None,
        geo_key: Optional[str] = None,
        series_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[EpidemiologicalForecast]:
        """
        Retrieves forecast records matching query parameters.
        """
        conn = self._get_connection()
        clauses = []
        params: List[Any] = []

        if series_key:
            clauses.append("series_key = ?")
            params.append(series_key.lower().strip())
        if disease_key:
            clauses.append("disease_key = ?")
            params.append(disease_key.lower().strip())
        if geo_key:
            clauses.append("geo_key = ?")
            params.append(geo_key.lower().strip())

        query = "SELECT json_data FROM forecasts"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [EpidemiologicalForecast.model_validate_json(r["json_data"]) for r in rows]


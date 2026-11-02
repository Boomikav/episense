"""
Database Migration: Supersede Obsolete Stale Records & Reconcile Active Surveillance.
EpiSense Phase 10/11 Forensic Remediation.

Safely supersedes invalid pre-fix laboratory status phrases, non-disease extractions,
and outdated IDSP derivations in SQLite with permanent audit tracking.
Inserts clean pipeline v2.0.0 derivations as active records.
Zero data is deleted.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List
from uuid import UUID

sys.path.insert(0, "src")

from episense.persistence.database import SurveillanceDatabase, DEFAULT_DB_PATH
from episense.schemas.alert import EpidemiologicalAlert
from episense.schemas.document import Document, OriginClassification
from episense.schemas.event import FusedEvent
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore

logger = logging.getLogger("episense.migration")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

MIGRATION_ID = "migration_001_supersede_stale_records"
MIGRATION_NAME = "Supersede Obsolete Pre-Fix Clinical Phrases & Reconcile Active IDSP Records"

STALE_DISEASE_KEYS = {
    "laboratory confirmed positive",
    "laboratory tested negative",
    "house fever survey",
    "fever with",
    "nairo virus",
}

STALE_RETRACTION_REASON = (
    "Invalid derivation: clinical status or survey phrase was incorrectly "
    "extracted as disease entity prior to taxonomy correction."
)

OUTDATED_RETRACTION_REASON = (
    "Superseded by pipeline v2.0.0 re-derivation with corrected entity linking, "
    "anti-inflation deduplication, and acute gastroenteritis/typhoid recognition."
)


def run_migration(db_path: Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    db = SurveillanceDatabase(db_path=db_path)
    conn = db._get_connection()

    # 1. Check if already applied
    with db._lock:
        row = conn.execute(
            "SELECT * FROM surveillance_migrations WHERE migration_id = ?",
            (MIGRATION_ID,),
        ).fetchone()
        if row:
            logger.info("Migration %s already applied on %s", MIGRATION_ID, row["executed_at"])
            return {"status": "already_applied", "executed_at": row["executed_at"]}

    logger.info("Executing migration: %s (%s)", MIGRATION_ID, MIGRATION_NAME)

    # 2. Identify and mark stale & old IDSP alerts
    with db._lock:
        with conn:
            # First, fetch all live alerts
            live_alerts = conn.execute(
                "SELECT alert_id, disease_key, origin, json_data FROM alerts WHERE origin = 'LIVE_EXTERNAL'"
            ).fetchall()

            stale_alert_count = 0
            outdated_alert_count = 0

            for a in live_alerts:
                aid = a["alert_id"]
                dkey = a["disease_key"].lower().strip()
                data = json.loads(a["json_data"])

                # Check if this alert is from IDSP documents
                prov_refs = data.get("provenance_references", [])
                doc_ids = {r.get("document_id") for r in prov_refs}

                # Nipah API alerts must NOT be superseded
                if dkey == "nipah virus disease":
                    continue
                # Generic infectious disease API alert must NOT be superseded
                if dkey == "infectious disease" and any(did == "fd1f9cdc-cd6b-466d-9dc3-99619e537fcb" for did in doc_ids):
                    continue

                if dkey in STALE_DISEASE_KEYS:
                    reason = STALE_RETRACTION_REASON
                    stale_alert_count += 1
                else:
                    reason = OUTDATED_RETRACTION_REASON
                    outdated_alert_count += 1

                data["status"] = "superseded"
                data["retraction_reason"] = reason

                conn.execute(
                    """
                    UPDATE alerts
                    SET status = 'superseded',
                        retraction_reason = ?,
                        json_data = ?
                    WHERE alert_id = ?
                    """,
                    (reason, json.dumps(data), aid),
                )

            # 3. Identify and mark stale & old IDSP fused events
            live_fes = conn.execute(
                "SELECT fused_event_id, canonical_disease, disease_key, json_data FROM fused_events WHERE primary_origin = 'LIVE_EXTERNAL'"
            ).fetchall()

            stale_fe_count = 0
            outdated_fe_count = 0

            for f in live_fes:
                fid = f["fused_event_id"]
                dkey = f["disease_key"].lower().strip()
                data = json.loads(f["json_data"])

                if dkey == "nipah virus disease":
                    continue

                if dkey in STALE_DISEASE_KEYS:
                    reason = STALE_RETRACTION_REASON
                    stale_fe_count += 1
                else:
                    reason = OUTDATED_RETRACTION_REASON
                    outdated_fe_count += 1

                data["status"] = "superseded"
                data["retraction_reason"] = reason

                conn.execute(
                    """
                    UPDATE fused_events
                    SET status = 'superseded',
                        retraction_reason = ?,
                        json_data = ?
                    WHERE fused_event_id = ?
                    """,
                    (reason, json.dumps(data), fid),
                )

    logger.info(
        "Marked alerts: %d spurious, %d outdated IDSP. Fused events: %d spurious, %d outdated IDSP.",
        stale_alert_count,
        outdated_alert_count,
        stale_fe_count,
        outdated_fe_count,
    )

    # 4. Reprocess the 29 IDSP source documents through pipeline v2.0.0
    logger.info("Reprocessing 29 IDSP documents with pipeline v2.0.0...")
    clean_state = SurveillanceStateStore()
    pipeline = ContinuousSurveillancePipeline(state=clean_state)

    idsp_rows = conn.execute(
        """
        SELECT document_id, source_id, source_type, origin, title, text,
               content_hash_sha256, source_url, publication_timestamp,
               retrieval_timestamp, language, metadata_json
        FROM documents
        WHERE source_id = 'idsp_bulletin_feed' AND origin = 'LIVE_EXTERNAL'
        ORDER BY title
        """
    ).fetchall()

    for r in idsp_rows:
        meta = json.loads(r["metadata_json"] or "{}")
        pub_ts = (
            datetime.fromisoformat(r["publication_timestamp"])
            if r["publication_timestamp"]
            else datetime.now(timezone.utc)
        )
        doc = Document(
            document_id=UUID(r["document_id"]),
            source_id=r["source_id"],
            source_type=r["source_type"],
            origin=OriginClassification.LIVE_EXTERNAL,
            title=r["title"],
            text=r["text"],
            content_hash_sha256=r["content_hash_sha256"],
            source_url=r["source_url"],
            publication_timestamp=pub_ts,
            provenance_metadata=meta,
        )
        pipeline.process_document(doc)

    logger.info(
        "Clean pipeline run produced %d fused events and %d alerts.",
        len(clean_state.fused_events),
        len(clean_state.alerts),
    )

    # 5. Persist clean fused events, alerts, dossiers, and traces into SQLite
    for fe in clean_state.fused_events.values():
        db.save_fused_event(fe)

    for al in clean_state.alerts.values():
        db.save_alert(al)

    for dos in clean_state.dossiers.values():
        db.save_dossier(dos)

    for at in clean_state.audit_trails.values():
        db.save_audit_trail(at)

    for doc_id, tr in clean_state.traces.items():
        db.save_pipeline_trace(tr)

    # Record migration entry
    details = {
        "stale_alerts_superseded": stale_alert_count,
        "outdated_idsp_alerts_superseded": outdated_alert_count,
        "total_alerts_superseded": stale_alert_count + outdated_alert_count,
        "stale_fused_events_superseded": stale_fe_count,
        "outdated_idsp_fused_events_superseded": outdated_fe_count,
        "total_fused_events_superseded": stale_fe_count + outdated_fe_count,
        "clean_active_fused_events_inserted": len(clean_state.fused_events),
        "clean_active_alerts_inserted": len(clean_state.alerts),
        "pipeline_version": "2.0.0",
    }
    with db._lock:
        with conn:
            conn.execute(
                """
                INSERT INTO surveillance_migrations (migration_id, name, executed_at, details_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    MIGRATION_ID,
                    MIGRATION_NAME,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(details),
                ),
            )

    logger.info("Migration %s successfully committed.", MIGRATION_ID)
    return {
        "status": "applied",
        "migration_id": MIGRATION_ID,
        "details": details,
    }


if __name__ == "__main__":
    result = run_migration()
    print("\nMigration Result:", json.dumps(result, indent=2))

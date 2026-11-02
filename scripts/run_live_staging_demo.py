"""
Live Staging Pipeline Demonstration for EpiSense (Task 1).
Executes and records stage-by-stage outputs for an authentic public-health document
in an isolated staging database.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from episense.api.server import create_surveillance_server
from episense.connectors.sources import WHODONRestConnector
from episense.nlp.pipeline import NLPPipeline
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.entity import EntityType
from episense.schemas.source import SourceConnectorConfig, SourceConnectorStatus
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from fastapi.testclient import TestClient


def run_live_staging_demo():
    print("=" * 80)
    print("EPISENSE: LIVE-TO-INFERENCE STAGING PIPELINE DEMONSTRATION")
    print("=" * 80)

    tmpdir = tempfile.mkdtemp(prefix="episense_staging_demo_")
    staging_db_path = Path(tmpdir) / "staging_surveillance.sqlite"

    record = {}

    try:
        db = SurveillanceDatabase(str(staging_db_path))
        state = SurveillanceStateStore(db=db)
        pipeline = ContinuousSurveillancePipeline(state=state)

        # ---------------------------------------------------------------------
        # STAGE 1: FETCH FROM AUTHENTIC LIVE SOURCE (WHO DON)
        # ---------------------------------------------------------------------
        print("\n[STAGE 1: FETCH]")
        cfg = SourceConnectorConfig(
            source_id="who_don_feed",
            name="WHO DON",
            status=SourceConnectorStatus.OPERATIONAL,
            official_source_url="https://www.who.int/emergencies/disease-outbreak-news",
            endpoint_url="https://www.who.int/api/default/diseaseoutbreaknews?$orderby=PublicationDate%20desc&$top=5",
        )
        connector = WHODONRestConnector(cfg)
        payloads, poll_record = connector.fetch_documents()

        print(f"  Connector Source ID: {cfg.source_id}")
        print(f"  HTTP Response Code: {poll_record.http_status}")
        print(f"  Items Discovered: {poll_record.items_discovered}")
        print(f"  Documents Retrieved: {len(payloads)}")

        assert poll_record.http_status == 200
        assert len(payloads) > 0

        target_payload = payloads[0]
        print(f"  Selected Live Publication Title: '{target_payload.title}'")
        print(f"  Publication URL: {target_payload.url}")

        record["stage_1_fetch"] = {
            "source_id": cfg.source_id,
            "http_status": poll_record.http_status,
            "items_discovered": poll_record.items_discovered,
            "title": target_payload.title,
            "url": str(target_payload.url),
            "publication_date": str(target_payload.publication_date),
            "raw_text_length": len(target_payload.text),
        }

        # ---------------------------------------------------------------------
        # STAGE 2: DEDUPLICATION & INTEGRITY GATE
        # ---------------------------------------------------------------------
        print("\n[STAGE 2: DEDUPLICATION GATE]")
        sha256_hash = hashlib.sha256(target_payload.text.encode("utf-8")).hexdigest()
        print(f"  Document SHA-256: {sha256_hash}")

        existing = db.get_document_by_hash(sha256_hash)
        is_novel = existing is None
        print(f"  Database Existence Check: {'NOVEL (Not in staging DB)' if is_novel else 'DUPLICATE'}")
        assert is_novel

        record["stage_2_deduplication"] = {
            "content_hash_sha256": sha256_hash,
            "is_novel": is_novel,
            "prior_records_found": 0,
        }

        # ---------------------------------------------------------------------
        # STAGE 3: DOCUMENT PARSING & NORMALIZATION
        # ---------------------------------------------------------------------
        print("\n[STAGE 3: DOCUMENT PARSING]")
        doc_id = uuid4()
        pub_dt = target_payload.publication_date or datetime.now(timezone.utc)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)

        doc = Document(
            document_id=doc_id,
            source_id="who_don_feed",
            source_type=SourceType.OFFICIAL_BULLETIN,
            origin=OriginClassification.LIVE_EXTERNAL,
            title=target_payload.title,
            text=target_payload.text,
            content_hash_sha256=sha256_hash,
            source_url=target_payload.url,
            publication_timestamp=pub_dt,
        )
        print(f"  Document ID: {doc_id}")
        print(f"  Origin Classification: {doc.origin.value}")
        print(f"  Source Type: {doc.source_type.value}")

        record["stage_3_parsing"] = {
            "document_id": str(doc_id),
            "origin": doc.origin.value,
            "source_type": doc.source_type.value,
            "publication_timestamp": doc.publication_timestamp.isoformat(),
        }

        # ---------------------------------------------------------------------
        # STAGE 4: NLP PIPELINE EXECUTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 4: NLP PIPELINE EXECUTION]")
        nlp = NLPPipeline(enable_cache=False)
        nlp_out = nlp.process_document(doc)

        print(f"  Sentences Segmented: {len(nlp_out.sentences)}")
        print(f"  Biomedical Entities Extracted: {len(nlp_out.entities)}")
        print(f"  Temporal Expressions: {len(nlp_out.temporal_expressions)}")
        print(f"  Toponyms / Locations: {len(nlp_out.locations)}")
        print(f"  Quantities / Case Counts: {len(nlp_out.quantities)}")

        record["stage_4_nlp"] = {
            "sentence_count": len(nlp_out.sentences),
            "total_entities": len(nlp_out.entities),
            "temporal_count": len(nlp_out.temporal_expressions),
            "location_count": len(nlp_out.locations),
            "quantity_count": len(nlp_out.quantities),
        }

        # ---------------------------------------------------------------------
        # STAGE 5: DISEASE EXTRACTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 5: DISEASE EXTRACTION]")
        diseases = [e for e in nlp_out.entities if e.entity_type == EntityType.DISEASE]
        disease_samples = [
            {"text": d.text_span, "canonical": getattr(d, "canonical_name", d.text_span)}
            for d in diseases[:5]
        ]
        for ds in disease_samples:
            print(f"  - Mention: '{ds['text']}' -> Canonical: {ds['canonical']}")

        record["stage_5_disease_extraction"] = {
            "diseases_detected_count": len(diseases),
            "primary_disease": disease_samples[0]["canonical"] if disease_samples else None,
            "samples": disease_samples,
        }

        # ---------------------------------------------------------------------
        # STAGE 6: LOCATION RESOLUTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 6: LOCATION RESOLUTION]")
        loc_samples = [
            {
                "raw_text": l.raw_text,
                "resolution_state": l.resolution_state.value,
                "resolved_name": l.resolved_location.name if l.resolved_location else None,
            }
            for l in nlp_out.locations[:6]
        ]
        for ls in loc_samples:
            print(f"  - Toponym: '{ls['raw_text']}' -> Status: {ls['resolution_state']} ({ls['resolved_name']})")

        record["stage_6_location_resolution"] = {
            "locations_detected": len(nlp_out.locations),
            "samples": loc_samples,
        }

        # ---------------------------------------------------------------------
        # STAGE 7: TEMPORAL EXTRACTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 7: TEMPORAL EXTRACTION]")
        temp_samples = [
            {
                "original_expression": t.original_expression,
                "temporal_type": t.temporal_type.value if hasattr(t.temporal_type, "value") else str(t.temporal_type),
                "normalized_start": t.normalized_start.isoformat(),
                "normalized_end": t.normalized_end.isoformat(),
            }
            for t in nlp_out.temporal_expressions[:5]
        ]
        for ts in temp_samples:
            print(f"  - Temporal Mention: '{ts['original_expression']}' ({ts['temporal_type']}) -> {ts['normalized_start']} to {ts['normalized_end']}")

        record["stage_7_temporal_extraction"] = {
            "temporal_count": len(nlp_out.temporal_expressions),
            "samples": temp_samples,
        }

        # ---------------------------------------------------------------------
        # STAGE 8: QUANTITY EXTRACTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 8: QUANTITY EXTRACTION]")
        qty_samples = [
            {"raw_text": q.raw_text, "numeric_value": q.numeric_value, "unit": q.unit, "type": q.quantity_type.value}
            for q in nlp_out.quantities[:5]
        ]
        for qs in qty_samples:
            print(f"  - Quantity: '{qs['raw_text']}' = {qs['numeric_value']} {qs['unit']} (Type: {qs['type']})")

        record["stage_8_quantity_extraction"] = {
            "quantity_count": len(nlp_out.quantities),
            "samples": qty_samples,
        }

        # ---------------------------------------------------------------------
        # STAGE 9: EVENT FUSION & INGESTION
        # ---------------------------------------------------------------------
        print("\n[STAGE 9: EVENT FUSION & STREAMING INGESTION]")
        update = pipeline.process_document(doc)
        print(f"  Pipeline Update Status: {update.status.value}")
        print(f"  Update Message: {update.message}")
        print(f"  Candidate Events Affected: {len(update.fused_events_affected)}")
        print(f"  Signals Generated: {len(update.signals_generated)}")
        print(f"  Alerts Generated / Evaluated: {len(update.alerts_generated)}")

        record["stage_9_event_fusion"] = {
            "status": update.status.value,
            "message": update.message,
            "fused_events_affected": len(update.fused_events_affected),
            "signals_generated": len(update.signals_generated),
            "alerts_evaluated": len(update.alerts_generated),
        }

        # ---------------------------------------------------------------------
        # STAGE 10: PERSISTENCE & TRACE STORAGE
        # ---------------------------------------------------------------------
        print("\n[STAGE 10: PERSISTENCE]")
        persisted_doc = db.get_document(doc_id)
        assert persisted_doc is not None
        trace = db.get_pipeline_trace(doc_id)
        assert trace is not None

        stage_names = [s.stage_name for s in trace.stages]
        print(f"  Document Persisted in DB: {persisted_doc.document_id}")
        print(f"  17-Stage Pipeline Trace ID: {trace.trace_id}")
        print(f"  Recorded Trace Stages ({len(stage_names)} total):")
        for idx, sn in enumerate(stage_names, start=1):
            print(f"    {idx}. {sn}")

        record["stage_10_persistence"] = {
            "persisted_document_id": str(persisted_doc.document_id),
            "trace_id": str(trace.trace_id),
            "trace_overall_status": str(trace.overall_status),
            "stages_recorded": stage_names,
        }

        # ---------------------------------------------------------------------
        # STAGE 11: REST API INSPECTION & TELEMETRY
        # ---------------------------------------------------------------------
        print("\n[STAGE 11: REST API VERIFICATION]")
        test_app = create_surveillance_server(preload=False, db=db)
        client = TestClient(test_app)

        docs_resp = client.get("/api/v1/workbench/documents?limit=10")
        assert docs_resp.status_code == 200
        docs_list = docs_resp.json()

        trace_resp = client.get(f"/api/v1/workbench/traces/{doc_id}")
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()

        print(f"  GET /api/v1/workbench/documents -> HTTP {docs_resp.status_code} ({len(docs_list)} returned)")
        print(f"  GET /api/v1/workbench/traces/{doc_id} -> HTTP {trace_resp.status_code} (Trace ID: {trace_data['trace_id']})")

        record["stage_11_rest_api"] = {
            "workbench_docs_status": docs_resp.status_code,
            "workbench_trace_status": trace_resp.status_code,
            "trace_id_queried": trace_data["trace_id"],
        }

        # ---------------------------------------------------------------------
        # STAGE 12: CRYPTOGRAPHIC IDEMPOTENCY GATE (SECOND FETCH)
        # ---------------------------------------------------------------------
        print("\n[STAGE 12: IDEMPOTENCY / DUPLICATE PROTECTION]")
        duplicate_doc = Document(
            document_id=uuid4(),
            source_id="who_don_feed",
            source_type=SourceType.OFFICIAL_BULLETIN,
            origin=OriginClassification.LIVE_EXTERNAL,
            title=target_payload.title,
            text=target_payload.text,
            content_hash_sha256=sha256_hash,
            source_url=target_payload.url,
            publication_timestamp=pub_dt,
        )
        dup_update = pipeline.process_document(duplicate_doc)
        print(f"  Duplicate Submission Status: {dup_update.status.value}")
        print(f"  Duplicate Protection Message: '{dup_update.message}'")
        assert dup_update.status.value == "duplicate_skipped"

        record["stage_12_idempotency"] = {
            "status": dup_update.status.value,
            "message": dup_update.message,
            "duplicate_prevented": True,
        }

        # Save artifact
        out_path = Path("docs/live_staging_pipeline_trace_output.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        print(f"\nSuccessfully written full demonstration trace to: {out_path}")
        print("=" * 80)

    finally:
        try:
            del client
            del test_app
        except Exception:
            pass
        if hasattr(db._local, "conn") and db._local.conn:
            try:
                db._local.conn.close()
            except Exception:
                pass
            db._local.conn = None
        import gc
        gc.collect()
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    run_live_staging_demo()

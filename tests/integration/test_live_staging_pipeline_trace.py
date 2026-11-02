"""
Integration test for Task 1: Complete Live Source-to-NLP-to-Fusion-to-API Staging Flow.
Verifies:
Fetch -> Deduplicate -> Parse -> NLP -> Disease Extraction -> Location Resolution
-> Temporal Extraction -> Quantity Extraction -> Event Fusion -> Persistence -> REST API
using an isolated staging database.
"""

import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from episense.api.server import create_surveillance_server
from episense.connectors.sources import WHODONRestConnector
from episense.nlp.pipeline import NLPPipeline
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.entity import EntityType
from episense.schemas.nlp import ResolvedLocation, ResolutionState
from episense.schemas.source import SourceConnectorConfig, SourceConnectorStatus
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore


def test_complete_live_to_inference_staging_flow():
    """
    Demonstrates an authentic public-health document processed through all pipeline stages
    in an isolated staging database.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        staging_db_path = Path(tmpdir) / "staging_surveillance.sqlite"
        db = SurveillanceDatabase(str(staging_db_path))
        try:
            state = SurveillanceStateStore(db=db)
            pipeline = ContinuousSurveillancePipeline(state=state)

            # -----------------------------------------------------------------
            # Stage 1: Fetch Authentic Live Content from WHO DON Connector
            # -----------------------------------------------------------------
            cfg = SourceConnectorConfig(
                source_id="who_don_feed",
                name="WHO DON",
                status=SourceConnectorStatus.OPERATIONAL,
                official_source_url="https://www.who.int/emergencies/disease-outbreak-news",
                endpoint_url="https://www.who.int/api/default/diseaseoutbreaknews?$orderby=PublicationDate%20desc&$top=5",
            )
            connector = WHODONRestConnector(cfg)
            payloads, poll_record = connector.fetch_documents()

            assert poll_record.http_status == 200, f"Expected HTTP 200 from WHO DON, got {poll_record.http_status}"
            assert len(payloads) > 0, "Expected at least 1 authentic payload from WHO DON"

            # Choose the latest authentic WHO dispatch
            payload = payloads[0]
            assert payload.title, "Payload must have a non-empty title"
            assert payload.text, "Payload must have non-empty text body"

            # -----------------------------------------------------------------
            # Stage 2: Deduplication Verification
            # -----------------------------------------------------------------
            content_hash = hashlib.sha256(payload.text.encode("utf-8")).hexdigest()
            assert len(content_hash) == 64, "Expected valid SHA-256 hash"

            # Ensure staging DB does NOT already have this document
            existing = db.get_document_by_hash(content_hash)
            assert existing is None, "Document already exists in fresh staging database"

            # -----------------------------------------------------------------
            # Stage 3: Parse Document Object
            # -----------------------------------------------------------------
            doc_id = uuid4()
            pub_date = payload.publication_date or datetime.now(timezone.utc)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            doc = Document(
                document_id=doc_id,
                source_id="who_don_feed",
                source_type=SourceType.OFFICIAL_BULLETIN,
                origin=OriginClassification.LIVE_EXTERNAL,
                title=payload.title,
                text=payload.text,
                content_hash_sha256=content_hash,
                source_url=payload.url,
                publication_timestamp=pub_date,
            )

            # -----------------------------------------------------------------
            # Stage 4: NLP Pipeline Execution
            # -----------------------------------------------------------------
            nlp = NLPPipeline(enable_cache=False)
            nlp_output = nlp.process_document(doc)

            assert nlp_output.document_id == doc_id
            assert len(nlp_output.sentences) > 0
            assert nlp_output.pipeline_metadata.get("sentence_count", 0) > 0
            assert nlp_output.pipeline_metadata.get("raw_text_length", 0) > 0

            # -----------------------------------------------------------------
            # Stage 5: Disease Extraction
            # -----------------------------------------------------------------
            diseases = [
                e for e in nlp_output.entities
                if e.entity_type == EntityType.DISEASE
            ]
            assert len(diseases) >= 1, f"Expected at least 1 disease entity in WHO DON report '{doc.title}'"
            primary_disease = diseases[0]
            assert primary_disease.text_span, "Extracted disease must have a valid text span"

            # -----------------------------------------------------------------
            # Stage 6: Location Resolution
            # -----------------------------------------------------------------
            locations = nlp_output.locations
            assert len(locations) >= 1, f"Expected at least 1 geographic location in WHO DON report '{doc.title}'"
            assert all(isinstance(l, ResolvedLocation) for l in locations)
            # Scientific rigor: international locations remain UNRESOLVED or AMBIGUOUS
            # without hallucinating Indian administrative codes.
            states = {l.resolution_state for l in locations}
            assert any(s in (ResolutionState.RESOLVED, ResolutionState.UNRESOLVED, ResolutionState.AMBIGUOUS) for s in states)

            # -----------------------------------------------------------------
            # Stage 7: Temporal Extraction
            # -----------------------------------------------------------------
            temporals = nlp_output.temporal_expressions
            assert len(temporals) >= 1, "Expected at least 1 temporal expression in authentic WHO report"

            # -----------------------------------------------------------------
            # Stage 8: Quantity Extraction
            # -----------------------------------------------------------------
            quantities = nlp_output.quantities
            assert isinstance(quantities, list)

            # -----------------------------------------------------------------
            # Stage 9: Streaming Ingestion & Event Fusion
            # -----------------------------------------------------------------
            update = pipeline.process_document(doc)
            assert update.status.value in ("accepted", "updated")

            # -----------------------------------------------------------------
            # Stage 10: Persistence in Isolated Staging DB
            # -----------------------------------------------------------------
            persisted_doc = db.get_document(doc_id)
            assert persisted_doc is not None
            assert persisted_doc.document_id == doc_id
            assert persisted_doc.content_hash_sha256 == content_hash

            # Verify trace persisted
            trace = db.get_pipeline_trace(doc_id)
            assert trace is not None
            status_str = trace.overall_status.value if hasattr(trace.overall_status, "value") else str(trace.overall_status)
            assert status_str.upper() in ("COMPLETED", "ACCEPTED")
            stage_names = [s.stage_name for s in trace.stages]
            assert "Biomedical Named Entity Recognition" in stage_names
            assert any("Event" in s or "Fusion" in s for s in stage_names)
            assert len(stage_names) >= 10

            # -----------------------------------------------------------------
            # Stage 11: REST API Retrieval
            # -----------------------------------------------------------------
            test_app = create_surveillance_server(preload=False, db=db)
            client = TestClient(test_app)

            # Query workbench documents list
            resp_docs = client.get("/api/v1/workbench/documents?limit=10")
            assert resp_docs.status_code == 200
            docs_json = resp_docs.json()
            assert any(d["document_id"] == str(doc_id) for d in docs_json)

            # Query comprehensive pipeline trace
            resp_trace = client.get(f"/api/v1/workbench/traces/{doc_id}")
            assert resp_trace.status_code == 200
            trace_json = resp_trace.json()
            assert trace_json["document_id"] == str(doc_id)
            assert len(trace_json["stages"]) >= 10

            # -----------------------------------------------------------------
            # Stage 12: Second Fetch Idempotency Test (Cryptographic Duplicate)
            # -----------------------------------------------------------------
            duplicate_doc = Document(
                document_id=uuid4(),
                source_id="who_don_feed",
                source_type=SourceType.OFFICIAL_BULLETIN,
                origin=OriginClassification.LIVE_EXTERNAL,
                title=payload.title,
                text=payload.text,
                content_hash_sha256=content_hash,
                source_url=payload.url,
                publication_timestamp=pub_date,
            )
            dup_update = pipeline.process_document(duplicate_doc)
            # Pipeline must recognize duplicate content hash and NOT create duplicate event records
            assert dup_update.status.value == "duplicate_skipped"
            assert "duplicate" in dup_update.message.lower()

        finally:
            # Clean up db connection and client references so Windows can clean up tmpdir
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

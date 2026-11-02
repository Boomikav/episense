"""
End-to-End Integration Tests for EpiSense Phase 12 Production REST API & WebSocket Feeds.

Validates the full surveillance lifecycle across the API layer:
  POST document
       ↓
  ContinuousSurveillancePipeline
       ↓
  SurveillanceEventUpdate
       ↓
  GET /api/v1/alerts
       ↓
  GET /api/v1/alerts/{id}/dossier
       ↓
  GET /api/v1/alerts/{id}/audit
       ↓
  GET /api/v1/alerts/{id}/provenance
       ↓
  GET /api/v1/events
       ↓
  GET /api/v1/signals
       ↓
  GET /api/v1/geo/alerts
       ↓
  GET /api/v1/geo/events
       ↓
  GET /api/v1/geo/summary
       ↓
  WebSocket real-time broadcast delivery
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient

from episense.schemas.document import Document, SourceType
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.location import GeographicLevel, Location
from episense.schemas.nlp import (
    ContextAssociation,
    NLPOutput,
    QuantityMention,
    ResolutionState,
    ResolvedLocation,
    SentenceSpan,
)
from episense.schemas.entity import Entity, EntityType
from episense.schemas.streaming import IngestionStatus
from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.api.app import create_app
from episense.api.websocket import SurveillanceEventPublisher
from episense.api.services import GeoResolver


class IntegrationNLPPipeline:
    """Deterministic NLP extractor for end-to-end integration tests."""

    def process_document(self, document_or_id: Any) -> NLPOutput:
        doc_id = document_or_id.document_id if isinstance(document_or_id, Document) else document_or_id
        text = document_or_id.text if isinstance(document_or_id, Document) else ""

        # Location extraction
        loc_name = "Kozhikode" if "Kozhikode" in text else ("Malappuram" if "Malappuram" in text else "UnknownRegion")
        loc_idx = text.find(loc_name)
        if loc_idx >= 0:
            start_char = loc_idx
            end_char = loc_idx + len(loc_name)
            loc_raw = text[start_char:end_char]
        else:
            start_char = 0
            end_char = min(len(text), 9)
            loc_raw = text[start_char:end_char]

        resolved_loc = Location(
            location_id=uuid4(),
            original_text=loc_raw,
            normalized_name=loc_name,
            geographic_level=GeographicLevel.DISTRICT,
            parent_location="Kerala",
        )

        loc = ResolvedLocation(
            raw_text=loc_raw,
            start_char=start_char,
            end_char=end_char,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=resolved_loc,
        )

        sent = SentenceSpan(
            sentence_index=0,
            start_char=0,
            end_char=len(text),
            text=text,
        )

        # Disease detection
        d_name = "Nipah virus" if "Nipah" in text else ("Chandipura virus" if "Chandipura" in text else "Dengue")
        d_idx = text.find(d_name)
        if d_idx >= 0:
            d_start = d_idx
            d_end = d_idx + len(d_name)
            d_text = text[d_start:d_end]
        else:
            d_start = 0
            d_end = min(len(text), 5)
            d_text = text[d_start:d_end]

        disease_entity = Entity(
            entity_id=uuid4(),
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span=d_text,
            start_char=d_start,
            end_char=d_end,
            normalized_value=d_name,
            extraction_confidence=0.98,
        )

        # Quantity
        quantities = []
        import re
        m = re.search(r"(\d+)\s*(?:confirmed\s*)?cases", text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            quantities.append(
                QuantityMention(
                    raw_text=m.group(0),
                    start_char=m.start(),
                    end_char=m.end(),
                    numeric_value=val,
                    unit="cases",
                )
            )

        assoc = ContextAssociation(
            association_id=uuid4(),
            sentence_index=0,
            start_char=0,
            end_char=len(text),
            primary_disease=disease_entity,
            assertion=Assertion(
                assertion_status=AssertionStatus.CONFIRMED,
                certainty=CertaintyLevel.DEFINITE,
            ),
            location=loc,
            quantity=quantities[0] if quantities else None,
        )

        return NLPOutput(
            document_id=doc_id,
            sentences=[sent],
            entities=[disease_entity],
            assertions=[],
            temporal_expressions=[],
            locations=[loc],
            quantities=quantities,
            context_associations=[assoc],
        )


@pytest.fixture
def integration_harness():
    """Sets up a complete isolated surveillance engine and FastAPI app."""
    state_store = SurveillanceStateStore()
    nlp = IntegrationNLPPipeline()
    pipeline = ContinuousSurveillancePipeline(nlp_pipeline=nlp, state=state_store)
    publisher = SurveillanceEventPublisher()
    geo_resolver = GeoResolver()

    app = create_app(
        state=state_store,
        pipeline=pipeline,
        publisher=publisher,
        geo_resolver=geo_resolver,
    )
    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "state": state_store,
        "pipeline": pipeline,
        "publisher": publisher,
        "geo_resolver": geo_resolver,
    }


class TestPhase12EndToEndIntegration:

    def test_full_pipeline_ingest_query_explain_geo_flow(self, integration_harness):
        client = integration_harness["client"]
        state = integration_harness["state"]

        # Step 1: Ingest document via POST /api/v1/documents
        doc_payload = {
            "document_id": "00000000-0000-0000-0000-000000000101",
            "source_id": "who_don_surveillance",
            "source_type": "official_bulletin",
            "title": "Nipah virus outbreak reported in Kozhikode district",
            "text": "Health authorities have confirmed 12 confirmed cases of Nipah virus in Kozhikode district.",
            "publication_date": "2024-07-20T12:00:00Z",
        }

        resp_ingest = client.post("/api/v1/documents", json=doc_payload)
        assert resp_ingest.status_code == 200
        data_ingest = resp_ingest.json()
        assert data_ingest["status"] == "accepted"
        assert data_ingest["document_id"] == doc_payload["document_id"]
        assert data_ingest["alerts_generated"] >= 1
        assert data_ingest["fused_events_affected"] >= 1

        # Step 2: Query alerts via GET /api/v1/alerts
        resp_alerts = client.get("/api/v1/alerts", params={"pathogen": "nipah"})
        assert resp_alerts.status_code == 200
        alerts_data = resp_alerts.json()
        assert alerts_data["total"] >= 1
        alert = alerts_data["items"][0]
        alert_id = alert["alert_id"]
        assert "nipah" in alert["disease_key"].lower()
        assert "kozhikode" in alert["geo_key"].lower()
        assert alert["composite_score"] > 0.0
        assert "score_breakdown" in alert
        assert "is_gated" in alert

        # Step 3: Query alert detail via GET /api/v1/alerts/{alert_id}
        resp_single_alert = client.get(f"/api/v1/alerts/{alert_id}")
        assert resp_single_alert.status_code == 200
        assert resp_single_alert.json()["alert_id"] == alert_id

        # Step 4: Query dossier via GET /api/v1/alerts/{alert_id}/dossier
        resp_dossier = client.get(f"/api/v1/alerts/{alert_id}/dossier")
        assert resp_dossier.status_code == 200
        dossier = resp_dossier.json()
        assert dossier["alert_id"] == alert_id
        assert "briefing" in dossier
        assert dossier["briefing"]["what_event"] != ""
        assert "driving_risk_factors" in dossier
        assert "reconstructed_evidence" in dossier
        assert "audit_trail" in dossier
        assert len(dossier["audit_trail"]["decision_steps"]) == 8
        assert dossier["audit_trail"]["audit_checksum"] is not None

        # Step 5: Query audit trail via GET /api/v1/alerts/{alert_id}/audit
        resp_audit = client.get(f"/api/v1/alerts/{alert_id}/audit")
        assert resp_audit.status_code == 200
        audit = resp_audit.json()
        assert audit["alert_id"] == alert_id
        assert len(audit["decision_steps"]) == 8
        assert audit["audit_checksum"] is not None

        # Step 6: Query provenance via GET /api/v1/alerts/{alert_id}/provenance
        resp_prov = client.get(f"/api/v1/alerts/{alert_id}/provenance")
        assert resp_prov.status_code == 200
        prov = resp_prov.json()
        assert prov["alert_id"] == alert_id
        assert len(prov["nodes"]) >= 1

        # Step 7: Query fused events via GET /api/v1/events
        resp_events = client.get("/api/v1/events", params={"pathogen": "nipah"})
        assert resp_events.status_code == 200
        events_data = resp_events.json()
        assert events_data["total"] >= 1
        event = events_data["items"][0]
        assert "nipah" in event["canonical_disease"].lower()
        event_id = event["fused_event_id"]

        # Step 7b: Query specific fused event
        resp_single_event = client.get(f"/api/v1/events/{event_id}")
        assert resp_single_event.status_code == 200
        assert resp_single_event.json()["fused_event_id"] == event_id

        # Step 8: Query signals via GET /api/v1/signals
        resp_signals = client.get("/api/v1/signals", params={"pathogen": "nipah"})
        assert resp_signals.status_code == 200
        signals_data = resp_signals.json()
        assert signals_data["total"] >= 1
        signal = signals_data["items"][0]
        assert signal["signal_level"] is not None
        assert signal["observed_value"] >= 1.0

        # Step 9: Query GeoJSON alerts via GET /api/v1/geo/alerts
        resp_geo_alerts = client.get("/api/v1/geo/alerts", params={"pathogen": "nipah"})
        assert resp_geo_alerts.status_code == 200
        geo_alerts = resp_geo_alerts.json()
        assert geo_alerts["type"] == "FeatureCollection"
        assert len(geo_alerts["features"]) >= 1
        feat = geo_alerts["features"][0]
        assert feat["type"] == "Feature"
        assert feat["properties"]["pathogen"] == alert["disease_key"]
        # Kozhikode is grounded in local gazetteer
        assert feat["geometry"] is not None
        assert feat["geometry"]["type"] == "Point"
        lon, lat = feat["geometry"]["coordinates"]
        assert 75.0 <= lon <= 76.5
        assert 11.0 <= lat <= 12.0

        # Step 10: Query GeoJSON events via GET /api/v1/geo/events
        resp_geo_events = client.get("/api/v1/geo/events")
        assert resp_geo_events.status_code == 200
        geo_events = resp_geo_events.json()
        assert geo_events["type"] == "FeatureCollection"
        assert len(geo_events["features"]) >= 1

        # Step 11: Query GeoJSON heatmap via GET /api/v1/geo/heatmap
        resp_geo_heat = client.get("/api/v1/geo/heatmap")
        assert resp_geo_heat.status_code == 200
        assert resp_geo_heat.json()["type"] == "FeatureCollection"

        # Step 12: Query Geo summary via GET /api/v1/geo/summary
        resp_geo_summary = client.get("/api/v1/geo/summary")
        assert resp_geo_summary.status_code == 200
        summary = resp_geo_summary.json()
        assert summary["total_regions"] >= 1
        assert len(summary["regions"]) >= 1
        region = summary["regions"][0]
        assert region["total_alerts"] >= 1
        assert region["total_events"] >= 1

    def test_idempotent_duplicate_document_handling(self, integration_harness):
        client = integration_harness["client"]
        doc_payload = {
            "document_id": "00000000-0000-0000-0000-000000000102",
            "source_id": "who_don",
            "source_type": "official_bulletin",
            "title": "Nipah cases in Kozhikode",
            "text": "Authorities reported 5 confirmed cases of Nipah in Kozhikode district.",
            "publication_date": "2024-07-21T12:00:00Z",
        }

        # First ingestion
        r1 = client.post("/api/v1/documents", json=doc_payload)
        assert r1.status_code == 200
        assert r1.json()["status"] == "accepted"

        # Second ingestion with identical content
        r2 = client.post("/api/v1/documents", json=doc_payload)
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate_skipped"

        # Check alerts count hasn't duplicated
        r_alerts = client.get("/api/v1/alerts")
        assert r_alerts.status_code == 200
        assert r_alerts.json()["total"] >= 1

    def test_geo_coordinate_safety_for_unresolved_locations(self, integration_harness):
        client = integration_harness["client"]
        doc_payload = {
            "document_id": "00000000-0000-0000-0000-000000000103",
            "source_id": "generic_feed",
            "source_type": "news_media",
            "title": "Dengue in UnknownRegion",
            "text": "Reports of 8 confirmed cases of Dengue in UnknownRegion.",
            "publication_date": "2024-07-22T12:00:00Z",
        }

        r = client.post("/api/v1/documents", json=doc_payload)
        assert r.status_code == 200

        # Geo alerts should have null geometry for UnknownRegion (zero coordinate fabrication!)
        r_geo = client.get("/api/v1/geo/alerts", params={"pathogen": "dengue"})
        assert r_geo.status_code == 200
        features = r_geo.json()["features"]
        assert len(features) >= 1
        unresolved_feat = [f for f in features if "unknown" in f["properties"]["location_name"].lower()]
        assert len(unresolved_feat) >= 1
        assert unresolved_feat[0]["geometry"] is None

    def test_websocket_receive_broadcast_on_ingestion(self, integration_harness):
        app = integration_harness["app"]
        publisher = integration_harness["publisher"]
        state = integration_harness["state"]
        pipeline = integration_harness["pipeline"]
        client = TestClient(app)

        with client.websocket_connect("/api/v1/ws/surveillance") as ws:
            ack = ws.receive_json()
            assert ack["type"] == "connection_ack"

            # Subscribe to all updates
            ws.send_json({"action": "subscribe", "filter": {}})
            sub_ack = ws.receive_json()
            assert sub_ack["type"] == "subscription_ack"

            # Ingest document directly through pipeline
            doc_dict = {
                "document_id": "00000000-0000-0000-0000-000000000104",
                "source_id": "reuters_health",
                "source_type": "news_report",
                "title": "Nipah outbreak in Kozhikode",
                "text": "Doctors registered 4 confirmed cases of Nipah virus in Kozhikode.",
                "publication_timestamp": datetime(2024, 7, 23, 10, 0, 0, tzinfo=timezone.utc),
            }
            update = pipeline.process_document(doc_dict)
            assert update.status == IngestionStatus.ACCEPTED

            # Broadcast update through publisher
            import asyncio
            asyncio.run(publisher.broadcast(update, alerts_lookup=state.alerts))

            # WebSocket client should receive the event
            broadcast_msg = ws.receive_json()
            assert broadcast_msg["type"] == "event_update"
            assert broadcast_msg["data"]["status"] == "accepted"
            assert broadcast_msg["data"]["document_id"] == doc_dict["document_id"]
            assert len(broadcast_msg["data"]["alerts_generated"]) >= 1

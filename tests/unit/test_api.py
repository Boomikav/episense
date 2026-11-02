"""
Unit Tests for EpiSense REST API (Phase 12).
Covers health probes, document ingestion, alert queries, explainability/audit/provenance,
fused events, early signals, security middleware, and OpenAPI specs.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
import pytest
from fastapi.testclient import TestClient

from episense.config.settings import APIConfig
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.schemas.alert import (
    AlertExplanation,
    AlertTier,
    EpidemiologicalAlert,
    PathogenThreatTier,
    RiskScoreBreakdown,
)
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.document import Document
from episense.schemas.event import (
    EpidemiologicalQuantities,
    EvidenceReference,
    FusedEvent,
    SourceGroup,
)
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.signal import (
    BaselineReliability,
    DetectionMethod,
    SignalLevel,
    SignalObservation,
)
from episense.streaming.state import SurveillanceStateStore
from episense.api.app import create_app


def make_sample_doc(text: str, title: str = "Test Outbreak Report", doc_id: Optional[UUID] = None) -> Document:
    import hashlib
    document_id = doc_id or uuid5(NAMESPACE_DNS, f"doc:{text[:30]}")
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        document_id=document_id,
        source_id="test_wire",
        title=title,
        text=text,
        publication_timestamp=datetime(2024, 7, 25, 10, 0, tzinfo=timezone.utc),
        content_hash_sha256=content_hash,
    )


def make_sample_alert(disease: str = "nipah", geo: str = "kozhikode", score: float = 0.75) -> EpidemiologicalAlert:
    aid = uuid5(NAMESPACE_DNS, f"alert:{disease}:{geo}:{score}")
    sig_id = uuid5(NAMESPACE_DNS, f"sig:{disease}:{geo}")
    fe_id = uuid5(NAMESPACE_DNS, f"fe:{disease}:{geo}")
    doc_id = uuid5(NAMESPACE_DNS, "doc:test")
    start = datetime(2024, 7, 22, tzinfo=timezone.utc)
    end = datetime(2024, 7, 28, tzinfo=timezone.utc)

    ev = EvidenceReference(
        document_id=doc_id,
        source_id="src_1",
        start_char=0,
        end_char=len(disease),
        span_text=disease,
        extraction_method="ner:test",
        attribute_role="primary_disease",
    )
    breakdown = RiskScoreBreakdown(
        anomaly_score=score,
        threat_score=score,
        evidence_score=score,
        certainty_score=score,
        spatial_score=score,
        raw_composite_score=score,
        penalty_applied=0.0,
        final_score=score,
    )
    return EpidemiologicalAlert(
        alert_id=aid,
        signal_id=sig_id,
        disease_key=disease,
        geo_key=geo,
        pathogen_threat_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        period_start=start,
        period_end=end,
        composite_score=score,
        alert_tier=AlertTier.MEDIUM,
        score_breakdown=breakdown,
        explanation=AlertExplanation(summary=f"Surveillance alert for {disease} in {geo}."),
        supporting_fused_event_ids=[fe_id],
        supporting_source_count=1,
        provenance_references=[ev],
        created_at=end,
    )


@pytest.fixture
def api_client():
    state = SurveillanceStateStore()
    alert = make_sample_alert()
    state.alerts[alert.alert_id] = alert

    fe = FusedEvent(
        fused_event_id=alert.supporting_fused_event_ids[0],
        canonical_disease="nipah",
        canonical_location=Location(
            original_text="Kozhikode",
            normalized_name="Kozhikode",
            geographic_level=GeographicLevel.DISTRICT,
            latitude=11.2588,
            longitude=75.7804,
        ),
        event_window_start=alert.period_start,
        event_window_end=alert.period_end,
        assertion_status=AssertionStatus.CONFIRMED,
        certainty=CertaintyLevel.PROBABLE,
        aggregated_quantities=EpidemiologicalQuantities(case_count=2),
        independent_sources=[SourceGroup(source_id="src_1", independence_group="g1")],
        independent_source_count=1,
        created_at=alert.period_end,
        updated_at=alert.period_end,
    )
    state.fused_events[fe.fused_event_id] = fe

    sig = SignalObservation(
        signal_id=alert.signal_id,
        disease_key="nipah",
        geo_key="kozhikode",
        target_period_start=alert.period_start,
        target_period_end=alert.period_end,
        observed_value=2.0,
        expected_value=0.0,
        deviation=2.0,
        threshold=2.0,
        signal_level=SignalLevel.SIGNAL,
        detection_method=DetectionMethod.EARS_C2,
        reliability_status=BaselineReliability.STABLE_BASELINE,
        supporting_fused_event_ids=[fe.fused_event_id],
        provenance_references=alert.provenance_references,
    )
    state.signals[sig.signal_id] = sig

    doc = make_sample_doc(
        text="Nipah virus cases were reported in Kozhikode.",
        title="Nipah Alert",
        doc_id=alert.provenance_references[0].document_id,
    )
    state.documents[doc.document_id] = doc

    config = APIConfig(max_payload_bytes=1024 * 1024)
    pipeline = ContinuousSurveillancePipeline(state=state)
    app = create_app(config=config, state=state, pipeline=pipeline)
    return TestClient(app)


class TestAPI:

    def test_health_endpoint(self, api_client):
        res = api_client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["pipeline_available"] is True
        assert data["state_store_available"] is True

    def test_readiness_probe(self, api_client):
        res = api_client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["ready"] is True
        assert data["state_alerts_count"] >= 1

    def test_liveness_probe(self, api_client):
        res = api_client.get("/health/live")
        assert res.status_code == 200
        assert res.json()["live"] is True

    def test_document_ingestion_success(self, api_client):
        payload = {
            "title": "New Dengue Outbreak",
            "text": "Ten dengue cases were confirmed in Pune on 15 August 2024.",
            "source_id": "pune_health_bulletin",
        }
        res = api_client.post("/api/v1/documents", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["update_id"] is not None
        assert data["fused_events_affected"] >= 1

    def test_document_ingestion_idempotency_duplicate(self, api_client):
        payload = {
            "title": "Cholera Cases in Puri",
            "text": "Five confirmed cholera cases in Puri reported today.",
            "source_id": "puri_news",
        }
        res1 = api_client.post("/api/v1/documents", json=payload)
        assert res1.status_code == 200
        assert res1.json()["status"] == "accepted"

        # Submit exact duplicate
        res2 = api_client.post("/api/v1/documents", json=payload)
        assert res2.status_code == 200
        assert res2.json()["status"] == "duplicate_skipped"

    def test_document_ingestion_validation_error_empty_text(self, api_client):
        payload = {
            "title": "Empty Report",
            "text": "",
        }
        res = api_client.post("/api/v1/documents", json=payload)
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_list_alerts(self, api_client):
        res = api_client.get("/api/v1/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["disease_key"] == "nipah"

    def test_list_alerts_filtering(self, api_client):
        # Match
        res1 = api_client.get("/api/v1/alerts?pathogen=nipah&tier=medium")
        assert res1.status_code == 200
        assert len(res1.json()["items"]) == 1

        # No match
        res2 = api_client.get("/api/v1/alerts?pathogen=nonexistentdisease")
        assert res2.status_code == 200
        assert len(res2.json()["items"]) == 0

    def test_get_alert_detail(self, api_client):
        alerts = api_client.get("/api/v1/alerts").json()["items"]
        aid = alerts[0]["alert_id"]

        res = api_client.get(f"/api/v1/alerts/{aid}")
        assert res.status_code == 200
        assert res.json()["alert_id"] == aid
        assert res.json()["composite_score"] == 0.75

    def test_get_alert_detail_not_found(self, api_client):
        random_id = str(uuid4())
        res = api_client.get(f"/api/v1/alerts/{random_id}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "ALERT_NOT_FOUND"

    def test_get_alert_detail_invalid_uuid(self, api_client):
        res = api_client.get("/api/v1/alerts/not-a-valid-uuid")
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_alert_dossier(self, api_client):
        alerts = api_client.get("/api/v1/alerts").json()["items"]
        aid = alerts[0]["alert_id"]

        res = api_client.get(f"/api/v1/alerts/{aid}/dossier")
        assert res.status_code == 200
        data = res.json()
        assert "briefing" in data
        assert "provenance_graph" in data
        assert "audit_trail" in data
        assert len(data["reconstructed_evidence"]) >= 1
        assert data["briefing"]["what_event"] is not None

    def test_alert_audit_trail(self, api_client):
        alerts = api_client.get("/api/v1/alerts").json()["items"]
        aid = alerts[0]["alert_id"]

        res = api_client.get(f"/api/v1/alerts/{aid}/audit")
        assert res.status_code == 200
        data = res.json()
        assert len(data["decision_steps"]) == 8
        assert "audit_checksum" in data
        assert len(data["audit_checksum"]) == 64

    def test_alert_provenance_graph(self, api_client):
        alerts = api_client.get("/api/v1/alerts").json()["items"]
        aid = alerts[0]["alert_id"]

        res = api_client.get(f"/api/v1/alerts/{aid}/provenance")
        assert res.status_code == 200
        data = res.json()
        assert data["is_acyclic"] is True
        assert len(data["nodes"]) >= 1
        assert len(data["edges"]) >= 1

    def test_list_events(self, api_client):
        res = api_client.get("/api/v1/events")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert data["items"][0]["canonical_disease"] == "nipah"

    def test_get_event_detail(self, api_client):
        events = api_client.get("/api/v1/events").json()["items"]
        eid = events[0]["fused_event_id"]

        res = api_client.get(f"/api/v1/events/{eid}")
        assert res.status_code == 200
        assert res.json()["fused_event_id"] == eid

    def test_get_event_detail_not_found(self, api_client):
        res = api_client.get(f"/api/v1/events/{uuid4()}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "EVENT_NOT_FOUND"

    def test_list_signals(self, api_client):
        res = api_client.get("/api/v1/signals")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert data["items"][0]["disease_key"] == "nipah"

    def test_get_signal_detail(self, api_client):
        signals = api_client.get("/api/v1/signals").json()["items"]
        sid = signals[0]["signal_id"]

        res = api_client.get(f"/api/v1/signals/{sid}")
        assert res.status_code == 200
        assert res.json()["signal_id"] == sid

    def test_get_signal_detail_not_found(self, api_client):
        res = api_client.get(f"/api/v1/signals/{uuid4()}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "SIGNAL_NOT_FOUND"

    def test_request_correlation_header(self, api_client):
        res = api_client.get("/health")
        assert "X-Request-ID" in res.headers
        assert res.headers["X-Request-ID"].startswith("req_")

        # Custom header echoed
        res2 = api_client.get("/health", headers={"X-Request-ID": "custom-trace-12345"})
        assert res2.headers["X-Request-ID"] == "custom-trace-12345"

    def test_cors_headers(self, api_client):
        res = api_client.options("/health", headers={"Origin": "https://dashboard.episense.org", "Access-Control-Request-Method": "GET"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") in ("*", "https://dashboard.episense.org")

    def test_payload_size_limit(self, api_client):
        # Configure app with tiny max_payload_bytes: 50 bytes
        tiny_app = create_app(config=APIConfig(max_payload_bytes=50))
        tiny_client = TestClient(tiny_app)

        large_payload = {"title": "A" * 100, "text": "B" * 200}
        res = tiny_client.post("/api/v1/documents", json=large_payload)
        assert res.status_code == 413
        assert res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_openapi_documentation(self, api_client):
        res = api_client.get("/openapi.json")
        assert res.status_code == 200
        spec = res.json()
        assert spec["info"]["title"] == "EpiSense Epidemiological Surveillance API"
        assert "/api/v1/documents" in spec["paths"]
        assert "/api/v1/alerts" in spec["paths"]
        assert "/api/v1/geo/alerts" in spec["paths"]
        # WebSockets are registered on app routes
        route_paths = []
        for r in api_client.app.routes:
            if hasattr(r, "path"):
                route_paths.append(r.path)
            elif hasattr(r, "routes"):
                for sub_r in r.routes:
                    if hasattr(sub_r, "path"):
                        route_paths.append(sub_r.path)
        assert "/api/v1/ws/surveillance" in route_paths

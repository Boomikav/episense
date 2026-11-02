"""
Unit Tests for EpiSense Geospatial Surveillance API (Phase 12).
Verifies RFC 7946 GeoJSON layers, Point coordinate fidelity, zero coordinate fabrication, and regional summaries.
"""

from datetime import datetime, timezone
import pytest
from uuid import uuid5, NAMESPACE_DNS
from fastapi.testclient import TestClient

from episense.schemas.alert import (
    AlertExplanation,
    AlertTier,
    EpidemiologicalAlert,
    PathogenThreatTier,
    RiskScoreBreakdown,
)
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.event import (
    EpidemiologicalQuantities,
    EvidenceReference,
    FusedEvent,
    SourceGroup,
)
from episense.schemas.location import Location, GeographicLevel
from episense.streaming.state import SurveillanceStateStore
from episense.api.app import create_app
from episense.api.services import GeoResolver


def make_alert(disease: str, geo: str, score: float, tier: AlertTier) -> EpidemiologicalAlert:
    sig_id = uuid5(NAMESPACE_DNS, f"sig:{disease}:{geo}:{score}")
    aid = uuid5(NAMESPACE_DNS, f"alert:{disease}:{geo}:{score}")
    fe_id = uuid5(NAMESPACE_DNS, f"fe:{disease}:{geo}:{score}")
    start = datetime(2024, 7, 22, tzinfo=timezone.utc)
    end = datetime(2024, 7, 28, tzinfo=timezone.utc)
    ev_ref = EvidenceReference(
        document_id=uuid5(NAMESPACE_DNS, "doc:1"),
        source_id="src_1",
        start_char=0,
        end_char=len(disease),
        span_text=disease,
        extraction_method="test",
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
    explanation = AlertExplanation(summary=f"Alert for {disease} in {geo}")

    return EpidemiologicalAlert(
        alert_id=aid,
        signal_id=sig_id,
        disease_key=disease,
        geo_key=geo,
        pathogen_threat_tier=PathogenThreatTier.TIER_3_SEVERE,
        period_start=start,
        period_end=end,
        composite_score=score,
        alert_tier=tier,
        score_breakdown=breakdown,
        explanation=explanation,
        supporting_fused_event_ids=[fe_id],
        supporting_source_count=1,
        provenance_references=[ev_ref],
        created_at=end,
    )


def make_event(disease: str, loc_name: str, lat=None, lon=None) -> FusedEvent:
    fe_id = uuid5(NAMESPACE_DNS, f"event:{disease}:{loc_name}")
    start = datetime(2024, 7, 1, tzinfo=timezone.utc)
    end = datetime(2024, 7, 7, tzinfo=timezone.utc)
    loc = Location(
        original_text=loc_name,
        normalized_name=loc_name,
        geographic_level=GeographicLevel.DISTRICT,
        latitude=lat,
        longitude=lon,
    )
    return FusedEvent(
        fused_event_id=fe_id,
        canonical_disease=disease,
        canonical_location=loc,
        event_window_start=start,
        event_window_end=end,
        assertion_status=AssertionStatus.CONFIRMED,
        certainty=CertaintyLevel.PROBABLE,
        aggregated_quantities=EpidemiologicalQuantities(case_count=10),
        independent_sources=[SourceGroup(source_id="src1", independence_group="g1")],
        independent_source_count=1,
        created_at=end,
        updated_at=end,
    )


@pytest.fixture
def populated_client():
    state = SurveillanceStateStore()
    # 1. Known location with verified gazetteer coordinates (Kozhikode, Kerala)
    a1 = make_alert("nipah", "Kozhikode", 0.85, AlertTier.HIGH)
    # 2. Known location (Pune, Maharashtra)
    a2 = make_alert("zika", "Pune", 0.65, AlertTier.MEDIUM)
    # 3. Unknown location with NO gazetteer coordinates
    a3 = make_alert("cholera", "UnknownFictionalDistrict", 0.45, AlertTier.LOW)

    state.alerts[a1.alert_id] = a1
    state.alerts[a2.alert_id] = a2
    state.alerts[a3.alert_id] = a3

    # Events
    e1 = make_event("nipah", "Kozhikode", lat=11.2588, lon=75.7804)
    e2 = make_event("cholera", "UnknownFictionalDistrict", lat=None, lon=None)
    state.fused_events[e1.fused_event_id] = e1
    state.fused_events[e2.fused_event_id] = e2

    app = create_app(state=state)
    return TestClient(app)


class TestGeoAPI:

    def test_get_geo_alerts_valid_rfc7946(self, populated_client):
        res = populated_client.get("/api/v1/geo/alerts")
        assert res.status_code == 200
        data = res.json()

        assert data["type"] == "FeatureCollection"
        assert data["total_features"] == 3
        assert data["features_with_geometry"] == 2
        assert data["unresolved_locations"] == 1

        # Check features
        features = data["features"]
        kozhikode_feature = next(f for f in features if f["properties"]["location_name"] == "Kozhikode")
        assert kozhikode_feature["geometry"]["type"] == "Point"
        # GeoJSON is [longitude, latitude]
        coords = kozhikode_feature["geometry"]["coordinates"]
        assert pytest.approx(coords[0], 0.01) == 75.7804
        assert pytest.approx(coords[1], 0.01) == 11.2588
        assert kozhikode_feature["properties"]["has_geometry"] is True
        assert kozhikode_feature["properties"]["alert_tier"] == "high"

    def test_get_geo_alerts_no_fabricated_coordinates(self, populated_client):
        res = populated_client.get("/api/v1/geo/alerts")
        data = res.json()
        unresolved = next(f for f in data["features"] if f["properties"]["location_name"] == "UnknownFictionalDistrict")
        # Geometry must strictly be None / null
        assert unresolved["geometry"] is None
        assert unresolved["properties"]["has_geometry"] is False

    def test_get_geo_alerts_filtering(self, populated_client):
        res = populated_client.get("/api/v1/geo/alerts?tier=high")
        assert res.status_code == 200
        data = res.json()
        assert data["total_features"] == 1
        assert data["features"][0]["properties"]["pathogen"] == "nipah"

    def test_get_geo_events(self, populated_client):
        res = populated_client.get("/api/v1/geo/events")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        assert data["total_features"] == 2
        assert data["features_with_geometry"] == 1

        f1 = next(f for f in data["features"] if f["properties"]["canonical_disease"] == "nipah")
        assert f1["geometry"]["type"] == "Point"
        assert f1["properties"]["case_count"] == 10

    def test_get_geo_heatmap(self, populated_client):
        res = populated_client.get("/api/v1/geo/heatmap")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        # Only features with geometry should be present in heatmap
        assert data["total_features"] == 2
        for f in data["features"]:
            assert f["geometry"] is not None
            assert f["properties"]["weight"] > 0.0

    def test_get_geo_summary(self, populated_client):
        res = populated_client.get("/api/v1/geo/summary")
        assert res.status_code == 200
        data = res.json()
        assert data["total_regions"] >= 2
        regions = data["regions"]
        # Deterministic sort: total_alerts DESC
        assert regions[0]["total_alerts"] >= regions[1]["total_alerts"]
        kozhikode_summary = next(r for r in regions if r["region"] == "Kozhikode")
        assert kozhikode_summary["total_alerts"] == 1
        assert kozhikode_summary["high_alerts"] == 1
        assert kozhikode_summary["has_geometry"] is True
        assert "Nipah" in kozhikode_summary["pathogens"]

    def test_geo_determinism(self, populated_client):
        res1 = populated_client.get("/api/v1/geo/alerts").text
        res2 = populated_client.get("/api/v1/geo/alerts").text
        assert res1 == res2

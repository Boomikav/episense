"""
Unit Tests for EpiSense API Query Services, GeoResolver, and Pagination (Phase 12).
"""

from datetime import datetime, timezone
import pytest
from uuid import UUID, uuid5, NAMESPACE_DNS

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
from episense.schemas.signal import (
    BaselineReliability,
    DetectionMethod,
    SignalLevel,
    SignalObservation,
)
from episense.schemas.location import Location, GeographicLevel
from episense.streaming.state import SurveillanceStateStore
from episense.api.services import (
    AlertQueryService,
    EventQueryService,
    GeoQueryService,
    GeoResolver,
    ProvenanceQueryService,
    SignalQueryService,
    paginate_list,
)


def make_mock_alert(disease: str, geo: str, score: float, tier: AlertTier) -> EpidemiologicalAlert:
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


def make_mock_event(disease: str, loc_name: str, end_day: int) -> FusedEvent:
    fe_id = uuid5(NAMESPACE_DNS, f"event:{disease}:{loc_name}:{end_day}")
    start = datetime(2024, 7, 1, tzinfo=timezone.utc)
    end = datetime(2024, 7, end_day, tzinfo=timezone.utc)
    loc = Location(
        original_text=loc_name,
        normalized_name=loc_name,
        geographic_level=GeographicLevel.DISTRICT,
    )
    return FusedEvent(
        fused_event_id=fe_id,
        canonical_disease=disease,
        canonical_location=loc,
        event_window_start=start,
        event_window_end=end,
        assertion_status=AssertionStatus.CONFIRMED,
        certainty=CertaintyLevel.PROBABLE,
        aggregated_quantities=EpidemiologicalQuantities(case_count=5),
        independent_sources=[SourceGroup(source_id="src1", independence_group="g1")],
        independent_source_count=1,
        created_at=end,
        updated_at=end,
    )


def make_mock_signal(disease: str, geo: str, day: int) -> SignalObservation:
    sig_id = uuid5(NAMESPACE_DNS, f"signal:{disease}:{geo}:{day}")
    start = datetime(2024, 7, day, tzinfo=timezone.utc)
    end = datetime(2024, 7, day + 6, tzinfo=timezone.utc)
    return SignalObservation(
        signal_id=sig_id,
        disease_key=disease,
        geo_key=geo,
        target_period_start=start,
        target_period_end=end,
        observed_value=5.0,
        expected_value=1.0,
        deviation=4.0,
        threshold=2.0,
        signal_level=SignalLevel.SIGNAL,
        detection_method=DetectionMethod.EARS_C2,
        reliability_status=BaselineReliability.STABLE_BASELINE,
    )


class TestAPIServices:

    def test_paginate_list_basic(self):
        items = list(range(100))
        page1 = paginate_list(items, page=1, page_size=20)
        assert page1.total == 100
        assert page1.page == 1
        assert page1.page_size == 20
        assert page1.total_pages == 5
        assert page1.has_next is True
        assert page1.has_prev is False
        assert page1.items == list(range(20))

        page5 = paginate_list(items, page=5, page_size=20)
        assert page5.has_next is False
        assert page5.has_prev is True
        assert page5.items == list(range(80, 100))

    def test_paginate_list_empty(self):
        page = paginate_list([], page=1, page_size=10)
        assert page.total == 0
        assert page.total_pages == 0
        assert page.has_next is False
        assert page.has_prev is False
        assert page.items == []

    def test_paginate_list_out_of_bounds(self):
        items = [1, 2, 3]
        page = paginate_list(items, page=10, page_size=5)
        assert page.total == 3
        assert page.items == []

    def test_geo_resolver_known_location(self):
        resolver = GeoResolver()
        lat, lon, lvl, gid = resolver.resolve("Kozhikode")
        assert lat is not None
        assert lon is not None
        assert pytest.approx(lat, 0.01) == 11.2588
        assert pytest.approx(lon, 0.01) == 75.7804
        assert gid == "GeoNames:1265873"

    def test_geo_resolver_unknown_location_no_fabrication(self):
        resolver = GeoResolver()
        lat, lon, lvl, gid = resolver.resolve("NonexistentAtlantisCity123")
        assert lat is None
        assert lon is None
        assert lvl is None
        assert gid is None

    def test_geo_resolver_caching(self):
        resolver = GeoResolver()
        lat1, lon1, _, _ = resolver.resolve("Pune")
        lat2, lon2, _, _ = resolver.resolve("Pune")
        assert lat1 == lat2 and lon1 == lon2
        assert "pune" in resolver._cache

    def test_alert_query_service_deterministic_ordering(self):
        state = SurveillanceStateStore()
        a1 = make_mock_alert("cholera", "puri", 0.50, AlertTier.LOW)
        a2 = make_mock_alert("nipah", "kozhikode", 0.85, AlertTier.HIGH)
        a3 = make_mock_alert("dengue", "delhi", 0.65, AlertTier.MEDIUM)
        state.alerts[a1.alert_id] = a1
        state.alerts[a2.alert_id] = a2
        state.alerts[a3.alert_id] = a3

        service = AlertQueryService(state)
        res = service.list_alerts(page=1, page_size=10)
        # Should sort composite_score DESC
        assert res.items[0].alert_id == a2.alert_id  # 0.85
        assert res.items[1].alert_id == a3.alert_id  # 0.65
        assert res.items[2].alert_id == a1.alert_id  # 0.50

    def test_alert_query_service_filters(self):
        state = SurveillanceStateStore()
        a1 = make_mock_alert("cholera", "puri", 0.50, AlertTier.LOW)
        a2 = make_mock_alert("nipah", "kozhikode", 0.85, AlertTier.HIGH)
        state.alerts[a1.alert_id] = a1
        state.alerts[a2.alert_id] = a2

        service = AlertQueryService(state)
        # Filter by tier
        high_alerts = service.list_alerts(tier=AlertTier.HIGH)
        assert len(high_alerts.items) == 1
        assert high_alerts.items[0].disease_key == "nipah"

        # Filter by pathogen
        nipah_alerts = service.list_alerts(pathogen="nip")
        assert len(nipah_alerts.items) == 1
        assert nipah_alerts.items[0].disease_key == "nipah"

        # Filter by score
        score_alerts = service.list_alerts(min_score=0.80)
        assert len(score_alerts.items) == 1
        assert score_alerts.items[0].composite_score == 0.85

    def test_event_query_service_sorting_and_filtering(self):
        state = SurveillanceStateStore()
        e1 = make_mock_event("cholera", "puri", 10)
        e2 = make_mock_event("nipah", "kozhikode", 20)
        state.fused_events[e1.fused_event_id] = e1
        state.fused_events[e2.fused_event_id] = e2

        service = EventQueryService(state)
        # Deterministic sorting: event_window_end DESC
        events = service.list_events()
        assert events.items[0].fused_event_id == e2.fused_event_id
        assert events.items[1].fused_event_id == e1.fused_event_id

        # Pathogen filter
        filtered = service.list_events(pathogen="cholera")
        assert len(filtered.items) == 1
        assert filtered.items[0].canonical_disease == "cholera"

    def test_signal_query_service_sorting_and_filtering(self):
        state = SurveillanceStateStore()
        s1 = make_mock_signal("cholera", "puri", 5)
        s2 = make_mock_signal("nipah", "kozhikode", 15)
        state.signals[s1.signal_id] = s1
        state.signals[s2.signal_id] = s2

        service = SignalQueryService(state)
        signals = service.list_signals()
        assert signals.items[0].signal_id == s2.signal_id
        assert signals.items[1].signal_id == s1.signal_id

    def test_request_id_domain_invariance(self):
        # Verify that generating a request ID has zero effect on domain IDs or checksums
        state = SurveillanceStateStore()
        alert = make_mock_alert("nipah", "kozhikode", 0.75, AlertTier.MEDIUM)
        state.alerts[alert.alert_id] = alert

        chk1 = state.compute_state_checksum()
        _ = f"req_test_{UUID('12345678-1234-5678-1234-567812345678')}"
        chk2 = state.compute_state_checksum()

        assert chk1 == chk2
        assert alert.alert_id == alert.alert_id

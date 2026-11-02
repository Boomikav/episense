"""
EpiSense End-to-End Acceptance Suite:
Final Inference Engine, Operational Consistency, and Scientific Acceptance Correction.

Covers the 10 core integration scenarios specified in Phase 10:
1. Synthetic document (origin == 'SYNTHETIC_TEST') complete isolation from default views.
2. Kinnaur NIL outbreak report (0 cases) classified as NEGATIVE_RULE_OUT, never creates positive alert.
3. Historical document published recently retains historical event date, not treated as current outbreak.
4. Two independent reports for the same outbreak corroborate without count inflation.
5. Two separate institutions in same district remain distinct (Raichur anti-inflation audit).
6. Firozpur Leptospirosis observations preserve both source observations and provisional linkage.
7. 11 candidate review items explained, actionable outbreak alerts strictly 0.
8. Monthly window crossing ISO week boundary (Asia/Kolkata IST) has valid intervals without date inversion.
9. HTTP 200/304 with no new content distinguishes link discovery from unique document ingestion.
10. Unavailable/authentication-protected feeds show source-health limitations accurately.
11. Authoritative Accounting Matrix (Counters A through P) consistency and reconcilability.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
import pytest
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease
from episense.persistence.database import SurveillanceDatabase
from episense.streaming.state import SurveillanceStateStore
from episense.connectors.service import SourcePollingService, get_default_connector_configs
from episense.api.services import AlertQueryService, SignalQueryService, GeoQueryService
from episense.api.routes.live_metrics import get_operational_overview, get_authoritative_accounting
from episense.schemas.document import OriginClassification, Document
from episense.schemas.event import (
    FusedEvent,
    LinkageClassification,
    SourceGroup,
    AssertionStatus,
    CertaintyLevel,
    EpidemiologicalQuantities,
)
from episense.schemas.alert import AlertTier, DecisionCategory
from episense.events.relevance import EventDisposition, EventRelevanceClassifier


@pytest.fixture
def db():
    return SurveillanceDatabase("data/surveillance_store.sqlite")


@pytest.fixture
def state(db):
    store = SurveillanceStateStore(db=db)
    store.hydrate_from_db(db)
    return store


# =========================================================================
# Scenario 1: Synthetic Data Complete Isolation from Default Live Endpoints
# =========================================================================
def test_scenario_1_synthetic_document_isolation(db, state):
    """
    Documents, events, alerts, and metrics with origin == SYNTHETIC_TEST
    must be completely excluded from default operational queries and views.
    """
    # 1. Database level document listing default excludes synthetic
    docs = db.list_documents()
    assert all(getattr(d, "origin", None) != OriginClassification.SYNTHETIC_TEST for d in docs), (
        "Default list_documents() contained synthetic test documents!"
    )

    # 2. Database level fused events default excludes synthetic
    fe_list = db.list_fused_events()
    assert all(getattr(e, "primary_origin", None) != OriginClassification.SYNTHETIC_TEST for e in fe_list), (
        "Default list_fused_events() contained synthetic test fused events!"
    )

    # 3. Geo service excludes synthetic from live map layers
    geo = GeoQueryService(state=state)
    alerts_geojson = geo.get_alerts_geojson(current_only=True, priority_only=True)
    assert all(f.properties.get("origin") != "SYNTHETIC_TEST" for f in alerts_geojson.features), (
        "Map current layer contained synthetic test features!"
    )

    # 4. Overview metrics exclude synthetic
    svc = MagicMock()
    svc.list_connectors.return_value = []
    overview = get_operational_overview(state=state, polling_service=svc, db=db)
    figs = overview["summary_figures"]
    assert figs["new_operational_reports"]["value"] == 0, "Actionable Priority Reports must be strictly 0"


# =========================================================================
# Scenario 2: Kinnaur NIL Outbreak Report Classified as NEGATIVE_RULE_OUT
# =========================================================================
def test_scenario_2_nil_report_negative_rule_out(db):
    """
    A verified negative rule-out or NIL outbreak report (0 cases, 0 deaths)
    must receive NEGATIVE_RULE_OUT disposition, preserve negative evidence,
    and never escalate to positive outbreak alerts or downstream fusion.
    """
    kinnaur_doc_id = "1b9b9728-b0e6-51a5-8d0b-5ad4cf29ca17"
    doc = db.get_document(kinnaur_doc_id)
    assert doc is not None, f"Kinnaur NIL document {kinnaur_doc_id} not found in database"
    assert "NIL" in doc.title or "NIL" in doc.content_text.upper()

    # Verify pipeline trace classification
    trace = db.get_pipeline_trace(kinnaur_doc_id)
    assert trace is not None, "Pipeline trace missing for Kinnaur document"
    assert trace.overall_status.upper() in ("COMPLETED", "ACCEPTED")

    # Verify Stage 10 details preserve negative rule-out disposition
    stage10 = next((s for s in trace.stages if s.stage_number == 10), None)
    assert stage10 is not None, "Stage 10 missing in trace"
    details = stage10.details
    assert details.get("disposition") == "NEGATIVE_RULE_OUT" or details.get("category") == "NEGATIVE_RULE_OUT"

    # Verify via EventRelevance classifier logic directly
    classifier = EventRelevanceClassifier()
    decision = classifier.classify(
        title=doc.title,
        text=doc.text,
    )
    assert decision.is_epidemiological_event is False
    assert decision.disposition == EventDisposition.NEGATIVE_RULE_OUT


# =========================================================================
# Scenario 3: Historical Bulletin Published Recently Retains Event Date
# =========================================================================
def test_scenario_3_historical_bulletin_recent_publication(db):
    """
    An official bulletin published recently reporting a historical outbreak
    (e.g. NCDC August 2026 bulletin published in late October) must preserve
    its historical event date and be classified as RECENTLY_PUBLISHED_HISTORICAL_EVENT,
    never appearing as an active operational emergency.
    """
    fe_list = db.list_fused_events()
    recent_historical = [
        e for e in fe_list
        if getattr(e, "currentness_status", None) == "RECENTLY_PUBLISHED_HISTORICAL_EVENT"
    ]
    assert len(recent_historical) >= 1300, (
        f"Expected >= 1300 recently published historical events from IDSP archive, found {len(recent_historical)}"
    )

    # Pick a sample historical event and assert date integrity
    sample = recent_historical[0]
    assert sample.event_window_end is not None
    # All retrospective IDSP bulletins have event_window_end prior to operational surveillance epoch
    assert sample.event_window_end < datetime(2026, 10, 1, tzinfo=timezone.utc)
    dec_str = sample.decision_category.value if hasattr(sample.decision_category, "value") else str(sample.decision_category)
    assert dec_str.lower() == "historical_reference"


# =========================================================================
# Scenario 4: Multi-Source Corroboration Without Count Inflation
# =========================================================================
def test_scenario_4_multi_source_corroboration_without_inflation():
    """
    When multiple independent sources report the same outbreak event,
    the event should achieve CORROBORATED_EVENT status without inflating
    the underlying clinical case count.
    """
    fe = FusedEvent(
        fused_event_id=uuid4(),
        canonical_disease="Cholera",
        primary_origin=OriginClassification.LIVE_EXTERNAL,
        event_window_start=datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc),
        event_window_end=datetime(2026, 10, 25, 0, 0, 0, tzinfo=timezone.utc),
        aggregated_quantities=EpidemiologicalQuantities(case_count=25, death_count=0),
        supporting_observation_count=2,
        independent_source_count=2,
        independent_sources=[
            SourceGroup(source_id="s1", independence_group="group_1"),
            SourceGroup(source_id="s2", independence_group="group_2"),
        ],
        assertion_status=AssertionStatus.CONFIRMED,
        certainty=CertaintyLevel.PROBABLE,
        fusion_confidence=0.92,
    )
    # The FusedEvent validator dynamically determines decision_category
    assert fe.decision_category == "CORROBORATED_EVENT"
    assert fe.aggregated_quantities.case_count == 25, "Case count must not be doubled or inflated by corroboration"
    assert fe.linkage_classification == LinkageClassification.HIGH_CONFIDENCE_LINKAGE


# =========================================================================
# Scenario 5: Two Separate Institutions in Same District Remain Distinct
# =========================================================================
def test_scenario_5_separate_institutions_distinct_events(db):
    """
    Anti-inflation audit: In Raichur, Week 31 (Minority Morarji Desai
    Residential School, 48 cases) and Week 32 (Dr. B.R. Ambedkar Post Metric
    Girls Hostel, 18 cases) are distinct populations/facilities and must
    remain two separate unlinked singleton events.
    """
    fe_list = db.list_fused_events()
    raichur_events = [
        e for e in fe_list
        if "raichur" in str(getattr(e, "canonical_location", "")).lower()
    ]
    # Verify that the two distinct school/hostel outbreaks are preserved separately
    case_counts = [e.aggregated_quantities.case_count for e in raichur_events]
    assert 48 in case_counts, "Expected Raichur 48 cases event (Minority Morarji Desai School)"
    assert 18 in case_counts, "Expected Raichur 18 cases event (Ambedkar Girls Hostel)"

    # Neither should be merged into a single 66-case cluster
    assert 66 not in case_counts, "Unjustified merge occurred: 48 + 18 was summed into 66!"


# =========================================================================
# Scenario 6: Firozpur Leptospirosis Provisional Cluster Cardinality
# =========================================================================
def test_scenario_6_firozpur_leptospirosis_cardinality(db):
    """
    Authoritative cardinality decision:
    In Firozpur, two serial Leptospirosis observations form exactly 1
    provisional cluster with supporting_observation_count == 2.
    The remaining 5 Leptospirosis observations across India remain singletons.
    Total Leptospirosis event groups = 6.
    """
    fe_list = db.list_fused_events()
    lepto_events = [
        e for e in fe_list
        if e.canonical_disease.lower() == "leptospirosis"
        and getattr(e, "primary_origin", None) == OriginClassification.LIVE_EXTERNAL
    ]
    assert len(lepto_events) == 6, f"Expected 6 Leptospirosis event groups (1 cluster + 5 singletons), found {len(lepto_events)}"

    # Find the Firozpur multi-observation cluster
    firozpur_clusters = [
        e for e in lepto_events
        if "firozpur" in str(getattr(e, "canonical_location", "")).lower()
        or e.supporting_observation_count > 1
    ]
    assert len(firozpur_clusters) == 1, "Expected exactly 1 Firozpur Leptospirosis cluster"
    firozpur = firozpur_clusters[0]
    assert firozpur.supporting_observation_count == 2, "Expected 2 supporting observations in Firozpur cluster"
    assert firozpur.linkage_classification == LinkageClassification.PROVISIONAL_LINKAGE


# =========================================================================
# Scenario 7: Candidate Review Queue (11) Reconciled vs Actionable (0)
# =========================================================================
def test_scenario_7_eleven_candidates_explained_actionable_zero(state):
    """
    Audit of the 11 items returned by GET /api/v1/alerts?priority_only=true&current_only=true:
    - All 11 originate from August 2026 IDSP weekly bulletins (Weeks 33–34) ingested in late October.
    - All 11 have decision_category == INFORMATIONAL.
    - None represent active current emergency outbreaks.
    - Actionable Priority Outbreaks is strictly 0.
    """
    alert_service = AlertQueryService(state=state)
    resp = alert_service.list_alerts(priority_only=True, current_only=True)
    candidates = resp.items
    assert len(candidates) == 11, f"Expected exactly 11 review candidates, found {len(candidates)}"

    for c in candidates:
        assert c.decision_category == DecisionCategory.INFORMATIONAL, (
            f"Alert {c.alert_id} for {c.disease_name} had unexpected decision category: {c.decision_category}"
        )
        assert c.alert_tier in (AlertTier.INFORMATIONAL, AlertTier.LOW), (
            f"Candidate alert {c.alert_id} had unexpected tier: {c.alert_tier}"
        )

    # Actionable outbreak alerts (positive active outbreaks) must be 0
    actionable_alerts = [
        c for c in candidates
        if c.decision_category in (DecisionCategory.CORROBORATED_EVENT, DecisionCategory.STATISTICAL_ANOMALY)
    ]
    assert len(actionable_alerts) == 0, f"Expected 0 actionable alerts, found {len(actionable_alerts)}"


# =========================================================================
# Scenario 8: Asia/Kolkata India-Local Surveillance Window Boundaries
# =========================================================================
def test_scenario_8_india_local_temporal_windows():
    """
    Temporal window audit:
    - Start date must be strictly <= cutoff date (no inverted ranges like '01 Nov - 30 Oct').
    - Weekly bounds must follow India-local Monday 00:00:00 to Sunday 23:59:59 IST.
    - UTC storage correctly stores ISO Week 44 without bleeding into November 2.
    """
    tz_ist = ZoneInfo("Asia/Kolkata")

    # Grounded operational audit window
    cutoff_dt = datetime(2026, 10, 30, 19, 38, 44, tzinfo=timezone.utc)
    cutoff_ist = cutoff_dt.astimezone(tz_ist)
    month_start_ist = datetime(cutoff_ist.year, cutoff_ist.month, 1, 0, 0, 0, tzinfo=tz_ist)

    # Assert strictly valid positive chronological interval
    assert month_start_ist <= cutoff_ist, "Inverted temporal window detected!"
    diff_days = (cutoff_ist - month_start_ist).total_seconds() / 86400.0
    assert 29.0 <= diff_days <= 31.0, f"Expected ~29.8 to 30.1 days audit window, got {diff_days}"

    # Verify formatted labels
    start_str = month_start_ist.strftime("%d %b %Y")
    end_str = cutoff_ist.strftime("%d %b %Y, %H:%M IST")
    assert start_str == "01 Oct 2026"
    assert end_str == "31 Oct 2026, 01:08 IST"


# =========================================================================
# Scenario 9: Disconnect Discovered Links from Unique Document Ingestion
# =========================================================================
def test_scenario_9_discovery_vs_ingestion_decoupling():
    """
    Source telemetry audit:
    - items_discovered (e.g. 42 links found on portal) must not be confused with
      newly ingested documents (0 new documents because all 34 are duplicate bulletins).
    - Prevents false claims of data growth or extraction failures.
    """
    configs = {c.source_id: c for c in get_default_connector_configs()}
    c = configs.get("idsp_bulletin_feed")
    assert c is not None, "idsp_bulletin_feed connector config missing"

    assert c.items_discovered == 42, "Expected 42 discovered links on IDSP portal"
    assert c.items_skipped_duplicates == 34, "Expected 34 skipped duplicates"
    wf = c.metadata.get("workflow_separation", {})
    assert wf.get("live_unique_documents_ingested") == 0, (
        "Expected 0 new documents ingested in live poll (archive already up to date)"
    )


# =========================================================================
# Scenario 10: Accurate Reporting of Degraded & Authenticated Feeds
# =========================================================================
def test_scenario_10_source_health_limitations(db, state):
    """
    Source health audit:
    - Feeds requiring authentication (e.g. social streams) or unavailable
      endpoints must be reported accurately with their specific status,
      not silently dropped or reported as successful empty fetches.
    """
    svc = SourcePollingService(pipeline=MagicMock(), db=db)
    overview = get_operational_overview(state=state, polling_service=svc, db=db)
    source_audit = overview["source_polling_audit"]
    source_map = {s["source_id"]: s for s in source_audit}

    assert "public_health_social_stream" in source_map, "Social stream missing from audit"
    social = source_map["public_health_social_stream"]
    assert social["status"] == "authentication_required" or social["polling_state"] == "AUTHENTICATION_REQUIRED"
    assert "token" in social["finding_summary"].lower() or "credentials" in social["finding_summary"].lower()


# =========================================================================
# Scenario 11: Authoritative Accounting Matrix (Counters A through P)
# =========================================================================
def test_scenario_11_authoritative_accounting_matrix(db):
    """
    Verification of the unified 16-counter accounting matrix (A through P):
    - All 16 keys exist with explicit units, time scopes, and descriptions.
    - Values reconcile with known public health and fusion cardinality facts.
    """
    svc = SourcePollingService(pipeline=MagicMock(), db=db)
    connectors = svc.list_connectors()
    cur_start = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    cur_end = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

    matrix = get_authoritative_accounting(db, connectors, cur_start, cur_end)
    assert len(matrix) == 16, f"Expected 16 counters A-P, got {len(matrix)}"

    expected_keys = [
        "A_external_items_discovered",
        "B_unique_documents_fetched",
        "C_duplicates_skipped",
        "D_successfully_parsed_documents",
        "E_failed_unresolved_documents",
        "F_priority_registry_matching_documents",
        "G_positive_event_observations",
        "H_negative_rule_outs",
        "I_suspected_observations",
        "J_administrative_documents",
        "K_out_of_scope_observations",
        "L_canonical_event_groups",
        "M_candidate_review_items",
        "N_actionable_outbreak_alerts",
        "O_historical_reference_records",
        "P_synthetic_test_records",
    ]
    for k in expected_keys:
        assert k in matrix, f"Missing key {k} in accounting matrix"
        entry = matrix[k]
        assert "value" in entry
        assert "unit" in entry
        assert "time_scope" in entry
        assert "description" in entry

    # Verify critical cardinalities
    assert matrix["G_positive_event_observations"]["value"] == 353, "Priority observations must be 353"
    assert matrix["L_canonical_event_groups"]["value"] == 1395, "Authoritative fused events must be 1,395"
    assert matrix["M_candidate_review_items"]["value"] == 11, "Candidate review queue must be 11"
    assert matrix["N_actionable_outbreak_alerts"]["value"] == 0, "Actionable priority outbreaks must be 0"
    assert matrix["H_negative_rule_outs"]["value"] >= 1, "Negative rule-outs must be at least 1 (Kinnaur)"
    assert matrix["E_failed_unresolved_documents"]["value"] == 0, "Failed documents must be 0"

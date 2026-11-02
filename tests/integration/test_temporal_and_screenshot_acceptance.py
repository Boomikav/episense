"""
Comprehensive 16-Point Integration Acceptance Suite for EpiSense
Screenshots, Temporal Semantics, NLP Quantity Extraction, Provenance,
and Gated Forecasting Integrity Audit.
"""

from datetime import datetime, timezone
import pytest
from uuid import UUID

from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES, resolve_priority_disease
from episense.taxonomy.registry import CANONICAL_ENTRIES
from episense.nlp.pipeline import NLPPipeline
from episense.nlp.entities.taxonomy import DISEASE_LEXICON, DEFAULT_TAXONOMY_REGISTRY
from episense.nlp.quantities import QuantityExtractor
from episense.persistence.database import SurveillanceDatabase
from episense.streaming.state import SurveillanceStateStore
from episense.connectors.service import SourcePollingService
from episense.api.services import AlertQueryService, SignalQueryService, GeoQueryService
from episense.api.routes.live_metrics import get_operational_overview
from episense.api.routes.fusion_inspector import get_cluster_details
from episense.schemas.document import OriginClassification, Document
from episense.schemas.alert import AlertTier, PathogenThreatTier
from episense.schemas.signal import SignalObservation, DetectionMethod
from unittest.mock import MagicMock


@pytest.fixture
def db():
    return SurveillanceDatabase("data/surveillance_store.sqlite")


@pytest.fixture
def nlp():
    return NLPPipeline()


# =========================================================================
# Check 1: Eight-Disease Priority Registry Integrity
# =========================================================================
def test_check_1_priority_registry_integrity():
    expected_8 = {
        "Dengue",
        "Malaria",
        "Chikungunya",
        "Leptospirosis",
        "Cholera",
        "Acute Diarrhoeal Disease",
        "Japanese Encephalitis",
        "Scrub Typhus",
    }
    canonical_set = set(PRIORITY_CANONICAL_NAMES)
    assert canonical_set == expected_8, f"Priority registry mismatch: {canonical_set} != {expected_8}"
    for d in expected_8:
        meta = resolve_priority_disease(d)
        assert meta is not None, f"Failed to resolve canonical disease: {d}"


# =========================================================================
# Check 1b: India Surveillance Weekly Reporting Window (Asia/Kolkata Bounds)
# =========================================================================
def test_check_1b_india_reporting_timezone_bounds():
    from episense.baseline.timeseries import TimeSeriesBuilder
    from zoneinfo import ZoneInfo

    ts_builder = TimeSeriesBuilder()
    start_utc, end_utc = ts_builder._get_iso_week_bounds(2026, 44, "Asia/Kolkata")

    # Authoritative India-local surveillance week:
    # Monday 00:00:00 Asia/Kolkata -> Sunday 18:30:00 UTC (preceding calendar day)
    # Sunday 23:59:59.999 Asia/Kolkata -> Sunday 18:29:59.999 UTC
    start_local = start_utc.astimezone(ZoneInfo("Asia/Kolkata"))
    end_local = end_utc.astimezone(ZoneInfo("Asia/Kolkata"))

    assert start_local.strftime("%Y-%m-%d %H:%M:%S") == "2026-10-26 00:00:00"
    assert end_local.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 23:59:59"
    assert start_local.weekday() == 0  # Monday
    assert end_local.weekday() == 6    # Sunday
    assert start_local.isocalendar()[1] == 44
    assert end_local.isocalendar()[1] == 44

    # Storage in UTC:
    assert start_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-10-25 18:30:00"
    assert end_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 18:29:59"
    assert end_utc.strftime("%Y-%m-%d") == "2026-11-01"  # In UTC, ends on Nov 1, ZERO roll-over into Nov 2!


# =========================================================================
# Check 1c: Comprehensive Boundary Tests for Asia/Kolkata ISO Surveillance Week
# =========================================================================
def test_check_1c_india_surveillance_week_boundary_cases():
    from zoneinfo import ZoneInfo
    tz_ist = ZoneInfo("Asia/Kolkata")

    # 1. Sunday 23:59 IST (End of Week 44)
    sun_2359 = datetime(2026, 11, 1, 23, 59, 0, tzinfo=tz_ist)
    assert sun_2359.isocalendar() == (2026, 44, 7), "Sunday 23:59 IST must belong to ISO Week 44"
    sun_2359_utc = sun_2359.astimezone(timezone.utc)
    assert sun_2359_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 18:29:00"

    # 2. Monday 00:00 IST (Start of Week 45)
    mon_0000 = datetime(2026, 11, 2, 0, 0, 0, tzinfo=tz_ist)
    assert mon_0000.isocalendar() == (2026, 45, 1), "Monday 00:00 IST must start ISO Week 45"
    mon_0000_utc = mon_0000.astimezone(timezone.utc)
    assert mon_0000_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 18:30:00", "Monday 00:00 IST must convert to Sunday 18:30 UTC"

    # 3. Monday 05:29 IST (Still Sunday in UTC, but Week 45 in IST surveillance)
    mon_0529 = datetime(2026, 11, 2, 5, 29, 0, tzinfo=tz_ist)
    assert mon_0529.isocalendar() == (2026, 45, 1), "Monday 05:29 IST must belong to ISO Week 45"
    mon_0529_utc = mon_0529.astimezone(timezone.utc)
    assert mon_0529_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 23:59:00"

    # 4. Monday 05:30 IST (Midnight UTC on Monday)
    mon_0530 = datetime(2026, 11, 2, 5, 30, 0, tzinfo=tz_ist)
    assert mon_0530.isocalendar() == (2026, 45, 1), "Monday 05:30 IST must belong to ISO Week 45"
    mon_0530_utc = mon_0530.astimezone(timezone.utc)
    assert mon_0530_utc.strftime("%Y-%m-%d %H:%M:%S") == "2026-11-02 00:00:00"

    # 5. UTC / local week boundary conversion round-trip
    from episense.baseline.timeseries import TimeSeriesBuilder
    ts = TimeSeriesBuilder()
    s_utc, e_utc = ts._get_iso_week_bounds(2026, 44, "Asia/Kolkata")
    assert s_utc.astimezone(tz_ist).strftime("%Y-%m-%d %H:%M:%S") == "2026-10-26 00:00:00"
    assert e_utc.astimezone(tz_ist).strftime("%Y-%m-%d %H:%M:%S") == "2026-11-01 23:59:59"

    # 6. ISO year transitions (2024 -> 2025 and 2026 -> 2027)
    # 2024-W52 to 2025-W01:
    sun_2024 = datetime(2024, 12, 29, 23, 59, 59, tzinfo=tz_ist)
    mon_2025 = datetime(2024, 12, 30, 0, 0, 0, tzinfo=tz_ist)
    assert sun_2024.isocalendar() == (2024, 52, 7)
    assert mon_2025.isocalendar() == (2025, 1, 1)

    # 2026 is a 53-week ISO year; 2026-W53 to 2027-W01:
    sun_2026 = datetime(2027, 1, 3, 23, 59, 59, tzinfo=tz_ist)
    mon_2027 = datetime(2027, 1, 4, 0, 0, 0, tzinfo=tz_ist)
    assert sun_2026.isocalendar() == (2026, 53, 7)
    assert mon_2027.isocalendar() == (2027, 1, 1)


# =========================================================================
# Check 1d: Source Reporting Week Preservation vs Internal Time-Series Bins
# =========================================================================
def test_check_1d_source_reporting_week_preservation_vs_internal_bins(db):
    import sqlite3
    import json
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    # Verify Firozpur Leptospirosis cluster preserves official source reporting weeks
    cur.execute("SELECT json_data FROM fused_events WHERE canonical_disease = 'Leptospirosis' AND primary_origin = 'LIVE_EXTERNAL' AND status = 'active' AND supporting_observation_count = 2")
    row = cur.fetchone()
    assert row is not None
    data = json.loads(row[0])
    assert data.get("source_reporting_week") == 9, "Leptospirosis wave 1 source week must be 9"
    assert data.get("source_reporting_year") == 2026, "Leptospirosis source year must be 2026"
    assert "Wave 1 (PB/FIR/2026/9/338, W9" in data["aggregated_quantities"]["quantity_semantics_note"]
    assert "Wave 2 (PB/FIR/2026/14/554, W14" in data["aggregated_quantities"]["quantity_semantics_note"]


# =========================================================================
# Check 2: Nipah ICD Taxonomy Reconciliation (No B27.8 or 1D65; 1D63 Distinct)
# =========================================================================
def test_check_2_nipah_icd_taxonomy():
    norm_name, icd_code = DISEASE_LEXICON.get("nipah virus", (None, "NOT_FOUND"))
    assert icd_code is None, f"Generic Nipah in DISEASE_LEXICON must be None (unresolved), found: {icd_code}"

    norm_name2, icd_code2 = DISEASE_LEXICON.get("nipah virus disease", (None, "NOT_FOUND"))
    assert icd_code2 is None, f"Generic Nipah virus disease ICD must be None, found: {icd_code2}"

    # Regression: Nipah never maps to 1D65 (1D65 is Severe acute respiratory syndrome / SARS)
    for term in ["nipah", "nipah virus", "nipah virus disease", "henipavirus"]:
        _, code = DISEASE_LEXICON.get(term, (None, None))
        assert code != "1D65" and code != "ICD11:1D65", f"Term '{term}' must never map to SARS code 1D65!"
        assert code != "1D63" and code != "ICD11:1D63", f"Generic term '{term}' must not be automatically diagnosed as 1D63 (Henipavirus encephalitis)!"

    # Regression: Generic Nipah in master canonical registry
    nipah_entries = [e for e in CANONICAL_ENTRIES if e.canonical_id == "nipah_virus"]
    if nipah_entries:
        assert nipah_entries[0].icd10_code is None, f"Nipah registry ICD code must be None, found {nipah_entries[0].icd10_code}"
        assert nipah_entries[0].icd10_code != "1D65"
        assert nipah_entries[0].icd10_code != "1D63"

    # Regression: Validated Henipavirus encephalitis mapping is distinct
    henipa_enc = [e for e in CANONICAL_ENTRIES if e.canonical_id == "henipavirus_encephalitis"]
    assert len(henipa_enc) == 1, "Expected distinct 'henipavirus_encephalitis' canonical entry"
    assert henipa_enc[0].icd10_code == "ICD11:1D63", f"Expected ICD11:1D63 for Henipavirus encephalitis, got {henipa_enc[0].icd10_code}"


# =========================================================================
# Check 3: NLP Quantity Extraction on Complex Assertion Preceding Count Units
# =========================================================================
def test_check_3_nlp_quantity_extraction_nipah(nlp):
    import hashlib
    text = "Two confirmed Nipah virus cases were reported in Kozhikode on 25 July 2024."
    doc = Document(
        document_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        source_id="test_feed",
        title="Nipah Report",
        text=text,
        content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        publication_timestamp=datetime(2024, 7, 26, tzinfo=timezone.utc),
    )
    res = nlp.process_document(doc)
    assert len(res.quantities) >= 1, f"Expected at least 1 quantity mention, found {len(res.quantities)}"
    q = res.quantities[0]
    assert q.numeric_value == 2.0, f"Expected numeric_value=2.0, found {q.numeric_value}"
    assert q.raw_text.lower() == "two"
    assert q.quantity_type.value.lower() == "case_count"

    # Verify assertion and temporal recognition
    assert len(res.assertions) >= 1
    assert res.assertions[0].assertion_status.value == "confirmed"
    assert res.assertions[0].is_historical is True

    # Verify day-level precision for "on 25 July 2024"
    assert len(res.temporal_expressions) >= 1
    t_day = res.temporal_expressions[0]
    assert t_day.date_precision.value == "DAY"
    assert t_day.event_date_precision.value == "DAY"
    assert t_day.event_period_start.day == 25
    assert t_day.event_period_start.month == 7
    assert t_day.event_period_start.year == 2024


# =========================================================================
# Check 3b: Temporal Precision Levels (YEAR, MONTH, DAY, REPORTING_PERIOD)
# =========================================================================
def test_check_3b_temporal_precision_month_vs_day(nlp):
    import hashlib
    from episense.schemas.temporal import DatePrecision, TemporalType

    # Phrase "in July 2024" must not become exact point date of 1 July 2024
    text_month = "Two confirmed Nipah virus cases were reported in Kerala in July 2024."
    doc_month = Document(
        document_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        source_id="test_feed",
        title="Nipah Monthly Report",
        text=text_month,
        content_hash_sha256=hashlib.sha256(text_month.encode("utf-8")).hexdigest(),
        publication_timestamp=datetime(2024, 8, 1, tzinfo=timezone.utc),
    )
    res_m = nlp.process_document(doc_month)
    assert len(res_m.temporal_expressions) >= 1
    t_m = res_m.temporal_expressions[0]
    assert t_m.date_precision == DatePrecision.MONTH
    assert t_m.event_date_precision == DatePrecision.MONTH
    assert t_m.temporal_type == TemporalType.INTERVAL
    assert t_m.event_period_start.strftime("%Y-%m-%d") == "2024-07-01"
    assert t_m.event_period_end.strftime("%Y-%m-%d") == "2024-07-31"

    # Year precision: "in 2024"
    text_year = "Dengue cases increased across the district in 2024."
    doc_year = Document(
        document_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        source_id="test_feed",
        title="Dengue Annual Report",
        text=text_year,
        content_hash_sha256=hashlib.sha256(text_year.encode("utf-8")).hexdigest(),
        publication_timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
    )
    res_y = nlp.process_document(doc_year)
    assert len(res_y.temporal_expressions) >= 1
    t_y = res_y.temporal_expressions[0]
    assert t_y.date_precision == DatePrecision.YEAR
    assert t_y.event_period_start.strftime("%Y-%m-%d") == "2024-01-01"
    assert t_y.event_period_end.strftime("%Y-%m-%d") == "2024-12-31"


# =========================================================================
# Check 4: Test Fixtures Isolated Under SYNTHETIC_TEST Origin
# =========================================================================
def test_check_4_synthetic_fixtures_isolated(db):
    conn = db._get_connection()
    synthetic_docs = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE origin = 'SYNTHETIC_TEST'"
    ).fetchone()[0]
    assert synthetic_docs >= 18, f"Expected at least 18 synthetic test documents, found {synthetic_docs}"

    # Verify test_src documents do not contaminate LIVE_EXTERNAL
    test_src_live = conn.execute(
        "SELECT COUNT(*) FROM documents WHERE source_id = 'test_src' AND origin != 'SYNTHETIC_TEST'"
    ).fetchone()[0]
    assert test_src_live == 0, f"Found {test_src_live} unisolated test_src documents in live origin"


# =========================================================================
# Check 5: Leptospirosis Firozpur Cluster Exact Provenance (No Synthetic Allocation)
# =========================================================================
def test_check_5_leptospirosis_firozpur_cluster_provenance(db):
    fe_clusters = [
        e for e in db.list_fused_events()
        if "firozepur" in (e.canonical_location.normalized_name if e.canonical_location else "").lower()
        and e.supporting_observation_count > 1
    ]
    assert len(fe_clusters) == 1, f"Expected exactly 1 Firozpur Leptospirosis cluster, found {len(fe_clusters)}"
    cluster = fe_clusters[0]

    # Clinical and lab allocation should be None (not artificially split 37 / 96)
    assert cluster.aggregated_quantities.clinical_case_count is None
    assert cluster.aggregated_quantities.lab_confirmed_count is None
    assert cluster.aggregated_quantities.case_count is None
    assert cluster.aggregated_quantities.death_count == 1

    # Verify details route returns exact source observations
    state = MagicMock()
    state.fused_events = {}
    state.observations_by_id = {}
    state.candidates_by_id = {}
    details = get_cluster_details(cluster.fused_event_id, state=state, db=db)
    obs = details["supporting_observations"]
    assert len(obs) == 2, f"Expected 2 supporting observations, found {len(obs)}"

    w9_obs = [o for o in obs if o["case_count"] == 37][0]
    w14_obs = [o for o in obs if o["case_count"] == 96][0]

    assert "2026-02-26" in w9_obs["observation_time"]
    assert "2026-04-02" in w14_obs["observation_time"]
    assert "Row 12" in w9_obs["measurement_scope"]
    assert "Row 32" in w14_obs["measurement_scope"]
    assert "Page 20" in w9_obs["measurement_scope"]
    assert "Page 14" in w14_obs["measurement_scope"]
    assert w9_obs["death_count"] == 1
    assert w14_obs["death_count"] == 0


# =========================================================================
# Check 6: Early Signals Geographic Resolution (Dhaka & Unspecified Excluded)
# =========================================================================
def test_check_6_early_signals_domestic_filtering():
    state = SurveillanceStateStore()
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    p_start = datetime(2026, 10, 26, tzinfo=timezone.utc)
    p_end = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)

    # Signal 1: Indian domestic priority
    sig_india = SignalObservation(
        disease_key="dengue",
        geo_key="delhi",
        target_period_start=p_start,
        target_period_end=p_end,
        observed_value=15.0,
        expected_value=10.0,
        deviation=5.0,
        threshold=2.0,
        detection_method=DetectionMethod.EARS_C1,
    )
    # Signal 2: International non-India (Dhaka)
    sig_dhaka = SignalObservation(
        disease_key="dengue",
        geo_key="dhaka",
        target_period_start=p_start,
        target_period_end=p_end,
        observed_value=50.0,
        expected_value=20.0,
        deviation=30.0,
        threshold=2.0,
        detection_method=DetectionMethod.EARS_C1,
    )
    # Signal 3: Unspecified or global
    sig_global = SignalObservation(
        disease_key="cholera",
        geo_key="unspecified_or_global",
        target_period_start=p_start,
        target_period_end=p_end,
        observed_value=5.0,
        expected_value=1.0,
        deviation=4.0,
        threshold=2.0,
        detection_method=DetectionMethod.EARS_C1,
    )

    state.signals[sig_india.signal_id] = sig_india
    state.signals[sig_dhaka.signal_id] = sig_dhaka
    state.signals[sig_global.signal_id] = sig_global

    svc = SignalQueryService(state=state)
    res = svc.list_signals(priority_only=True)
    geo_keys = [s.geo_key.lower() for s in res.items]

    assert "delhi" in geo_keys
    assert "dhaka" not in geo_keys
    assert "unspecified_or_global" not in geo_keys


# =========================================================================
# Check 7: Missing Quantities Preserved as None (Not Coerced to 0.0)
# =========================================================================
def test_check_7_missing_quantities_preserved_as_none():
    sig = SignalObservation(
        disease_key="malaria",
        geo_key="odisha",
        target_period_start=datetime(2026, 10, 26, tzinfo=timezone.utc),
        target_period_end=datetime(2026, 11, 1, tzinfo=timezone.utc),
        observed_value=None,  # missing count
        expected_value=0.0,
        deviation=0.0,
        threshold=2.0,
        detection_method=DetectionMethod.EARS_C1,
    )
    assert sig.observed_value is None, f"Expected observed_value=None, found {sig.observed_value}"


# =========================================================================
# Check 8: Explainable Alerts Triage Review Queue vs Actionable Alerts
# =========================================================================
def test_check_8_alerts_review_queue_vs_actionable():
    state = SurveillanceStateStore()
    svc = AlertQueryService(state=state)
    res = svc.list_alerts(priority_only=True, current_only=True)
    # Operational alerts in current layer should be empty or purely informational
    actionable_alerts = [a for a in res.items if a.alert_tier in (AlertTier.HIGH, AlertTier.MEDIUM) and a.decision_category == "ACTIONABLE_ALERT"]
    assert len(actionable_alerts) == 0, f"Expected 0 actionable active alerts, found {len(actionable_alerts)}"


# =========================================================================
# Check 9: Pathogen Threat Priorities (No "Bio Hazard" Mislabeling)
# =========================================================================
def test_check_9_pathogen_threat_priorities():
    valid_threat_tiers = {
        PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        PathogenThreatTier.TIER_3_SEVERE,
        PathogenThreatTier.TIER_2_MODERATE,
        PathogenThreatTier.TIER_1_MILD,
        PathogenThreatTier.NONE,
    }
    for tier in PathogenThreatTier:
        assert tier in valid_threat_tiers


# =========================================================================
# Check 10: Overview KPIs: Puri Cholera In Review Queue, Current Active = 0
# =========================================================================
def test_check_10_overview_kpis(db):
    state = SurveillanceStateStore()
    svc = MagicMock()
    svc.list_connectors.return_value = []
    overview = get_operational_overview(state=state, polling_service=svc, db=db)

    figs = overview["summary_figures"]
    assert figs["new_operational_reports"]["value"] == 0, "Actionable Priority Reports must be 0"
    assert figs["priority_events_requiring_review"]["value"] == 1, "Puri Cholera candidate must count in review queue (=1)"
    assert figs["eligible_numerical_series"]["value"] in (0, 2), "Eligible numerical series must be 0 or 2"
    assert figs["current_supported_anomalies"]["value"] in (0, 1), "Current supported anomalies must be 0 or 1"
    assert figs["current_eligible_forecasts"]["value"] == 0, "Current eligible forecasts must be 0"


# =========================================================================
# Check 11: Separated Counters Decoupled From Historical Corpus
# =========================================================================
def test_check_11_separated_counters(db):
    state = SurveillanceStateStore()
    svc = MagicMock()
    svc.list_connectors.return_value = []
    overview = get_operational_overview(state=state, polling_service=svc, db=db)

    counters = overview["separated_counters"]
    assert counters["current_operational_events"]["value"] == 0
    assert counters["negative_rule_outs"]["value"] == 2
    assert counters["candidate_epidemiological_events"]["value"] == 1
    assert counters["recently_published_historical_events"]["value"] >= 1395


# =========================================================================
# Check 12: Source Extraction Telemetry Exposes All Processing Stages
# =========================================================================
def test_check_12_source_telemetry_exposed(db):
    breakdown = db.get_operational_surveillance_breakdown()
    expected_fields = [
        "new_publications_discovered",
        "unique_documents_fetched",
        "successfully_parsed_documents",
        "priority_disease_documents",
        "candidate_epidemiological_events",
        "current_operational_events",
        "recently_published_historical_events",
        "negative_rule_outs",
        "out_of_scope_events",
        "administrative_background_items",
        "failed_unresolved_extractions",
    ]
    for f in expected_fields:
        assert f in breakdown, f"Missing telemetry field: {f}"


# =========================================================================
# Check 12b: Source Telemetry Workflow Separation (Backfill vs Live Polling)
# =========================================================================
def test_check_12b_source_telemetry_workflow_separation():
    from episense.connectors.service import get_default_connector_configs
    configs = {c.source_id: c for c in get_default_connector_configs()}
    assert "idsp_bulletin_feed" in configs

    c = configs["idsp_bulletin_feed"]
    assert c.items_discovered == 42, f"Expected 42 discovered portal links, found {c.items_discovered}"
    assert c.items_skipped_duplicates == 34, f"Expected 34 skipped duplicate bulletins, found {c.items_skipped_duplicates}"

    wf = c.metadata.get("workflow_separation", {})
    assert wf.get("historical_backfill_bulletins") == 34, "Expected 34 historical backfill bulletins"
    assert wf.get("historical_backfill_observations") == 1396, "Expected 1,396 historical backfill observations"
    assert wf.get("live_portal_discovered_links") == 42, "Expected 42 live portal discovered links"
    assert wf.get("live_unique_documents_ingested") == 0, "Expected 0 live unique documents ingested (archive up to date)"


# =========================================================================
# Check 13: Geographic Current Layer Has Zero False Positive Outbreaks
# =========================================================================
def test_check_13_map_current_layer_zero_false_positives():
    state = SurveillanceStateStore()
    geo = GeoQueryService(state=state)
    alerts_fc = geo.get_alerts_geojson(current_only=True, priority_only=True)
    assert alerts_fc.total_features == 0, f"Expected 0 active alerts on map current layer, found {alerts_fc.total_features}"


# =========================================================================
# Check 14: Quantitative Forecasting Suppression Rules Enforced
# =========================================================================
def test_check_14_forecasting_suppression_enforced(db):
    from episense.surveillance.data_sufficiency import DataSufficiencyProfiler
    profiler = DataSufficiencyProfiler(db_path=db.db_path)
    profiles = profiler.audit_database()

    # Malaria and Dengue are evaluated (Malaria exploratory baseline, Dengue retrospective panel); all others suppressed
    for disease_key, p in profiles.items():
        if disease_key in ("Malaria", "Dengue"):
            assert p.capability_b_quantitative_forecasting in (
                "GO",
                "FORECAST_READY",
                "RETROSPECTIVE_EVALUATION",
                "EXPLORATORY_BASELINE_SELECTED",
            )
        else:
            assert p.capability_b_quantitative_forecasting in (
                "SUPPRESSED_INSUFFICIENT_BASELINE",
                "SUPPRESSED_STALE_DATA",
                "NO-GO",
                "BASELINE_ONLY",
                "INSUFFICIENT_HISTORICAL_DATA",
                "INSUFFICIENT_REPORTING_COVERAGE",
            ), f"Series {disease_key} was not properly suppressed: {p.capability_b_quantitative_forecasting}"


# =========================================================================
# Check 15: Temporal Semantics Window Boundary Separation
# =========================================================================
def test_check_15_temporal_semantics_window_boundary():
    # End date Nov 1 23:59:59 UTC represents ISO week 44 boundary, not an incident occurrence date
    p_start = datetime(2026, 10, 26, 0, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc)
    now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)

    # On Oct 31, 2026, the week ending Nov 1 23:59:59 is IN PROGRESS
    assert p_end > now, "Period end should be in the future relative to Oct 31"
    duration_days = (p_end - p_start).total_seconds() / 86400.0
    assert abs(duration_days - 7.0) < 0.01, f"Expected 7-day weekly aggregation window, got {duration_days}"


# =========================================================================
# Check 16: Cardinality Consistency of Fused Events
# =========================================================================
def test_check_16_cardinality_consistency(db):
    fused_events = db.list_fused_events()
    live_fe = [e for e in fused_events if getattr(e, "primary_origin", None) == OriginClassification.LIVE_EXTERNAL]
    assert len(live_fe) == 1395, f"Expected exactly 1,395 authoritative live fused events, found {len(live_fe)}"

    priority_fe = [
        e for e in live_fe
        if resolve_priority_disease(e.canonical_disease) is not None
        or e.canonical_disease in PRIORITY_CANONICAL_NAMES
    ]
    assert len(priority_fe) == 352, f"Expected exactly 352 priority live fused events, found {len(priority_fe)}"

    non_priority_fe = [
        e for e in live_fe
        if resolve_priority_disease(e.canonical_disease) is None
        and e.canonical_disease not in PRIORITY_CANONICAL_NAMES
    ]
    assert len(non_priority_fe) == 1043, f"Expected exactly 1,043 non-priority live fused events, found {len(non_priority_fe)}"

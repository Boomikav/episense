"""
Comprehensive Audit and Verification Test Suite for EpiSense.
Verifies IDSP bulletin extraction, multi-page table handling, phantom column fixes,
temporal baseline alignment, ISO week year boundaries, and polling idempotency.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest

from episense.connectors.pdf_adapter import IDSPBulletinPDFAdapter, IDSPOutbreakRecord
from episense.nlp.temporal.extractor import RuleBasedTemporalExtractor
from episense.schemas.temporal import TemporalType
from episense.baseline.timeseries import TimeSeriesBuilder
from episense.evaluation.event_evaluator import EventEvaluator


class TestIDSPBulletinAudit:
    """Verifies all 29 records in the official IDSP bulletin and Page 18 fixes."""

    @pytest.fixture
    def bulletin_pdf_bytes(self):
        p = Path("data/raw/bulletins/idsp_2026_w1.pdf")
        if not p.exists():
            pytest.skip("IDSP bulletin PDF fixture not found")
        return p.read_bytes()

    def test_extract_all_29_records(self, bulletin_pdf_bytes):
        adapter = IDSPBulletinPDFAdapter()
        records = adapter.extract_records_from_pdf(bulletin_pdf_bytes)

        assert len(records) == 29, f"Expected exactly 29 records, found {len(records)}"
        valid_records = [r for r in records if r.is_valid]
        assert len(valid_records) == 29, f"Expected all 29 records to be valid, found {len(valid_records)}"

    def test_page_18_late_outbreak_records(self, bulletin_pdf_bytes):
        """Verifies phantom spacer cell fix for Bihar and Uttar Pradesh records on Page 18."""
        adapter = IDSPBulletinPDFAdapter()
        records = adapter.extract_records_from_pdf(bulletin_pdf_bytes)

        # Record 28: Bihar Measles
        r28 = [r for r in records if r.unique_id == "BH/PUR/2026/01/28"][0]
        assert r28.state == "Bihar"
        assert r28.district == "Purbi Champaran"
        assert r28.disease == "Measles"
        assert r28.cases == 5
        assert r28.deaths == 0
        assert r28.start_date == "03-12-2025"
        assert r28.is_valid is True

        # Record 29: UP Measles
        r29 = [r for r in records if r.unique_id == "UP/SAM/2026/01/29"][0]
        assert r29.state == "Uttar Pradesh"
        assert r29.district == "Sambhal"
        assert r29.disease == "Measles"
        assert r29.cases == 5
        assert r29.deaths == 0
        assert r29.start_date == "15-11-2025"
        assert r29.is_valid is True

    def test_text_dehyphenation_and_normalization(self, bulletin_pdf_bytes):
        """Verifies multi-word and syllabic repairs in real bulletin records."""
        adapter = IDSPBulletinPDFAdapter()
        records = adapter.extract_records_from_pdf(bulletin_pdf_bytes)

        # Check Maharashtra normalization in MH/JAL and MH/PAR
        mh_records = [r for r in records if r.unique_id in ("MH/JAL/2026/01/19", "MH/PAR/2026/01/20")]
        for r in mh_records:
            assert r.state == "Maharashtra", f"Failed Maharashtra normalization: {r.state}"

        # Check Tiruchirappalli normalization in TN/TIR
        tn_tir = [r for r in records if r.unique_id == "TN/TIR/2026/01/26"][0]
        assert tn_tir.district == "Tiruchirappalli", f"Failed Tiruchirappalli normalization: {tn_tir.district}"

        # Check Acute Gastroenteritis normalization in KL/ERN
        kl_ern = [r for r in records if r.unique_id == "KL/ERN/2026/01/11"][0]
        assert kl_ern.disease == "Acute Gastroenteritis", f"Failed Gastroenteritis normalization: {kl_ern.disease}"


class TestTemporalAlignmentAndISOWeek:
    """Verifies numeric date extraction and ISO week year boundary handling."""

    def test_numeric_date_pattern_extraction(self):
        extractor = RuleBasedTemporalExtractor()
        ref_dt = datetime(2026, 1, 15, tzinfo=timezone.utc)

        # Indian DD-MM-YYYY format
        text = "Date of start of outbreak: 30-12-2025 | Reported on 01-01-2026."
        exprs = extractor.extract(text, reference_date=ref_dt)

        assert len(exprs) == 2
        e1, e2 = exprs[0], exprs[1]

        assert e1.original_expression == "30-12-2025"
        assert e1.temporal_type == TemporalType.POINT
        assert e1.normalized_start == datetime(2025, 12, 30, 0, 0, tzinfo=timezone.utc)

        assert e2.original_expression == "01-01-2026"
        assert e2.temporal_type == TemporalType.POINT
        assert e2.normalized_start == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)

    def test_iso_week_year_boundary_2025_2026(self):
        """
        Verifies that 2025-12-30 maps to ISO Week 1 of 2026 (2025-12-29 to 2026-01-04),
        NOT ISO Week 1 of 2025 (2024-12-30 to 2025-01-05).
        """
        ts = TimeSeriesBuilder()

        # 2025-12-30 (Tuesday)
        dt_2025_12_30 = datetime(2025, 12, 30, tzinfo=timezone.utc)
        iso_year, iso_week, iso_day = dt_2025_12_30.isocalendar()
        assert iso_year == 2026
        assert iso_week == 1
        assert iso_day == 2

        bounds_start, bounds_end = ts._get_iso_week_bounds(iso_year, iso_week)
        assert bounds_start == datetime(2025, 12, 29, 0, 0, 0, tzinfo=timezone.utc)
        assert bounds_end == datetime(2026, 1, 4, 23, 59, 59, tzinfo=timezone.utc)
        assert bounds_start <= dt_2025_12_30 <= bounds_end

        # Historical comparison window: ISO Week 1 of 2025
        hist_start, hist_end = ts._get_iso_week_bounds(2025, 1)
        assert hist_start == datetime(2024, 12, 30, 0, 0, 0, tzinfo=timezone.utc)
        assert hist_end == datetime(2025, 1, 5, 23, 59, 59, tzinfo=timezone.utc)


class TestEventBenchmarkDeterministic:
    """Verifies that all 14 scenarios in the event benchmark evaluate deterministically."""

    def test_run_event_benchmark(self):
        evaluator = EventEvaluator()
        summary = evaluator.evaluate()

        assert summary.total_scenarios_evaluated == 14
        # Independent outbreaks (excluding duplicates)
        assert summary.outbreak_detection_metrics.tp == 4
        assert summary.outbreak_detection_metrics.fp == 0
        assert summary.outbreak_detection_metrics.fn == 0
        assert summary.outbreak_detection_metrics.precision == 1.0
        assert summary.outbreak_detection_metrics.recall == 1.0
        assert summary.outbreak_detection_metrics.f1 == 1.0
        assert summary.false_alert_rate == 0.0
        assert summary.preparedness_suppression_rate == 1.0
        assert summary.negation_suppression_rate == 1.0
        assert summary.historical_suppression_rate == 1.0
        assert summary.duplicate_fusion_accuracy == 1.0

    def test_run_adversarial_v2_event_benchmark(self):
        """Verifies expanded 24-scenario adversarial benchmark."""
        evaluator = EventEvaluator(benchmark_path="data/benchmarks/event_benchmark/event_ground_truth_v2_adversarial.json")
        summary = evaluator.evaluate()

        assert summary.total_scenarios_evaluated == 24
        assert summary.outbreak_detection_metrics.tp == 7
        assert summary.outbreak_detection_metrics.fp == 0
        assert summary.outbreak_detection_metrics.fn == 0
        assert summary.outbreak_detection_metrics.precision == 1.0
        assert summary.outbreak_detection_metrics.recall == 1.0
        assert summary.outbreak_detection_metrics.f1 == 1.0
        assert summary.false_alert_rate == 0.0
        assert summary.preparedness_suppression_rate == 1.0
        assert summary.negation_suppression_rate == 1.0
        assert summary.historical_suppression_rate == 1.0
        assert summary.duplicate_fusion_accuracy == 1.0


class TestFacultyReviewRemediationVerification:
    """Verifies all specific issues raised during faculty review."""

    def test_idsp_case_count_negation_safeguard(self):
        """No. of Cases in IDSP bulletin header must never be treated as clinical negation."""
        from uuid import uuid4
        from episense.nlp.assertion.analyzer import ContextualAssertionAnalyzer
        from episense.schemas.assertion import AssertionStatus
        from episense.schemas.entity import Entity, EntityType

        analyzer = ContextualAssertionAnalyzer()
        text = "State: Kerala | District: Ernakulam | Disease/Illness: Acute Gastroenteritis | No. of Cases: 28 | No. of Deaths: 0 | Date: 08-01-2024"
        ent = Entity(
            entity_id=uuid4(),
            document_id=uuid4(),
            text_span="Acute Gastroenteritis",
            start_char=text.find("Acute Gastroenteritis"),
            end_char=text.find("Acute Gastroenteritis") + len("Acute Gastroenteritis"),
            entity_type=EntityType.DISEASE,
            extraction_confidence=0.95,
        )
        assertions = analyzer.analyze(text, [ent])
        assert len(assertions) == 1
        assert assertions[0].is_negated is False
        assert assertions[0].assertion_status == AssertionStatus.CONFIRMED

    def test_distinct_district_spatial_boundary_no_false_merge(self):
        """Distinct districts in the same state (Ernakulam vs Palakkad) must never merge."""
        from uuid import uuid4
        from episense.schemas.location import Location, GeographicLevel
        from episense.schemas.nlp import ResolvedLocation, ResolutionState
        from episense.fusion.geo_linker import GeographicLinker

        linker = GeographicLinker()
        loc_ernakulam = ResolvedLocation(
            raw_text="Ernakulam",
            start_char=0,
            end_char=9,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Ernakulam",
                normalized_name="Ernakulam",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
                gazetteer_id="GeoNames:1272304",
            ),
        )
        loc_palakkad = ResolvedLocation(
            raw_text="Palakkad",
            start_char=0,
            end_char=8,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Palakkad",
                normalized_name="Palakkad",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
                gazetteer_id="GeoNames:1261807",
            ),
        )
        is_compat, score, canon, hier, rationale = linker.evaluate_compatibility(loc_ernakulam, loc_palakkad)
        assert is_compat is False
        assert score == 0.0
        assert "Conflicting locations" in rationale

    def test_policy_target_year_suppression(self):
        """Future policy target years like 'achieved by 2030' must not extract as contemporary event dates."""
        extractor = RuleBasedTemporalExtractor()
        ref_dt = datetime(2026, 10, 24, tzinfo=timezone.utc)
        text = "Working together to build back a better world where the Global Goals remain the guiding plan to be achieved by 2030."
        results = extractor.extract(text, ref_dt)
        for r in results:
            assert r.normalized_start.year <= 2026

    def test_insufficient_baseline_signal_gating_and_score_suppression(self):
        """Signals with insufficient baseline history must set standardized_score to None and method to suppressed."""
        from uuid import uuid4
        from episense.anomaly.detector import SignalDetector
        from episense.schemas.signal import BaselineEstimate, BaselineReliability, EpidemiologicalTimeBin, DetectionMethod, SignalLevel

        detector = SignalDetector()
        baseline = BaselineEstimate(
            baseline_id=uuid4(),
            disease_key="cholera",
            geo_key="puri",
            target_period_start=datetime(2026, 1, 4, tzinfo=timezone.utc),
            target_period_end=datetime(2026, 1, 10, tzinfo=timezone.utc),
            baseline_window_weeks=7,
            baseline_count=0.0,
            baseline_mean=0.0,
            baseline_median=0.0,
            baseline_std=0.0,
            baseline_variance=0.0,
            dispersion_metric=0.0,
            number_of_historical_bins=0,
            number_of_nonzero_bins=0,
            reliability_status=BaselineReliability.INSUFFICIENT_HISTORY,
            rationale="No historical observations available.",
        )
        target = EpidemiologicalTimeBin(
            disease_key="cholera",
            geo_key="puri",
            period_start=datetime(2026, 1, 4, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 10, tzinfo=timezone.utc),
            iso_year=2026,
            iso_week=1,
            observed_case_count=12,
            fused_event_count=1,
            independent_source_count=1,
        )
        signal = detector.detect_signal([], target, baseline, value_type="cases")
        assert signal.signal_level == SignalLevel.NO_SIGNAL
        assert signal.standardized_score is None
        assert signal.detection_method == DetectionMethod.SUPPRESSED_INSUFFICIENT_BASELINE
        assert signal.is_downgraded is True

    def test_future_dates_and_epoch_dates_quarantine(self):
        """Quarantine extreme future dates (> 2026) and Unix epoch (< 2000) from event candidates."""
        from uuid import uuid4
        from episense.events.builder import EventCandidateBuilder
        from episense.schemas.nlp import NLPOutput, ContextAssociation
        from episense.schemas.entity import Entity, EntityType
        from episense.schemas.temporal import TemporalExpression, TemporalType

        builder = EventCandidateBuilder()
        doc_id = uuid4()
        now = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc)

        # Candidate with future temporal expression (2030)
        t_future = TemporalExpression(
            original_expression="target 2030",
            normalized_start=datetime(2030, 1, 1, tzinfo=timezone.utc),
            normalized_end=datetime(2030, 12, 31, tzinfo=timezone.utc),
            start_char=0,
            end_char=11,
            temporal_type=TemporalType.INTERVAL,
            confidence=0.9,
        )
        ent = Entity(
            entity_id=uuid4(),
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span="Malaria",
            start_char=20,
            end_char=27,
            extraction_confidence=0.9,
        )
        assoc = ContextAssociation(
            sentence_index=0,
            start_char=0,
            end_char=50,
            primary_disease=ent,
            temporal=t_future,
        )
        nlp_out = NLPOutput(
            document_id=doc_id,
            entities=[ent],
            temporal_expressions=[t_future],
            context_associations=[assoc],
        )
        cands = builder.build_candidates(nlp_out, publication_time=now)
        assert len(cands) == 1
        cand = cands[0]
        # Must be quarantined to publication time, NOT year 2030
        assert cand.observation.event_time.normalized_start.year <= 2026
        assert cand.observation.event_time.normalized_start == now

    def test_historical_live_provenance_separation(self):
        """Historical corpus documents must never be classified as live external."""
        from episense.persistence.database import SurveillanceDatabase
        db = SurveillanceDatabase()
        live_docs = db.list_documents(origin="LIVE_EXTERNAL", limit=None)
        hist_docs = db.list_documents(origin="HISTORICAL_CORPUS", limit=None)
        assert len(live_docs) >= 100
        assert len(hist_docs) >= 100
        live_ids = {d.document_id for d in live_docs}
        hist_ids = {d.document_id for d in hist_docs}
        assert live_ids.isdisjoint(hist_ids), "Live and Historical document sets overlap!"

    def test_duplicate_and_syndicated_reports_anti_inflation(self):
        """Syndicated reports with repeated counts must not sum-inflate cases in quantity aggregator."""
        from uuid import uuid4
        from episense.fusion.quantities import QuantityAggregator
        from episense.schemas.event import EventObservation, EpidemiologicalQuantities
        from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel

        agg = QuantityAggregator()
        doc1 = uuid4()
        doc2 = uuid4()
        doc3 = uuid4()
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        ass = Assertion(assertion_status=AssertionStatus.CONFIRMED, certainty=CertaintyLevel.DEFINITE, confidence=1.0)

        obs1 = EventObservation(
            observation_id=uuid4(),
            document_id=doc1,
            source_id="reuters_wire",
            canonical_disease="Malaria",
            raw_disease_span="Malaria",
            assertion=ass,
            publication_time=now,
            quantities=EpidemiologicalQuantities(case_count=15, death_count=2),
            extraction_confidence=0.9,
            observation_confidence=0.9,
        )
        obs2 = EventObservation(
            observation_id=uuid4(),
            document_id=doc2,
            source_id="ap_syndicate",
            canonical_disease="Malaria",
            raw_disease_span="Malaria",
            assertion=ass,
            publication_time=now,
            quantities=EpidemiologicalQuantities(case_count=15, death_count=2),
            extraction_confidence=0.9,
            observation_confidence=0.9,
        )
        obs3 = EventObservation(
            observation_id=uuid4(),
            document_id=doc3,
            source_id="local_daily",
            canonical_disease="Malaria",
            raw_disease_span="Malaria",
            assertion=ass,
            publication_time=now,
            quantities=EpidemiologicalQuantities(case_count=15, death_count=2),
            extraction_confidence=0.9,
            observation_confidence=0.9,
        )

        res, has_conflicts, summary = agg.aggregate([obs1, obs2, obs3])
        assert res.case_count == 15, f"Expected 15 cases (anti-inflation), got {res.case_count}"
        assert res.death_count == 2, f"Expected 2 deaths, got {res.death_count}"
        assert has_conflicts is False

    def test_backend_frontend_consistent_schema_fields(self):
        """Signal and Alert schemas must expose fields consistent with frontend expectations."""
        from episense.schemas.signal import SignalObservation, DetectionMethod, SignalLevel, BaselineReliability
        from episense.schemas.alert import EpidemiologicalAlert, AlertTier, PathogenThreatTier, RiskScoreBreakdown
        from uuid import uuid4

        sig = SignalObservation(
            signal_id=uuid4(),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            target_period_start=datetime(2026, 10, 19, tzinfo=timezone.utc),
            target_period_end=datetime(2026, 10, 25, tzinfo=timezone.utc),
            observed_value=1.0,
            expected_value=1.25,
            deviation=-0.25,
            standardized_score=-0.5,
            threshold=2.0,
            detection_method=DetectionMethod.EARS_C1,
            signal_level=SignalLevel.NO_SIGNAL,
            reliability_status=BaselineReliability.STABLE_BASELINE,
            explainable_rationale="Test rationale",
        )
        sig_dict = sig.model_dump()
        assert "signal_id" in sig_dict
        assert "standardized_score" in sig_dict
        assert "reliability_status" in sig_dict
        assert "detection_method" in sig_dict

        suppressed_sig = SignalObservation(
            signal_id=uuid4(),
            disease_key="cholera",
            geo_key="puri",
            target_period_start=datetime(2026, 10, 19, tzinfo=timezone.utc),
            target_period_end=datetime(2026, 10, 25, tzinfo=timezone.utc),
            observed_value=1.0,
            expected_value=0.0,
            deviation=1.0,
            standardized_score=None,
            threshold=2.0,
            detection_method=DetectionMethod.SUPPRESSED_INSUFFICIENT_BASELINE,
            signal_level=SignalLevel.NO_SIGNAL,
            reliability_status=BaselineReliability.INSUFFICIENT_HISTORY,
            explainable_rationale="Suppressed rationale",
        )
        assert suppressed_sig.standardized_score is None
        assert suppressed_sig.detection_method.value == "suppressed_insufficient_baseline"



"""
Comprehensive Unit Test Suite for EpiSense Phase 8:
Statistical Baselines & Early Signal Detection Engine.
Tests:
- Weekly TimeBin aggregation & anti-inflation invariants
- Duplicate FusedEvent protection
- Case and death count aggregation
- Conflicting quantity preservation
- Historical event segregation and event date precedence
- Missing period and zero count handling
- Historical baseline calculation (mean, median, variance, std, dispersion)
- Baseline reliability states (INSUFFICIENT_HISTORY, SPARSE_HISTORY, HIGH_VARIANCE, STABLE_BASELINE)
- EARS C1, C2 (with 2-week guard band), and C3 persistence accumulation
- Bounded Farrington-style quasi-Poisson detection & Anscombe 2/3 transform
- SignalDetector classification, explainability, single-source downgrade, and provenance
- Disease and geographic stratification
- 100% deterministic reproducibility
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID, uuid4
import pytest

from episense.schemas.event import (
    FusedEvent,
    EpidemiologicalQuantities,
    EvidenceReference,
    SourceGroup,
)
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.signal import (
    EpidemiologicalTimeBin,
    BaselineEstimate,
    BaselineReliability,
    SignalLevel,
    DetectionMethod,
    SignalObservation,
)
from episense.baseline.timeseries import TimeSeriesBuilder
from episense.baseline.reliability import BaselineReliabilityTracker
from episense.baseline.engine import BaselineEngine
from episense.anomaly.ears import EARSDetector, EARSResult
from episense.anomaly.farrington import BoundedFarringtonDetector, FarringtonResult
from episense.anomaly.detector import SignalDetector
from episense.anomaly.batch import SignalBatchRunner


def make_fused_event(
    disease: str = "Nipah virus disease",
    location_name: str = "Kozhikode",
    geo_level: GeographicLevel = GeographicLevel.DISTRICT,
    event_time: datetime = datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc),
    cases: int = 2,
    deaths: int = 1,
    obs_count: int = 3,
    sources: List[str] = None,
    assertion: AssertionStatus = AssertionStatus.CONFIRMED,
    has_conflicts: bool = False,
    reported_values: dict = None,
    is_estimated: bool = False,
    event_id: UUID = None,
) -> FusedEvent:
    """Helper to construct realistic FusedEvent records for unit tests."""
    source_names = sources or ["who_don", "promed_mail"]
    source_groups = [
        SourceGroup(source_id=s, independence_group=s.upper()) for s in source_names
    ]
    quantities = EpidemiologicalQuantities(
        case_count=cases,
        death_count=deaths,
        is_conflicting=has_conflicts,
        reported_values=reported_values or ({"cases": [float(cases)]} if cases is not None else {}),
    )
    loc = Location(
        original_text=location_name,
        normalized_name=location_name,
        geographic_level=geo_level,
        parent_location="India",
    )
    ev_refs = [
        EvidenceReference(
            document_id=uuid4(),
            source_id=source_names[0],
            start_char=10,
            end_char=25,
            span_text=f"{cases} confirmed cases",
            extraction_method="rule_based",
            attribute_role="case_count",
        )
    ]
    return FusedEvent(
        fused_event_id=event_id or uuid4(),
        canonical_disease=disease,
        canonical_location=loc,
        event_window_start=event_time,
        event_window_end=event_time,
        is_event_time_estimated=is_estimated,
        assertion_status=assertion,
        certainty=CertaintyLevel.PROBABLE,
        aggregated_quantities=quantities,
        supporting_observation_count=obs_count,
        independent_sources=source_groups,
        independent_source_count=len(source_groups),
        evidence_references=ev_refs,
        has_conflicts=has_conflicts,
    )


class TestStatisticalBaselines:
    """Comprehensive test suite for Phase 8 statistical baselines & early signal detection."""

    # 1. Weekly TimeBin ISO calendar bounds
    def test_timebin_iso_week_aggregation(self):
        builder = TimeSeriesBuilder()
        # 2024-07-15 is Monday of 2024-W29
        t = datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc)
        fe = make_fused_event(event_time=t)
        bins = builder.build_weekly_bins([fe])

        assert len(bins) == 1
        b = bins[0]
        assert b.iso_year == 2024
        assert b.iso_week == 29
        assert b.period_start == datetime(2024, 7, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert b.period_end == datetime(2024, 7, 21, 23, 59, 59, tzinfo=timezone.utc)
        assert b.fused_event_count == 1

    # 2. Duplicate FusedEvent protection (seen_fused_ids)
    def test_duplicate_fused_event_protection(self):
        builder = TimeSeriesBuilder()
        fe_id = uuid4()
        fe = make_fused_event(event_id=fe_id, cases=5)
        # Pass identical FusedEvent twice
        bins = builder.build_weekly_bins([fe, fe])

        assert len(bins) == 1
        assert bins[0].fused_event_count == 1
        assert bins[0].observed_case_count == 5

    # 3. Anti-inflation quantity preservation
    def test_anti_inflation_quantity_preservation(self):
        builder = TimeSeriesBuilder()
        # Outbreak reported across 10 syndicated articles with canonical case_count = 2
        fe = make_fused_event(cases=2, obs_count=10)
        bins = builder.build_weekly_bins([fe])

        assert len(bins) == 1
        # Crucial invariant: case count is 2, NOT 2 * 10 = 20
        assert bins[0].observed_case_count == 2
        assert bins[0].supporting_observation_count == 10

    # 4. Death count aggregation
    def test_death_count_aggregation(self):
        builder = TimeSeriesBuilder()
        t1 = datetime(2024, 7, 15, tzinfo=timezone.utc)
        t2 = datetime(2024, 7, 17, tzinfo=timezone.utc)
        fe1 = make_fused_event(event_time=t1, cases=3, deaths=1)
        fe2 = make_fused_event(event_time=t2, cases=4, deaths=2)
        bins = builder.build_weekly_bins([fe1, fe2])

        assert len(bins) == 1
        assert bins[0].observed_case_count == 7
        assert bins[0].observed_death_count == 3
        assert bins[0].fused_event_count == 2

    # 5. Conflicting quantity handling in bins
    def test_conflicting_quantity_handling_in_bins(self):
        builder = TimeSeriesBuilder()
        fe = make_fused_event(
            cases=5,
            has_conflicts=True,
            reported_values={"cases": [2.0, 5.0]},
        )
        bins = builder.build_weekly_bins([fe])

        assert len(bins) == 1
        assert bins[0].has_conflicts is True
        assert "cases" in bins[0].conflicting_quantities
        assert bins[0].conflicting_quantities["cases"] == [2.0, 5.0]

    # 6. Historical event exclusion from contemporary window
    def test_historical_event_exclusion_from_current_window(self):
        builder = TimeSeriesBuilder()
        # Generic historical statement published in 2024 with estimated time
        pub_t = datetime(2024, 7, 15, tzinfo=timezone.utc)
        fe_hist = make_fused_event(
            event_time=pub_t,
            assertion=AssertionStatus.HISTORICAL,
            is_estimated=True,
            cases=10,
        )
        # Active confirmed event in 2024
        fe_active = make_fused_event(
            event_time=pub_t,
            assertion=AssertionStatus.CONFIRMED,
            is_estimated=False,
            cases=3,
        )
        bins = builder.build_weekly_bins([fe_hist, fe_active])

        # fe_hist must NOT contaminate fe_active's 2024-W29 bin count
        active_bin = next(b for b in bins if b.iso_year == 2024 and b.iso_week == 29)
        assert active_bin.observed_case_count == 3  # Not 3 + 10 = 13!
        assert active_bin.fused_event_count == 1

        # fe_hist is segregated into historical reference bin (year 1970)
        hist_bin = next(b for b in bins if b.iso_year == 1970)
        assert hist_bin.completeness_status == "historical_background"

    # 7. Event date precedence over publication date
    def test_event_date_precedence_over_pub_date(self):
        builder = TimeSeriesBuilder()
        # Event explicitly occurred in May 2024 (W20) reported in July 2024
        event_t = datetime(2024, 5, 14, tzinfo=timezone.utc)
        fe = make_fused_event(event_time=event_t, cases=4, is_estimated=False)
        bins = builder.build_weekly_bins([fe])

        assert len(bins) == 1
        assert bins[0].iso_year == 2024
        assert bins[0].iso_week == 20  # May, not July
        assert bins[0].observed_case_count == 4

    # 8. Missing period handling
    def test_missing_period_handling(self):
        tracker = BaselineReliabilityTracker(min_sample_size=4)
        # Two observations separated by 4 weeks (weeks 10 and 14)
        t10 = datetime(2024, 3, 4, tzinfo=timezone.utc)
        t14 = datetime(2024, 4, 1, tzinfo=timezone.utc)
        b1 = EpidemiologicalTimeBin(
            disease_key="dengue", geo_key="delhi", period_start=t10, period_end=t10 + timedelta(days=6),
            iso_year=2024, iso_week=10, observed_case_count=5, fused_event_count=1,
        )
        b_target = EpidemiologicalTimeBin(
            disease_key="dengue", geo_key="delhi", period_start=t14, period_end=t14 + timedelta(days=6),
            iso_year=2024, iso_week=14, observed_case_count=8, fused_event_count=1,
        )
        # Historical bins list only contains the 1 observed week (does NOT fabricate fake zeros for missing weeks)
        rel, rat = tracker.evaluate_reliability([b1], b_target)
        assert rel == BaselineReliability.INSUFFICIENT_HISTORY
        assert "1 historical bins available" in rat

    # 9. Zero count behavior
    def test_zero_count_behavior(self):
        engine = BaselineEngine()
        t = datetime(2024, 7, 15, tzinfo=timezone.utc)
        target = EpidemiologicalTimeBin(
            disease_key="cholera", geo_key="odisha", period_start=t, period_end=t + timedelta(days=6),
            iso_year=2024, iso_week=29, observed_case_count=0, fused_event_count=0,
        )
        # Zero-history evaluation does not crash with zero division
        base = engine.compute_baseline([], target)
        assert base.baseline_mean == 0.0
        assert base.baseline_std == 0.0
        assert base.reliability_status == BaselineReliability.INSUFFICIENT_HISTORY

    # 10. Baseline mean calculation
    def test_baseline_mean_calculation(self):
        engine = BaselineEngine()
        bins = []
        for i, count in enumerate([10, 20, 30]):
            t = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=i)
            bins.append(EpidemiologicalTimeBin(
                disease_key="measles", geo_key="mumbai", period_start=t, period_end=t + timedelta(days=6),
                iso_year=2024, iso_week=i + 1, observed_case_count=count, fused_event_count=1,
            ))
        t_target = datetime(2024, 1, 22, tzinfo=timezone.utc)
        target = EpidemiologicalTimeBin(
            disease_key="measles", geo_key="mumbai", period_start=t_target, period_end=t_target + timedelta(days=6),
            iso_year=2024, iso_week=4, observed_case_count=25, fused_event_count=1,
        )
        base = engine.compute_baseline(bins, target)
        assert base.baseline_mean == 20.0
        assert base.number_of_historical_bins == 3

    # 11. Baseline median calculation
    def test_baseline_median_calculation(self):
        engine = BaselineEngine()
        # Odd number of counts: [2, 4, 100] -> median is 4 (resistant to outlier 100)
        bins = []
        for i, count in enumerate([2, 4, 100]):
            t = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=i)
            bins.append(EpidemiologicalTimeBin(
                disease_key="nipah", geo_key="kozhikode", period_start=t, period_end=t + timedelta(days=6),
                iso_year=2024, iso_week=i + 1, observed_case_count=count, fused_event_count=1,
            ))
        t_target = datetime(2024, 1, 22, tzinfo=timezone.utc)
        target = EpidemiologicalTimeBin(
            disease_key="nipah", geo_key="kozhikode", period_start=t_target, period_end=t_target + timedelta(days=6),
            iso_year=2024, iso_week=4, observed_case_count=5, fused_event_count=1,
        )
        base = engine.compute_baseline(bins, target)
        assert base.baseline_median == 4.0
        assert base.baseline_mean == pytest.approx(35.333, abs=1e-2)

    # 12. Dispersion and standard deviation calculation
    def test_dispersion_calculation(self):
        engine = BaselineEngine()
        # Sample: [10, 12, 14] -> mean=12, var=((10-12)^2 + 0 + (14-12)^2)/2 = 8/2 = 4.0, std=2.0
        bins = []
        for i, count in enumerate([10, 12, 14]):
            t = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=i)
            bins.append(EpidemiologicalTimeBin(
                disease_key="dengue", geo_key="kerala", period_start=t, period_end=t + timedelta(days=6),
                iso_year=2024, iso_week=i + 1, observed_case_count=count, fused_event_count=1,
            ))
        t_target = datetime(2024, 1, 22, tzinfo=timezone.utc)
        target = EpidemiologicalTimeBin(
            disease_key="dengue", geo_key="kerala", period_start=t_target, period_end=t_target + timedelta(days=6),
            iso_year=2024, iso_week=4, observed_case_count=15, fused_event_count=1,
        )
        base = engine.compute_baseline(bins, target)
        assert base.baseline_std == 2.0
        assert base.baseline_variance == 4.0
        assert base.dispersion_metric == pytest.approx(4.0 / 12.0, abs=1e-3)

    # 13. Insufficient history reliability state
    def test_insufficient_history_reliability_state(self):
        tracker = BaselineReliabilityTracker(min_sample_size=3)
        t = datetime(2024, 1, 1, tzinfo=timezone.utc)
        b = EpidemiologicalTimeBin(
            disease_key="rabies", geo_key="delhi", period_start=t, period_end=t + timedelta(days=6),
            iso_year=2024, iso_week=1, observed_case_count=1, fused_event_count=1,
        )
        rel, rat = tracker.evaluate_reliability([b], b)
        assert rel == BaselineReliability.INSUFFICIENT_HISTORY

    # 14. Sparse history reliability state
    def test_sparse_history_reliability_state(self):
        tracker = BaselineReliabilityTracker(min_sample_size=3)
        # 3 bins but only 1 non-zero count: [0, 0, 5]
        bins = []
        for i, count in enumerate([0, 0, 5]):
            t = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=i)
            bins.append(EpidemiologicalTimeBin(
                disease_key="rabies", geo_key="delhi", period_start=t, period_end=t + timedelta(days=6),
                iso_year=2024, iso_week=i + 1, observed_case_count=count, fused_event_count=count,
            ))
        target = bins[-1]
        rel, _ = tracker.evaluate_reliability(bins, target)
        assert rel == BaselineReliability.SPARSE_HISTORY

    # 15. High variance reliability state
    def test_high_variance_reliability_state(self):
        tracker = BaselineReliabilityTracker(min_sample_size=3, cv_threshold=1.5)
        # Highly volatile series: [1, 1, 50] -> CV is well above 1.5
        bins = []
        for i, count in enumerate([1, 1, 50]):
            t = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=i)
            bins.append(EpidemiologicalTimeBin(
                disease_key="cholera", geo_key="gujarat", period_start=t, period_end=t + timedelta(days=6),
                iso_year=2024, iso_week=i + 1, observed_case_count=count, fused_event_count=1,
            ))
        target = bins[-1]
        rel, _ = tracker.evaluate_reliability(bins, target)
        assert rel == BaselineReliability.HIGH_VARIANCE

    # 16. EARS C1 calculation and threshold
    def test_ears_c1_calculation_and_threshold(self):
        ears = EARSDetector(baseline_weeks=7, threshold=2.0)
        # 7 historical points: all 10.0 -> mean=10.0, std=0.0 -> denom=smoothing_epsilon=0.001
        history = [10.0] * 7
        # Target = 15.0 -> stat = (15 - 10) / 0.001 >> 2.0 -> alert
        series = history + [15.0]
        res = ears.evaluate_c1(series)
        assert res.is_valid is True
        assert res.is_alert is True
        assert res.statistic > 2.0

        # Normal target = 10.0 -> stat = 0.0 -> no alert
        series_normal = history + [10.0]
        res_normal = ears.evaluate_c1(series_normal)
        assert res_normal.is_alert is False
        assert res_normal.statistic == 0.0

    # 17. EARS C2 guard-band enforcement
    def test_ears_c2_guard_band_enforcement(self):
        ears = EARSDetector(baseline_weeks=7, threshold=2.0)
        # Series: 7 baseline weeks (10.0 each) + 2 guard-band weeks (50.0 outbreak onset) + 1 target week (60.0)
        # Guard band (weeks t-2 and t-1) must be EXCLUDED from reference mean!
        series = [10.0] * 7 + [50.0, 50.0] + [60.0]
        res = ears.evaluate_c2(series, guard_band_weeks=2)

        assert res.is_valid is True
        assert res.reference_count == 7
        assert res.baseline_mean == 10.0  # Guard band 50.0 was successfully excluded!
        assert res.is_alert is True

    # 18. EARS C3 persistence accumulation
    def test_ears_c3_persistence_accumulation(self):
        ears = EARSDetector(baseline_weeks=7, threshold=2.0)
        # Construct series with moderate elevation across 3 consecutive weeks
        # Baseline: 7 weeks of 10.0 +/- 2.0
        base_vals = [8.0, 12.0, 10.0, 10.0, 11.0, 9.0, 10.0]
        # Guard band + 3 weeks of elevated activity (16.0)
        series = base_vals + [10.0, 10.0] + [16.0, 16.0, 16.0]
        res = ears.evaluate_c3(series, persistence_window=3, guard_band_weeks=2)

        assert res.is_valid is True
        assert res.is_alert is True
        assert res.statistic >= 2.0

    # 19. Farrington overdispersion and threshold
    def test_farrington_overdispersion_and_threshold(self):
        farrington = BoundedFarringtonDetector(min_reference_periods=4, z_alpha=1.96)
        # Reference: [5.0, 5.0, 6.0, 4.0] (mean = 5.0)
        ref = [5.0, 5.0, 6.0, 4.0]
        # Normal observation = 6.0 (under threshold)
        res_normal = farrington.evaluate(ref, 6.0)
        assert res_normal.is_valid is True
        assert res_normal.is_alert is False
        assert res_normal.threshold > 5.0

        # Outbreak observation = 25.0 (exceeds threshold)
        res_outbreak = farrington.evaluate(ref, 25.0)
        assert res_outbreak.is_valid is True
        assert res_outbreak.is_alert is True

    # 20. Farrington insufficient history gate
    def test_farrington_insufficient_history_gate(self):
        farrington = BoundedFarringtonDetector(min_reference_periods=4)
        # Only 2 reference periods available (less than 4)
        res = farrington.evaluate([10.0, 12.0], 20.0)
        assert res.is_valid is False
        assert res.is_alert is False
        assert res.threshold == float("inf")
        assert "Insufficient historical data" in res.rationale

    # 21. Signal detector downgrading for single source under high variance
    def test_signal_detector_downgrading_for_single_source(self):
        detector = SignalDetector()
        t = datetime(2024, 7, 15, tzinfo=timezone.utc)
        # High variance baseline
        baseline = BaselineEstimate(
            disease_key="dengue", geo_key="kerala", target_period_start=t, target_period_end=t + timedelta(days=6),
            baseline_window_weeks=5, baseline_count=50.0, baseline_mean=10.0, baseline_median=8.0,
            baseline_std=15.0, baseline_variance=225.0, dispersion_metric=22.5,
            number_of_historical_bins=5, number_of_nonzero_bins=5,
            reliability_status=BaselineReliability.HIGH_VARIANCE,
        )
        # Target bin has elevated cases (50.0) but ONLY 1 independent source
        target = EpidemiologicalTimeBin(
            disease_key="dengue", geo_key="kerala", period_start=t, period_end=t + timedelta(days=6),
            iso_year=2024, iso_week=29, observed_case_count=50, fused_event_count=1,
            independent_source_count=1, supporting_observation_count=1,
        )
        sig = detector.detect_signal([], target, baseline)
        assert sig.signal_level == SignalLevel.WATCH
        assert sig.is_downgraded is True
        assert "single reporting source under high historical variance" in sig.downgrade_reason

    # 22. Geographic stratification no cross-merging
    def test_geographic_stratification_no_cross_merging(self):
        builder = TimeSeriesBuilder()
        t = datetime(2024, 7, 15, tzinfo=timezone.utc)
        fe_kozhikode = make_fused_event(location_name="Kozhikode", event_time=t, cases=3)
        fe_malda = make_fused_event(location_name="Malda", event_time=t, cases=5)
        bins = builder.build_weekly_bins([fe_kozhikode, fe_malda])

        assert len(bins) == 2
        geo_keys = {b.geo_key for b in bins}
        assert geo_keys == {"kozhikode", "malda"}

    # 23. Disease stratification no cross-merging
    def test_disease_stratification_no_cross_merging(self):
        builder = TimeSeriesBuilder()
        t = datetime(2024, 7, 15, tzinfo=timezone.utc)
        fe_nipah = make_fused_event(disease="Nipah virus disease", event_time=t, cases=2)
        fe_dengue = make_fused_event(disease="Dengue", event_time=t, cases=10)
        bins = builder.build_weekly_bins([fe_nipah, fe_dengue])

        assert len(bins) == 2
        disease_keys = {b.disease_key for b in bins}
        assert disease_keys == {"nipah virus disease", "dengue"}

    # 24. Deterministic reproducibility and provenance preservation
    def test_deterministic_reproducibility_and_provenance(self):
        runner = SignalBatchRunner(min_sample_size=2)
        t1 = datetime(2024, 7, 8, tzinfo=timezone.utc)
        t2 = datetime(2024, 7, 15, tzinfo=timezone.utc)
        fe1 = make_fused_event(event_time=t1, cases=2, obs_count=2)
        fe2 = make_fused_event(event_time=t2, cases=8, obs_count=3)

        # Run 1
        rep1, bins1, base1, sig1 = runner.process_fused_events([fe1, fe2], run_name="run_1")
        # Run 2
        rep2, bins2, base2, sig2 = runner.process_fused_events([fe1, fe2], run_name="run_2")

        # Bit-for-bit identical IDs and metrics across runs
        assert rep1.total_signals_detected == rep2.total_signals_detected
        assert [b.bin_id for b in bins1] == [b.bin_id for b in bins2]
        assert [b.baseline_id for b in base1] == [b.baseline_id for b in base2]
        assert [s.signal_id for s in sig1] == [s.signal_id for s in sig2]

        # Provenance preservation check
        assert len(sig2[1].provenance_references) > 0
        ref = sig2[1].provenance_references[0]
        assert ref.span_text == "8 confirmed cases"
        assert ref.attribute_role == "case_count"

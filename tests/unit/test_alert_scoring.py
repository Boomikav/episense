"""
Unit tests for Phase 9 Epidemiological Alert Scoring & Risk Assessment Engine.
Covers pathogen threat classification, multi-criteria risk scoring, safety ceilings,
explainability dossier compilation, determinism, and batch execution.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest
from uuid import UUID, NAMESPACE_DNS, uuid5

from episense.schemas.alert import (
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
from episense.schemas.location import GeographicLevel, Location
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.config.settings import ScoringConfig
from episense.scoring.threat import PathogenThreatClassifier
from episense.scoring.explainer import AlertExplainer
from episense.scoring.scorer import AlertScorer
from episense.scoring.batch import AlertBatchRunner


# ==============================================================================
# Helpers & Fixtures
# ==============================================================================

def make_test_signal(
    disease: str = "dengue",
    geo: str = "kozhikode",
    start_dt: Optional[datetime] = None,
    obs_val: float = 10.0,
    exp_val: float = 2.0,
    z_score: float = 2.5,
    method: DetectionMethod = DetectionMethod.EARS_C1,
    level: SignalLevel = SignalLevel.SIGNAL,
    reliability: BaselineReliability = BaselineReliability.STABLE_BASELINE,
    source_count: int = 2,
    is_downgraded: bool = False,
    downgrade_reason: Optional[str] = None,
    provenance_references: Optional[List[EvidenceReference]] = None,
) -> SignalObservation:
    start = start_dt or datetime(2024, 9, 2, tzinfo=timezone.utc)
    end = datetime(2024, 9, 8, 23, 59, 59, tzinfo=timezone.utc)
    sig_id = uuid5(NAMESPACE_DNS, f"{disease}:{geo}:{start.isoformat()}:sig")
    if provenance_references is None:
        prov_refs = [
            EvidenceReference(
                document_id=uuid5(NAMESPACE_DNS, "doc1"),
                source_id="pib_mohfw_india",
                start_char=10,
                end_char=20,
                span_text=disease,
                extraction_method="ner:exact",
                attribute_role="primary_disease",
            )
        ]
    else:
        prov_refs = provenance_references

    return SignalObservation(
        signal_id=sig_id,
        disease_key=disease,
        geo_key=geo,
        target_period_start=start,
        target_period_end=end,
        observed_value=obs_val,
        expected_value=exp_val,
        deviation=obs_val - exp_val,
        standardized_score=z_score,
        threshold=2.0,
        detection_method=method,
        signal_level=level,
        supporting_fused_event_ids=[],
        supporting_source_count=source_count,
        reliability_status=reliability,
        is_downgraded=is_downgraded,
        downgrade_reason=downgrade_reason,
        explainable_rationale="Test signal rationale",
        provenance_references=prov_refs,
        created_at=end,
    )


def make_test_fused_event(
    disease: str = "dengue",
    geo: str = "kozhikode",
    status: AssertionStatus = AssertionStatus.CONFIRMED,
    case_count: int = 10,
    death_count: int = 0,
    source_ids: Optional[List[str]] = None,
    has_conflicts: bool = False,
) -> FusedEvent:
    start = datetime(2024, 9, 2, tzinfo=timezone.utc)
    end = datetime(2024, 9, 8, 23, 59, 59, tzinfo=timezone.utc)
    fid = uuid5(NAMESPACE_DNS, f"{disease}:{geo}:{start.isoformat()}:fused")
    s_ids = source_ids or ["pib_mohfw_india", "who_don_feed"]
    sources = [SourceGroup(independence_group=s, source_id=s) for s in s_ids]

    loc = Location(
        original_text=geo,
        normalized_name=geo,
        geographic_level=GeographicLevel.DISTRICT,
        confidence=1.0,
    )

    return FusedEvent(
        fused_event_id=fid,
        canonical_disease=disease,
        canonical_location=loc,
        geographic_hierarchy={"district": geo},
        event_window_start=start,
        event_window_end=end,
        assertion_status=status,
        certainty=CertaintyLevel.DEFINITE,
        aggregated_quantities=EpidemiologicalQuantities(
            case_count=case_count,
            death_count=death_count,
        ),
        independent_sources=sources,
        has_conflicts=has_conflicts,
        supporting_observation_count=len(s_ids),
        evidence_references=[
            EvidenceReference(
                document_id=uuid5(NAMESPACE_DNS, "doc1"),
                source_id="pib_mohfw_india",
                start_char=10,
                end_char=20,
                span_text=disease,
                extraction_method="ner:exact",
                attribute_role="primary_disease",
            )
        ],
    )


# ==============================================================================
# Unit Test Cases (22 Comprehensive Tests)
# ==============================================================================

class TestAlertScoring:

    def test_pathogen_threat_classification(self):
        """1. Verify correct pathogen clinical consequence tiering."""
        classifier = PathogenThreatClassifier()
        assert classifier.classify("Nipah virus disease") == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE
        assert classifier.classify("Marburg virus") == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE
        assert classifier.classify("avian influenza") == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE
        assert classifier.classify("Cholera") == PathogenThreatTier.TIER_3_SEVERE
        assert classifier.classify("Kyasanur Forest Disease") == PathogenThreatTier.TIER_3_SEVERE
        assert classifier.classify("Dengue") == PathogenThreatTier.TIER_2_MODERATE
        assert classifier.classify("Malaria") == PathogenThreatTier.TIER_2_MODERATE
        assert classifier.classify("disease/illness") == PathogenThreatTier.TIER_1_MILD
        assert classifier.classify("viral fever") == PathogenThreatTier.TIER_1_MILD
        assert classifier.classify("unrecognized random condition") == PathogenThreatTier.TIER_1_MILD

    def test_statistical_anomaly_score_scaling(self):
        """2. Verify Z-score scaling and multi-detector bonus."""
        scorer = AlertScorer()
        
        # Test Z=1.0 -> 0.0, Z=2.5 -> 0.50, Z>=4.0 -> 1.0
        sig_low = make_test_signal(z_score=1.0, level=SignalLevel.WATCH)
        alert_low = scorer.score_signal(sig_low)
        assert alert_low.score_breakdown.anomaly_score >= 0.25  # WATCH lower bound

        sig_high = make_test_signal(z_score=4.5, level=SignalLevel.STRONG_SIGNAL, method=DetectionMethod.MULTI_DETECTOR)
        alert_high = scorer.score_signal(sig_high)
        assert alert_high.score_breakdown.anomaly_score >= 0.85

    def test_source_diversity_scoring(self):
        """3. Verify source diversity scoring and official authority boost."""
        scorer = AlertScorer()

        # 1 source without official authority
        sig1 = make_test_signal(source_count=1, provenance_references=[])
        fe1 = make_test_fused_event(source_ids=["local_tabloid"])
        alert1 = scorer.score_signal(sig1, fused_events=[fe1])
        assert alert1.score_breakdown.evidence_score == 0.35

        # 2 sources with official authority (pib_mohfw_india)
        sig2 = make_test_signal(source_count=2)
        fe2 = make_test_fused_event(source_ids=["pib_mohfw_india", "hindu_news"])
        alert2 = scorer.score_signal(sig2, fused_events=[fe2])
        assert alert2.score_breakdown.evidence_score == min(1.0, 0.70 + 0.15)

    def test_assertion_and_mortality_scoring(self):
        """4. Verify clinical certainty and mortality confirmation boosts."""
        scorer = AlertScorer()

        # Suspected, no deaths
        fe_susp = make_test_fused_event(status=AssertionStatus.SUSPECTED, death_count=0)
        alert_susp = scorer.score_signal(make_test_signal(), fused_events=[fe_susp])
        assert alert_susp.score_breakdown.certainty_score == 0.70

        # Confirmed with reported mortality
        fe_conf = make_test_fused_event(status=AssertionStatus.CONFIRMED, death_count=3)
        alert_conf = scorer.score_signal(make_test_signal(), fused_events=[fe_conf])
        assert alert_conf.score_breakdown.certainty_score == 1.00  # 1.0 + 0.2 capped at 1.0

    def test_spatial_resolution_scoring(self):
        """5. Verify spatial granularity weighting (district vs state vs global)."""
        scorer = AlertScorer()

        # District
        alert_dist = scorer.score_signal(make_test_signal(geo="kozhikode"))
        assert alert_dist.score_breakdown.spatial_score == 1.00

        # State
        alert_state = scorer.score_signal(make_test_signal(geo="kerala"))
        assert alert_state.score_breakdown.spatial_score == 0.75

        # Unspecified or global
        alert_glob = scorer.score_signal(make_test_signal(geo="unspecified_or_global"))
        assert alert_glob.score_breakdown.spatial_score == 0.30

    def test_composite_score_weighting(self):
        """6. Verify exact mathematical weighted sum."""
        scorer = AlertScorer(
            weight_anomaly=0.30,
            weight_threat=0.25,
            weight_evidence=0.20,
            weight_certainty=0.15,
            weight_spatial=0.10,
        )
        sig = make_test_signal(disease="dengue", geo="kozhikode", z_score=2.5)
        fe = make_test_fused_event(disease="dengue", geo="kozhikode", status=AssertionStatus.CONFIRMED)
        alert = scorer.score_signal(sig, fused_events=[fe])

        bd = alert.score_breakdown
        expected_raw = round(
            0.30 * bd.anomaly_score
            + 0.25 * bd.threat_score
            + 0.20 * bd.evidence_score
            + 0.15 * bd.certainty_score
            + 0.10 * bd.spatial_score,
            3,
        )
        assert abs(bd.raw_composite_score - expected_raw) < 1e-4

    def test_alert_tier_assignment(self):
        """7. Verify threshold boundaries for AlertTier assignment."""
        scorer = AlertScorer()
        # Routine generic fever on low anomaly -> INFORMATIONAL
        sig_info = make_test_signal(
            disease="disease/illness",
            geo="unspecified_or_global",
            level=SignalLevel.NO_SIGNAL,
            z_score=0.2,
            source_count=1,
            provenance_references=[],
        )
        fe_info = make_test_fused_event(disease="disease/illness", geo="unspecified_or_global", status=AssertionStatus.HISTORICAL, source_ids=["local_tabloid"])
        alert_info = scorer.score_signal(sig_info, fused_events=[fe_info])
        assert alert_info.alert_tier == AlertTier.INFORMATIONAL
        assert alert_info.composite_score < 0.40

    def test_insufficient_history_ceiling(self):
        """8. Verify that INSUFFICIENT_HISTORY caps alert tier at MEDIUM or LOW."""
        scorer = AlertScorer()
        # Endemic condition with high anomaly but insufficient baseline
        sig = make_test_signal(
            disease="dengue",
            geo="kozhikode",
            z_score=5.0,
            level=SignalLevel.SIGNAL,
            reliability=BaselineReliability.INSUFFICIENT_HISTORY,
            source_count=3,
        )
        fe = make_test_fused_event(disease="dengue", geo="kozhikode", status=AssertionStatus.CONFIRMED)
        alert = scorer.score_signal(sig, fused_events=[fe])

        assert alert.is_gated is True
        assert alert.alert_tier == AlertTier.LOW
        assert alert.composite_score <= 0.64
        assert "insufficient" in alert.gating_reason.lower()

    def test_conflicting_data_penalty_and_ceiling(self):
        """9. Verify -0.10 penalty and MEDIUM ceiling under CONFLICTING_DATA."""
        scorer = AlertScorer()
        sig = make_test_signal(
            disease="nipah virus disease",
            geo="kozhikode",
            z_score=4.0,
            level=SignalLevel.SIGNAL,
            reliability=BaselineReliability.CONFLICTING_DATA,
            source_count=3,
        )
        fe = make_test_fused_event(
            disease="nipah virus disease",
            geo="kozhikode",
            status=AssertionStatus.CONFIRMED,
            has_conflicts=True,
        )
        alert = scorer.score_signal(sig, fused_events=[fe])

        assert alert.is_gated is True
        assert alert.score_breakdown.penalty_applied == 0.10
        assert alert.composite_score <= 0.79
        assert alert.alert_tier in (AlertTier.MEDIUM, AlertTier.LOW)

    def test_single_source_high_alert_prevention(self):
        """10. Verify single reporting source cannot trigger HIGH alert tier."""
        scorer = AlertScorer()
        # High-threat pathogen, huge anomaly, but only 1 source
        sig = make_test_signal(
            disease="nipah virus disease",
            geo="kozhikode",
            z_score=6.0,
            level=SignalLevel.STRONG_SIGNAL,
            reliability=BaselineReliability.STABLE_BASELINE,
            source_count=1,
        )
        fe = make_test_fused_event(disease="nipah virus disease", geo="kozhikode", source_ids=["local_reporter"])
        alert = scorer.score_signal(sig, fused_events=[fe])

        assert alert.is_gated is True
        assert alert.alert_tier != AlertTier.HIGH
        assert alert.composite_score <= 0.79

    def test_syndicated_wire_independence_scoring_prevention(self):
        """10b. Verify syndicated copies from same wire network do not inflate alert score to HIGH."""
        scorer = AlertScorer()
        # Three syndicated clippings from same wire agency (e.g. PTI regional bureaus)
        fe = make_test_fused_event(
            disease="dengue",
            geo="delhi",
            source_ids=["pti_delhi", "pti_punjab", "pti_haryana"],
        )
        # When independence groups are properly respected, independent_sources == 1
        sig_with_grouping = make_test_signal(
            disease="dengue",
            geo="delhi",
            level=SignalLevel.STRONG_SIGNAL,
            z_score=4.0,
            source_count=1,  # Resolves to 1 independent group
        )
        alert_grouped = scorer.score_signal(sig_with_grouping, fused_events=[fe])

        # Composite score must be 0.775 (Tier MEDIUM), NOT 0.875 (Tier HIGH)
        assert alert_grouped.alert_tier == AlertTier.MEDIUM
        assert alert_grouped.composite_score == 0.775
        assert alert_grouped.score_breakdown.evidence_score == 0.50

        # Contrast: if naively treated as 3 independent publishers, it would inflate to 0.875 (HIGH)
        sig_unfused = make_test_signal(
            disease="dengue",
            geo="delhi",
            level=SignalLevel.STRONG_SIGNAL,
            z_score=4.0,
            source_count=3,
        )
        alert_inflated = scorer.score_signal(sig_unfused, fused_events=[fe])
        assert alert_inflated.composite_score == 0.875
        assert alert_inflated.alert_tier == AlertTier.HIGH

    def test_negated_event_suppression(self):
        """11. Verify negated events are suppressed to INFORMATIONAL with score 0.0."""
        scorer = AlertScorer()
        sig = make_test_signal(disease="nipah virus disease", geo="kozhikode")
        fe_neg = make_test_fused_event(
            disease="nipah virus disease",
            geo="kozhikode",
            status=AssertionStatus.NEGATED,
        )
        alert = scorer.score_signal(sig, fused_events=[fe_neg])

        assert alert.composite_score == 0.0
        assert alert.alert_tier == AlertTier.INFORMATIONAL
        assert alert.is_gated is True
        assert "negated" in alert.gating_reason.lower()

    def test_multi_detector_strong_signal_high_alert(self):
        """12. Multi-source corroborated strong signal on stable baseline achieves HIGH alert."""
        scorer = AlertScorer()
        sig = make_test_signal(
            disease="nipah virus disease",
            geo="kozhikode",
            z_score=4.5,
            level=SignalLevel.STRONG_SIGNAL,
            method=DetectionMethod.MULTI_DETECTOR,
            reliability=BaselineReliability.STABLE_BASELINE,
            source_count=3,
        )
        fe = make_test_fused_event(
            disease="nipah virus disease",
            geo="kozhikode",
            status=AssertionStatus.CONFIRMED,
            death_count=2,
            source_ids=["who_don_feed", "pib_mohfw_india", "reuters"],
        )
        alert = scorer.score_signal(sig, fused_events=[fe])

        assert alert.alert_tier == AlertTier.HIGH
        assert alert.composite_score >= 0.80
        assert alert.is_gated is False

    def test_high_threat_pathogen_priority(self):
        """13. Verify high-consequence pathogen outranks higher-count mild condition."""
        scorer = AlertScorer()
        
        # Nipah virus with 2 cases (Tier 4)
        sig_nipah = make_test_signal(disease="nipah virus disease", geo="kozhikode", obs_val=2.0, z_score=2.0, source_count=2)
        fe_nipah = make_test_fused_event(disease="nipah virus disease", geo="kozhikode", case_count=2)
        alert_nipah = scorer.score_signal(sig_nipah, fused_events=[fe_nipah])

        # Generic illness with 100 cases (Tier 1)
        sig_mild = make_test_signal(disease="disease/illness", geo="kozhikode", obs_val=100.0, z_score=2.0, source_count=2)
        fe_mild = make_test_fused_event(disease="disease/illness", geo="kozhikode", case_count=100)
        alert_mild = scorer.score_signal(sig_mild, fused_events=[fe_mild])

        assert alert_nipah.score_breakdown.threat_score > alert_mild.score_breakdown.threat_score
        assert alert_nipah.composite_score > alert_mild.composite_score

    def test_explainability_dossier_generation(self):
        """14. Verify driving factors and structured narrative in explanation."""
        scorer = AlertScorer()
        sig = make_test_signal(disease="cholera", geo="rayagada", z_score=3.0)
        fe = make_test_fused_event(disease="cholera", geo="rayagada", death_count=1)
        alert = scorer.score_signal(sig, fused_events=[fe])

        exp = alert.explanation
        assert "Cholera" in exp.summary
        assert len(exp.driving_factors) >= 4
        assert "EPIDEMIOLOGICAL ALERT AUDIT DOSSIER" in exp.detailed_narrative
        assert "DIMENSION EVALUATION" in exp.detailed_narrative

    def test_full_provenance_preservation(self):
        """15. Verify underlying character-level EvidenceReferences are preserved."""
        scorer = AlertScorer()
        sig = make_test_signal()
        fe = make_test_fused_event()
        alert = scorer.score_signal(sig, fused_events=[fe])

        assert len(alert.provenance_references) > 0
        ref = alert.provenance_references[0]
        assert ref.start_char == 10
        assert ref.end_char == 20
        assert ref.span_text == "dengue"

    def test_deterministic_alert_id_generation(self):
        """16. Verify deterministic UUID5 generation for identical inputs."""
        scorer = AlertScorer()
        sig1 = make_test_signal()
        sig2 = make_test_signal()

        alert1 = scorer.score_signal(sig1)
        alert2 = scorer.score_signal(sig2)
        assert alert1.alert_id == alert2.alert_id

    def test_batch_runner_execution(self, tmp_path):
        """17. Verify batch execution and artifact serialization."""
        runner = AlertBatchRunner(output_dir=str(tmp_path / "alerts"))
        sigs = [
            make_test_signal(disease="dengue", geo="kozhikode"),
            make_test_signal(disease="cholera", geo="rayagada"),
        ]
        fes = [
            make_test_fused_event(disease="dengue", geo="kozhikode"),
            make_test_fused_event(disease="cholera", geo="rayagada"),
        ]
        report, alerts = runner.process_signals(sigs, fused_events=fes, run_name="test_run")

        assert len(alerts) == 2
        assert report.total_signals_consumed == 2
        assert report.total_alerts_generated == 2
        assert (tmp_path / "alerts" / "test_run" / "alerts.json").exists()
        assert (tmp_path / "alerts" / "test_run" / "alert_summary.json").exists()

    def test_byte_for_byte_reproducibility(self, tmp_path):
        """18. Verify dual-run byte-for-byte serialization reproducibility."""
        runner1 = AlertBatchRunner(output_dir=str(tmp_path / "run1"))
        runner2 = AlertBatchRunner(output_dir=str(tmp_path / "run2"))

        sigs = [make_test_signal(disease="dengue", geo="kerala")]
        fes = [make_test_fused_event(disease="dengue", geo="kerala")]

        runner1.process_signals(sigs, fused_events=fes, run_name="out")
        runner2.process_signals(sigs, fused_events=fes, run_name="out")

        bytes1 = (tmp_path / "run1" / "out" / "alerts.json").read_bytes()
        bytes2 = (tmp_path / "run2" / "out" / "alerts.json").read_bytes()
        assert bytes1 == bytes2

    def test_empty_and_no_signal_handling(self):
        """19. Verify empty signals and NO_SIGNAL handled gracefully."""
        scorer = AlertScorer()
        sig_none = make_test_signal(level=SignalLevel.NO_SIGNAL)
        alert = scorer.score_signal(sig_none)
        assert alert.score_breakdown.anomaly_score == 0.0

        runner = AlertBatchRunner(output_dir="data/alerts/tmp_test")
        rep, alerts = runner.process_signals([])
        assert len(alerts) == 0
        assert rep.total_alerts_generated == 0

    def test_config_custom_weights(self):
        """20. Verify AlertScorer loads and respects custom weights from ScoringConfig."""
        cfg = ScoringConfig(
            weight_anomaly=0.25,
            weight_threat=0.35,
            weight_evidence=0.20,
            weight_certainty=0.10,
            weight_spatial=0.10,
        )
        scorer = AlertScorer.from_config(cfg)
        assert scorer.weights["threat"] == 0.35
        assert scorer.weights["anomaly"] == 0.25

    def test_disease_geographic_stratification(self):
        """21. Verify alerts maintain strict disease and geographic separation."""
        scorer = AlertScorer()
        sig_dengue = make_test_signal(disease="dengue", geo="kozhikode")
        sig_malaria = make_test_signal(disease="malaria", geo="rayagada")

        a1 = scorer.score_signal(sig_dengue)
        a2 = scorer.score_signal(sig_malaria)
        assert a1.disease_key != a2.disease_key
        assert a1.geo_key != a2.geo_key
        assert a1.alert_id != a2.alert_id

    def test_pydantic_schema_validation(self):
        """22. Verify Pydantic validation rejects invalid ranges or empty keys."""
        with pytest.raises(Exception):
            EpidemiologicalAlert(
                signal_id=uuid5(NAMESPACE_DNS, "sig"),
                disease_key="",  # Empty disease key rejected
                geo_key="kozhikode",
                pathogen_threat_tier=PathogenThreatTier.TIER_2_MODERATE,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                composite_score=1.5,  # Out of [0, 1] range rejected
                alert_tier=AlertTier.HIGH,
                score_breakdown=None,  # Missing required breakdown
                explanation=None,
            )

    def test_score_semantics_and_recommended_action(self):
        """23. Verify Phase 3 score semantics: event_triage_score, indicator_anomaly_result, and recommended_action."""
        from episense.schemas.alert import RecommendedReviewAction
        scorer = AlertScorer()

        # Case A: High threat Nipah signal with multi-source support
        fe_high = make_test_fused_event(
            disease="nipah virus disease",
            geo="kozhikode",
            status=AssertionStatus.CONFIRMED,
            source_ids=["who", "promed"],
        )
        sig_high = make_test_signal(
            disease="nipah virus disease",
            geo="kozhikode",
            level=SignalLevel.STRONG_SIGNAL,
            z_score=3.5,
            source_count=2,
            method=DetectionMethod.EARS_C1,
        )
        alert_high = scorer.score_signal(sig_high, fused_events=[fe_high])
        assert alert_high.event_triage_score == alert_high.composite_score
        assert alert_high.recommended_action == RecommendedReviewAction.INVESTIGATE
        assert alert_high.indicator_anomaly_result is not None
        assert alert_high.indicator_anomaly_result["primary_method"] == "ears_c1"
        assert alert_high.indicator_anomaly_result["standardized_score"] == 3.5

        # Case B: Negated mention gets DISCARD
        fe_neg = make_test_fused_event(
            disease="cholera",
            geo="malda",
            status=AssertionStatus.NEGATED,
        )
        sig_neg = make_test_signal(disease="cholera", geo="malda")
        alert_neg = scorer.score_signal(sig_neg, fused_events=[fe_neg])
        assert alert_neg.composite_score == 0.0
        assert alert_neg.event_triage_score == 0.0
        assert alert_neg.recommended_action == RecommendedReviewAction.DISCARD

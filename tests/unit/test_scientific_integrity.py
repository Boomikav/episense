"""
Scientific Integrity and Epidemiological Safety Verification Tests for EpiSense.
Verifies:
1. Insufficient historical baseline produces explicit gating and suppresses false anomaly signals.
2. Strict separation between document/event mentions and epidemiological case counts.
3. Spatial and disease granularity isolation (incompatible series rejected).
4. Cardiovascular disease cannot cause outbreaks and is gated to INFORMATIONAL.
5. GroundedLLMAdapter operates in OFFLINE_DETERMINISTIC_MODE with zero live external claims.
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest

from episense.schemas.signal import EpidemiologicalTimeBin, BaselineReliability, SignalLevel
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.alert import AlertTier, PathogenThreatTier
from episense.taxonomy.registry import DEFAULT_TAXONOMY_REGISTRY
from episense.taxonomy.models import TaxonomyCategory
from episense.baseline.reliability import BaselineReliabilityTracker
from episense.baseline.engine import BaselineEngine
from episense.anomaly.detector import SignalDetector
from episense.scoring.scorer import AlertScorer
from episense.nlp.llm_adapter import GroundedLLMAdapter, LLMStructuredExtraction, LLMExtractedEntity
from episense.nlp.pipeline import NLPPipeline


def create_mock_bin(
    disease: str,
    geo: str,
    week: int,
    year: int = 2026,
    cases: int = None,
    deaths: int = None,
    events: int = 1,
    conflicts: dict = None,
) -> EpidemiologicalTimeBin:
    start = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=week - 1)
    end = start + timedelta(days=7)
    return EpidemiologicalTimeBin(
        bin_id=uuid4(),
        disease_key=disease,
        geo_key=geo,
        period_start=start,
        period_end=end,
        iso_year=year,
        iso_week=week,
        observed_case_count=int(cases) if cases is not None else None,
        observed_death_count=int(deaths) if deaths is not None else None,
        fused_event_count=events,
        independent_source_count=1,
        supporting_observation_count=1,
        has_conflicts=bool(conflicts),
        conflicting_quantities=conflicts or {},
        is_zero_reporting=False,
        completeness_status="complete",
        fused_event_ids=[],
        origin=OriginClassification.LIVE_EXTERNAL,
        provenance_references=[],
    )


class TestScientificIntegrity:

    def test_insufficient_historical_baseline_blocks_statistical_signals(self):
        """
        When fewer than 3 historical periods exist, the system must emit
        INSUFFICIENT_HISTORY, set is_downgraded = True, and suppress signal to NO_SIGNAL.
        """
        tracker = BaselineReliabilityTracker(min_sample_size=3)
        engine = BaselineEngine(min_sample_size=3)
        detector = SignalDetector()

        # Only 2 historical bins (< 3)
        history = [create_mock_bin("Dengue", "District_X", w, cases=10) for w in [1, 2]]
        target = create_mock_bin("Dengue", "District_X", 3, cases=50)

        rel, rationale = tracker.evaluate_reliability(history, target, value_type="cases")
        assert rel in (BaselineReliability.INSUFFICIENT_HISTORY, BaselineReliability.INSUFFICIENT_BASELINE)
        assert "minimum required is 3" in rationale

        baseline = engine.compute_baseline(history, target, value_type="cases")
        assert baseline.reliability_status == rel

        signal = detector.detect_signal(history, target, baseline, value_type="cases")
        assert signal.is_downgraded is True
        assert signal.signal_level == SignalLevel.NO_SIGNAL
        assert "Signal suppressed" in signal.explainable_rationale

    def test_separation_of_document_mentions_from_case_counts(self):
        """
        Document and fused event mention counts must NEVER be substituted
        for epidemiological case counts.
        """
        engine = BaselineEngine(min_sample_size=3)

        # Historical bins with 10 event mentions each, but NO quantitative case observations
        history = [create_mock_bin("Cholera", "District_Y", w, cases=None, events=10) for w in range(1, 6)]
        target = create_mock_bin("Cholera", "District_Y", 6, cases=5, events=1)

        baseline = engine.compute_baseline(history, target, value_type="cases")
        # Invariant: baseline mean of cases must be 0.0, NOT 10.0
        assert baseline.baseline_mean == 0.0

    def test_spatial_and_disease_granularity_isolation(self):
        """
        Historical observations from an unrelated district or different disease
        must be rejected with INCOMPATIBLE_GRANULARITY.
        """
        tracker = BaselineReliabilityTracker(min_sample_size=3)

        # Cross-district mismatch
        hist_geo = [create_mock_bin("Dengue", "District_A", w, cases=10) for w in range(1, 5)]
        target_geo = create_mock_bin("Dengue", "District_B", 5, cases=25)
        rel_geo, rat_geo = tracker.evaluate_reliability(hist_geo, target_geo, value_type="cases")
        assert rel_geo == BaselineReliability.INCOMPATIBLE_GRANULARITY
        assert "Incompatible spatial granularity" in rat_geo

        # Cross-pathogen mismatch
        hist_dis = [create_mock_bin("Dengue", "District_A", w, cases=10) for w in range(1, 5)]
        target_dis = create_mock_bin("Malaria", "District_A", 5, cases=25)
        rel_dis, rat_dis = tracker.evaluate_reliability(hist_dis, target_dis, value_type="cases")
        assert rel_dis == BaselineReliability.INCOMPATIBLE_GRANULARITY
        assert "Incompatible disease key" in rat_dis

    def test_cardiovascular_disease_cannot_cause_outbreak(self):
        """
        Cardiovascular Disease is classified as NON_COMMUNICABLE_CONDITION with 0 threat score,
        and AlertScorer must gate it to INFORMATIONAL (score <= 0.35).
        """
        reg = DEFAULT_TAXONOMY_REGISTRY
        match = reg.resolve("Cardiovascular disease")
        assert match is not None
        assert match.category == TaxonomyCategory.NON_COMMUNICABLE_CONDITION
        assert match.can_cause_outbreak is False
        assert match.pathogen_tier == PathogenThreatTier.NONE

        scorer = AlertScorer()
        mock_signal = SignalDetector().detect_signal(
            [create_mock_bin("Cardiovascular disease", "District_A", w, cases=10) for w in range(1, 5)],
            create_mock_bin("Cardiovascular disease", "District_A", 5, cases=30),
            BaselineEngine().compute_baseline(
                [create_mock_bin("Cardiovascular disease", "District_A", w, cases=10) for w in range(1, 5)],
                create_mock_bin("Cardiovascular disease", "District_A", 5, cases=30),
                value_type="cases"
            ),
            value_type="cases"
        )

        alert = scorer.score_signal(
            signal=mock_signal,
            fused_events=[],
        )

        assert alert.alert_tier == AlertTier.INFORMATIONAL
        assert alert.composite_score <= 0.35
        assert alert.is_gated is True
        assert alert.gating_reason is not None
        assert "Non-communicable condition" in alert.gating_reason

    def test_llm_adapter_operating_mode_is_offline_deterministic(self):
        """
        GroundedLLMAdapter must explicitly report OFFLINE_DETERMINISTIC_MODE,
        is_live_external_operational == False, verify evidence spans, and fall back cleanly.
        """
        import hashlib
        adapter = GroundedLLMAdapter()
        assert adapter.operating_mode == "OFFLINE_DETERMINISTIC_MODE"
        assert adapter.is_live_external_operational is False

        # Verify hallucination rejection
        text = "Confirmed 5 cases of Dengue in Kozhikode."
        hallucination = LLMStructuredExtraction(
            primary_disease=LLMExtractedEntity(
                raw_span="Ebola virus",
                canonical_name="Ebola virus disease",
                start_char=0,
                end_char=11,
            )
        )
        res = adapter.verify_grounding(text, hallucination)
        assert res.is_grounded is False
        assert res.hallucination_detected is True

        # Verify deterministic spaCy fallback
        pipeline = NLPPipeline(enable_cache=False)
        doc = Document(
            document_id=uuid4(),
            source_id="test",
            source_type=SourceType.NEWS_MEDIA,
            origin=OriginClassification.LIVE_EXTERNAL,
            title="Dengue outbreak",
            text=text,
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            publication_timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        output = adapter.process_document(doc, fallback_pipeline=pipeline)
        assert output.document_id == doc.document_id
        assert len(output.entities) > 0
        assert any(e.text_span == "Dengue" for e in output.entities)

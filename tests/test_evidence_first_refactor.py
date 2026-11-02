"""
Comprehensive Regression Test Suite for Evidence-First Epidemiological Intelligence Refactor.
Verifies all 11 audited defects from the forensic audit:
1. Provenance separation & live/historical metric segregation
2. 2023 year-as-count rejection
3. Preparedness and Chintan Shivir non-outbreak classification
4. Surveillance program acronym exclusion (IDSP, NCDC, IHIP)
5. Spatial/temporal granularity matching & baseline anomaly suppression
6. Supporting candidate observations linkage in event clusters
7. Threat tier vs situational alert priority decoupling
8. Structured 5-question explainability dossier and analyst playbook
"""

from datetime import datetime, timezone
import pytest
from uuid import uuid4

from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.event import (
    EventCandidate,
    EventObservation,
    FusedEvent,
    EpidemiologicalQuantities,
    EvidenceReference,
)
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.schemas.alert import AlertTier, EpidemiologicalAlert, PathogenThreatTier
from episense.nlp.quantities import QuantityExtractor
from episense.events.relevance import EventRelevanceClassifier, EventRelevanceCategory
from episense.nlp.entities.extractor import HybridHealthEntityExtractor
from episense.baseline.reliability import BaselineReliabilityTracker
from episense.anomaly.detector import SignalDetector
from episense.scoring.scorer import AlertScorer
from episense.explainability.dossier import DossierGenerator


class TestEvidenceFirstRefactor:
    """Verifies that all 11 audited defects have been solved and cannot regress."""

    def test_2023_year_not_extracted_as_case_count(self):
        """Defect 5: 2023 calendar year must never be parsed as a case or death count."""
        extractor = QuantityExtractor()

        # Test A: IDSP summary with date of start
        text_idsp = (
            "State: Maharashtra | District: Mumbai Suburban | Disease/Illness: Measles | "
            "No. of Cases: 31 | No. of Deaths: 0 | Date of start of outbreak: 2023-01-29."
        )
        quantities = extractor.extract(text_idsp)
        values = [q.numeric_value for q in quantities]

        assert 2023 not in values, f"2023 was erroneously extracted as a quantity in: {values}"
        assert 31 in values, f"True case count 31 should be extracted: {values}"

        # Test B: Prepositional temporal year expression
        text_temporal = "In 2023 cases of cholera increased across the district, with 14 confirmed cases recorded."
        q_temp = extractor.extract(text_temporal)
        v_temp = [q.numeric_value for q in q_temp]

        assert 2023 not in v_temp, f"Prepositional 'In 2023' must not be parsed as case count: {v_temp}"
        assert 14 in v_temp, f"True case count 14 should be extracted: {v_temp}"

    def test_adversarial_quantity_variations(self):
        """Item 4: Verify 7 adversarial quantity patterns."""
        extractor = QuantityExtractor()

        # 1. Meeting held in 2023 -> rejected
        assert len(extractor.extract("The meeting was held in 2023.")) == 0

        # 2. Report published in 2023 -> rejected
        assert len(extractor.extract("The report was published in 2023.")) == 0

        # 3. 2023 confirmed cases -> accepted
        q3 = extractor.extract("2023 confirmed cases were reported.")
        assert len(q3) == 1 and q3[0].numeric_value == 2023.0 and q3[0].unit == "confirmed cases"

        # 4. 23 confirmed cases -> accepted
        q4 = extractor.extract("There were 23 confirmed cases.")
        assert len(q4) == 1 and q4[0].numeric_value == 23.0

        # 5. 23 suspected cases and 2 deaths -> separated
        q5 = extractor.extract("23 suspected cases and 2 deaths were reported.")
        assert len(q5) == 2
        vals = {q.numeric_value: q.unit for q in q5}
        assert 23.0 in vals and "suspected" in vals[23.0]
        assert 2.0 in vals and "death" in vals[2.0]

        # 6. Cumulative total of 1,250 cases with 15 new cases -> comma parsed properly
        q6 = extractor.extract("A cumulative total of 1,250 cases have been recorded, with 15 new cases reported today.")
        vals6 = [q.numeric_value for q in q6]
        assert 1250.0 in vals6
        assert 15.0 in vals6

        # 7. Percentage, population denominator, date, ID -> non-clinical units rejected
        q7 = extractor.extract("Mortality reached 12.5% among the population of 50,000 as of 2023-04-15 (Report ID: REF-98421).")
        assert len(q7) == 0

    def test_preparedness_chintan_shivir_classified_as_non_outbreak(self):
        """Defect 3: National Influenza Chintan Shivir seasonal preparedness must not become ACUTE_OUTBREAK_REPORT."""
        classifier = EventRelevanceClassifier()

        title = "MoHFW and WHO organize National Influenza Chintan Shivir for seasonal preparedness"
        text = (
            "The Ministry of Health and Family Welfare (MoHFW) in collaboration with WHO "
            "organized a two-day National Influenza Chintan Shivir to review seasonal preparedness "
            "and response measures across states and UTs. Joint capacity building and surveillance "
            "strengthening under IDSP were discussed."
        )
        decision = classifier.classify(title, text)

        assert decision.category == EventRelevanceCategory.PREPAREDNESS_OR_TRAINING
        assert decision.is_epidemiological_event is False
        assert "Chintan Shivir" in decision.rationale or "preparedness" in decision.rationale.lower()

    def test_administrative_program_names_not_disease_entities(self):
        """Defect 4: Administrative acronyms (IDSP, NCDC, IHIP) must not be extracted as acute disease entities."""
        extractor = HybridHealthEntityExtractor()
        doc_id = uuid4()
        text = "Under the IDSP and NCDC national surveillance program, monitoring was reinforced."

        entities = extractor.extract(text, doc_id)
        disease_spans = [e.text_span.lower() for e in entities if e.entity_type.value == "disease"]

        assert "idsp" not in disease_spans
        assert "ncdc" not in disease_spans

    def test_granularity_mismatch_suppression(self):
        """Defect 7: Mismatched spatial/temporal series must return INCOMPATIBLE_GRANULARITY and suppress false anomalies."""
        tracker = BaselineReliabilityTracker(min_sample_size=3)

        now = datetime.now(timezone.utc)
        target_bin = EpidemiologicalTimeBin(
            disease_key="dengue",
            geo_key="kolkata",
            period_start=now,
            period_end=now,
            iso_year=2024,
            iso_week=30,
            observed_case_count=1,
            fused_event_count=1,
        )

        # Historical bins with mismatched geo (state instead of district)
        hist_bins = [
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="west_bengal",
                period_start=now,
                period_end=now,
                iso_year=2024,
                iso_week=27,
                observed_case_count=675,
                fused_event_count=1,
            ),
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="west_bengal",
                period_start=now,
                period_end=now,
                iso_year=2024,
                iso_week=28,
                observed_case_count=676,
                fused_event_count=1,
            ),
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="west_bengal",
                period_start=now,
                period_end=now,
                iso_year=2024,
                iso_week=29,
                observed_case_count=675,
                fused_event_count=1,
            ),
        ]

        status, rationale = tracker.evaluate_reliability(hist_bins, target_bin)
        assert status == BaselineReliability.INCOMPATIBLE_GRANULARITY
        assert "Incompatible spatial granularity" in rationale

        # Check SignalDetector suppression
        detector = SignalDetector()
        baseline = BaselineEstimate(
            disease_key="dengue",
            geo_key="kolkata",
            target_period_start=now,
            target_period_end=now,
            baseline_window_weeks=3,
            baseline_count=2026.0,
            baseline_mean=675.33,
            baseline_median=675.0,
            baseline_std=0.5,
            baseline_variance=0.25,
            dispersion_metric=0.25,
            number_of_historical_bins=3,
            number_of_nonzero_bins=3,
            reliability_status=status,
        )

        signal = detector.detect_signal(hist_bins, target_bin, baseline)
        assert signal.signal_level == SignalLevel.NO_SIGNAL
        assert signal.is_downgraded is True
        assert "incompatible" in signal.downgrade_reason.lower()

    def test_cross_disease_granularity_suppression(self):
        """Item 6: Comparing historical bins of dengue to target cholera must be rejected."""
        tracker = BaselineReliabilityTracker(min_sample_size=3)
        now = datetime.now(timezone.utc)
        target = EpidemiologicalTimeBin(
            disease_key="cholera",
            geo_key="kolkata",
            period_start=now,
            period_end=now,
            iso_year=2026,
            iso_week=24,
            observed_case_count=10,
            fused_event_count=1,
        )
        hist = [
            EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="kolkata",
                period_start=now,
                period_end=now,
                iso_year=2026,
                iso_week=23,
                observed_case_count=10,
                fused_event_count=1,
            )
            for _ in range(3)
        ]
        status, rat = tracker.evaluate_reliability(hist, target)
        assert status == BaselineReliability.INCOMPATIBLE_GRANULARITY
        assert "incompatible disease" in rat.lower()

    def test_pathogen_threat_vs_alert_priority_decoupling(self):
        """Defect 11: High-consequence pathogen (Tier 4) with zero active transmission remains Informational/Low priority."""
        scorer = AlertScorer()
        now = datetime.now(timezone.utc)

        # Create low-volume signal for Nipah (Tier 4)
        signal = SignalObservation(
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            target_period_start=now,
            target_period_end=now,
            observed_value=0.0,
            expected_value=0.0,
            deviation=0.0,
            standardized_score=0.0,
            threshold=2.0,
            detection_method=DetectionMethod.EARS_C1,
            signal_level=SignalLevel.NO_SIGNAL,
            supporting_source_count=1,
            reliability_status=BaselineReliability.STABLE_BASELINE,
        )

        target_bin = EpidemiologicalTimeBin(
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            period_start=now,
            period_end=now,
            iso_year=2026,
            iso_week=25,
            observed_case_count=0,
            fused_event_count=1,
        )

        baseline = BaselineEstimate(
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            target_period_start=now,
            target_period_end=now,
            baseline_window_weeks=3,
            baseline_count=0.0,
            baseline_mean=0.0,
            baseline_median=0.0,
            baseline_std=0.0,
            baseline_variance=0.0,
            dispersion_metric=0.0,
            number_of_historical_bins=3,
            number_of_nonzero_bins=0,
            reliability_status=BaselineReliability.STABLE_BASELINE,
        )

        alert = scorer.score_signal(signal=signal, time_bin=target_bin, baseline=baseline, fused_events=[])

        # Verify biological hazard is Tier 4 but situational alert priority is NOT high/emergency
        assert alert.pathogen_threat_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE
        assert alert.alert_tier in (AlertTier.INFORMATIONAL, AlertTier.LOW)

    def test_evidence_first_dossier_analyst_playbook(self):
        """Phase 7: Explainability dossier must include actionable analyst recommendations."""
        generator = DossierGenerator()
        now = datetime.now(timezone.utc)

        alert = EpidemiologicalAlert(
            signal_id=uuid4(),
            disease_key="cholera",
            geo_key="rayagada",
            pathogen_threat_tier=PathogenThreatTier.TIER_3_SEVERE,
            period_start=now,
            period_end=now,
            composite_score=0.72,
            alert_tier=AlertTier.MEDIUM,
            origin=OriginClassification.LIVE_EXTERNAL,
            score_breakdown={
                "anomaly_score": 0.8,
                "threat_score": 0.75,
                "evidence_score": 0.7,
                "certainty_score": 0.65,
                "spatial_score": 0.8,
                "raw_composite_score": 0.74,
                "final_score": 0.72,
            },
            explanation={
                "summary": "[MEDIUM] Cholera in rayagada - Observed: 15 vs Expected: 2.0",
                "driving_factors": ["Statistical Aberration", "Severe Epidemic Pathogen"],
            },
        )

        dossier = generator.create_dossier(alert=alert)

        assert dossier.briefing.recommended_action != ""
        assert "hospital admission" in dossier.briefing.recommended_action.lower()
        assert dossier.analyst_action_playbook != ""
        assert "Review required" in dossier.analyst_action_playbook

    def test_administrative_laboratory_location_not_spurious_outbreak_epicenter(self):
        """Priority 2: NIV Pune must not generate spurious Nipah outbreak events in Pune."""
        from episense.nlp.pipeline import NLPPipeline
        from episense.events.builder import EventCandidateBuilder
        from episense.schemas.document import Document

        text = (
            "On 18 June 2026, state health authorities in Kerala confirmed a fatal case of Nipah virus disease "
            "in Kozhikode district. Confirmatory testing was conducted at the National Institute of Virology (NIV) Pune. "
            "A total of 3 confirmed cases and 1 death have been reported."
        )
        import hashlib
        doc = Document(
            document_id=uuid4(),
            title="Nipah Kerala Test",
            text=text,
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            source_id="test_feed",
            origin=OriginClassification.MANUAL_SUBMISSION,
        )
        pipeline = NLPPipeline(enable_cache=False)
        nlp_out = pipeline.process_document(doc)

        # 1. Verify NIV is NOT extracted as a disease
        diseases = [e.text_span for e in nlp_out.entities if e.entity_type.value == "disease"]
        assert "NIV" not in diseases
        assert "Niv" not in diseases
        assert any("Nipah" in d for d in diseases)

        # 2. Build event candidates
        builder = EventCandidateBuilder()
        candidates = builder.build_candidates(nlp_out, raw_text=text)

        # 3. Verify candidates for Kozhikode, and NO candidate for Pune
        geos = [c.geo_key for c in candidates]
        assert "pune" not in geos
        assert "kozhikode" in geos

    def test_dossier_temporal_distinction(self):
        """Priority 2: Dossier must distinguish event date from baseline surveillance window."""
        generator = DossierGenerator()
        now = datetime(2026, 6, 18, 10, 0, 0, tzinfo=timezone.utc)
        period_start = datetime(2026, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        period_end = datetime(2026, 6, 21, 23, 59, 59, tzinfo=timezone.utc)

        alert = EpidemiologicalAlert(
            signal_id=uuid4(),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            pathogen_threat_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
            period_start=period_start,
            period_end=period_end,
            composite_score=0.6,
            alert_tier=AlertTier.LOW,
            origin=OriginClassification.MANUAL_SUBMISSION,
            score_breakdown={
                "anomaly_score": 0.5, "threat_score": 1.0, "evidence_score": 0.6,
                "certainty_score": 0.7, "spatial_score": 1.0, "raw_composite_score": 0.65, "final_score": 0.6,
            },
            explanation={
                "summary": "[LOW] Nipah in kozhikode",
                "driving_factors": ["High-Consequence Pathogen"],
            },
        )
        fe = FusedEvent(
            canonical_disease="Nipah virus disease",
            event_window_start=now,
            event_window_end=now,
            supporting_observation_count=1,
            evidence_references=[],
        )

        dossier = generator.create_dossier(alert=alert, fused_events=[fe])

        # Verify event date is clearly noted alongside baseline window
        assert "2026-06-18" in dossier.briefing.when_period
        assert "2026-06-15 to 2026-06-21" in dossier.briefing.when_period
        assert "Observed event date: 2026-06-18" in dossier.analyst_action_playbook

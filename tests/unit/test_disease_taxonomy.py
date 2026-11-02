"""
Unit Tests for EpiSense Epidemiological Disease Taxonomy and Threat Classification.
Validates:
1. Formal taxonomy categories (INFECTIOUS_DISEASE, PATHOGEN, SYNDROME, EVENT_CATEGORY, NON_COMMUNICABLE_CONDITION, ALIAS).
2. Proper classification and outbreak eligibility of non-communicable conditions (Cardiovascular disease).
3. Proper classification of syndromes and public health event categories (Acute Diarrheal Disease, Food Poisoning).
4. PathogenThreatClassifier scoring, including 0.0 threat score for NON_COMMUNICABLE_CONDITION.
5. Safety gating in AlertScorer ensuring non-communicable conditions can never trigger acute epidemic alert tiers.
"""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from episense.taxonomy.models import (
    CanonicalTaxonomyEntry,
    TaxonomyCategory,
    TaxonomyMatch,
)
from episense.taxonomy.registry import (
    DEFAULT_TAXONOMY_REGISTRY,
    TaxonomyRegistry,
)
from episense.scoring.threat import PathogenThreatClassifier
from episense.scoring.scorer import AlertScorer
from episense.schemas.alert import AlertTier, PathogenThreatTier
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    SignalLevel,
    SignalObservation,
)
from episense.schemas.event import FusedEvent, MatchDecision
from episense.schemas.assertion import AssertionStatus
from episense.nlp.entities.normalizer import EntityNormalizer


class TestDiseaseTaxonomy:
    """Verifies formal categorization and properties across the disease taxonomy."""

    def test_canonical_categories_defined(self):
        """Confirm that all six required taxonomy categories exist in TaxonomyCategory."""
        categories = {c.value for c in TaxonomyCategory}
        assert "infectious_disease" in categories
        assert "pathogen" in categories
        assert "syndrome" in categories
        assert "event_category" in categories
        assert "non_communicable_condition" in categories
        assert "alias" in categories

    def test_cardiovascular_disease_is_non_communicable_and_cannot_outbreak(self):
        """Confirm that cardiovascular disease is classified as NON_COMMUNICABLE_CONDITION with outbreak eligibility False."""
        match = DEFAULT_TAXONOMY_REGISTRY.resolve("cardiovascular disease")
        assert match is not None
        assert match.canonical_id == "cardiovascular_disease"
        assert match.category == TaxonomyCategory.NON_COMMUNICABLE_CONDITION
        assert match.can_cause_outbreak is False
        assert match.pathogen_tier == PathogenThreatTier.NONE
        assert match.icd10_code == "ICD10:I51.9"

        # Check alias 'heart disease'
        alias_match = DEFAULT_TAXONOMY_REGISTRY.resolve("heart disease")
        assert alias_match is not None
        assert alias_match.canonical_id == "cardiovascular_disease"
        assert alias_match.can_cause_outbreak is False

    def test_acute_diarrheal_disease_is_syndrome(self):
        """Confirm that Acute Diarrheal Disease is classified as SYNDROME with outbreak eligibility True."""
        match = DEFAULT_TAXONOMY_REGISTRY.resolve("acute diarrheal disease")
        assert match is not None
        assert match.canonical_id == "acute_diarrheal_disease"
        assert match.category == TaxonomyCategory.SYNDROME
        assert match.can_cause_outbreak is True

    def test_food_poisoning_is_event_category(self):
        """Confirm that Food Poisoning is classified as EVENT_CATEGORY with outbreak eligibility True."""
        match = DEFAULT_TAXONOMY_REGISTRY.resolve("food poisoning")
        assert match is not None
        assert match.canonical_id == "food_poisoning"
        assert match.category == TaxonomyCategory.EVENT_CATEGORY
        assert match.can_cause_outbreak is True

    def test_nipah_is_high_consequence_infectious_disease(self):
        """Confirm that Nipah virus is classified as INFECTIOUS_DISEASE with TIER_4_HIGH_CONSEQUENCE."""
        match = DEFAULT_TAXONOMY_REGISTRY.resolve("Nipah virus")
        assert match is not None
        assert match.canonical_id == "nipah_virus"
        assert match.category == TaxonomyCategory.INFECTIOUS_DISEASE
        assert match.can_cause_outbreak is True
        assert match.pathogen_tier == PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE

    def test_covid19_alias_normalization(self):
        """Confirm that COVID-19, SARS-CoV-2, and coronavirus resolve to COVID-19."""
        for term in ["COVID-19", "covid-19", "SARS-CoV-2", "coronavirus"]:
            match = DEFAULT_TAXONOMY_REGISTRY.resolve(term)
            assert match is not None
            assert "covid" in match.canonical_id or "sars_cov" in match.canonical_id

    def test_threat_classifier_non_communicable_scores_zero(self):
        """Confirm that PathogenThreatClassifier assigns PathogenThreatTier.NONE and 0.0 score to NCDs."""
        classifier = PathogenThreatClassifier()

        tier = classifier.classify("cardiovascular disease")
        assert tier == PathogenThreatTier.NONE
        score = classifier.get_score(tier)
        assert score == 0.0

        # Also for heart disease alias
        tier_alias = classifier.classify("heart disease")
        assert tier_alias == PathogenThreatTier.NONE
        assert classifier.get_score(tier_alias) == 0.0

    def test_threat_classifier_infectious_threat_hierarchy(self):
        """Confirm the threat tier hierarchy: Nipah (1.0) > Cholera (0.75) > Dengue (0.50) > Food Poisoning (0.25)."""
        classifier = PathogenThreatClassifier()

        score_nipah = classifier.get_score(classifier.classify("nipah"))
        score_cholera = classifier.get_score(classifier.classify("cholera"))
        score_dengue = classifier.get_score(classifier.classify("dengue"))
        score_fp = classifier.get_score(classifier.classify("food poisoning"))

        assert score_nipah == 1.00
        assert score_cholera == 0.75
        assert score_dengue == 0.50
        assert score_fp == 0.25
        assert score_nipah > score_cholera > score_dengue > score_fp

    def test_alert_scorer_locks_non_communicable_to_informational(self):
        """Confirm that AlertScorer locks non-communicable conditions to INFORMATIONAL tier and records gating reason."""
        scorer = AlertScorer()

        # Signal for cardiovascular disease
        signal = SignalObservation(
            signal_id=uuid4(),
            disease_key="cardiovascular disease",
            geo_key="india",
            target_period_start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            target_period_end=datetime(2026, 6, 7, tzinfo=timezone.utc),
            observed_value=100.0,
            expected_value=10.0,
            deviation=90.0,
            threshold=2.0,
            signal_level=SignalLevel.STRONG_SIGNAL,
            detection_method=DetectionMethod.EARS_C3,
            standardized_score=4.5,
            supporting_source_count=5,
            reliability_status=BaselineReliability.STABLE_BASELINE,
        )

        alert = scorer.score_signal(signal=signal)

        # Must be locked to INFORMATIONAL despite high count, high Z-score, and multi-source
        assert alert.alert_tier == AlertTier.INFORMATIONAL
        assert alert.is_gated is True
        assert alert.gating_reason is not None
        assert "Non-communicable condition" in alert.gating_reason
        assert alert.composite_score < 0.40

    def test_entity_normalizer_integration(self):
        """Confirm EntityNormalizer returns rich TaxonomyMatch."""
        name, icd = EntityNormalizer.normalize_disease("cardiovascular disease")
        assert name == "Cardiovascular Disease"
        assert icd == "ICD10:I51.9"

        match = EntityNormalizer.normalize_concept("cardiovascular disease")
        assert match is not None
        assert match.category == TaxonomyCategory.NON_COMMUNICABLE_CONDITION
        assert match.can_cause_outbreak is False

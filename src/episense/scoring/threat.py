"""
Pathogen Clinical Threat Classification Engine for EpiSense (Phase 9).
Categorizes pathogens into public health consequence tiers and provides
calibrated baseline threat weights.
"""

from typing import Dict, Optional
from episense.schemas.alert import PathogenThreatTier
from episense.taxonomy.models import TaxonomyCategory
from episense.taxonomy.registry import DEFAULT_TAXONOMY_REGISTRY


class PathogenThreatClassifier:
    """
    Deterministic classifier assigning pathogens to public health clinical threat tiers.
    """

    # Exact and canonical pathogen mappings
    THREAT_MAP: Dict[str, PathogenThreatTier] = {
        # Non-communicable or non-pathogen (Tier 0 / None)
        "cardiovascular disease": PathogenThreatTier.NONE,
        "heart disease": PathogenThreatTier.NONE,
        "lung disease": PathogenThreatTier.NONE,
        "chronic respiratory disease": PathogenThreatTier.NONE,
        "diabetes": PathogenThreatTier.NONE,
        "diabetes mellitus": PathogenThreatTier.NONE,
        "hypertension": PathogenThreatTier.NONE,
        "stroke": PathogenThreatTier.NONE,

        # Tier 4: High Consequence / High CFR / Emerging Zoonotic
        "nipah": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "nipah virus": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "nipah virus disease": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "marburg": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "marburg virus": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "marburg virus disease": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "ebola": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "ebola virus disease": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "avian influenza": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "bird flu": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "influenza a(h5n1)": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "chandipura": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "chandipura virus": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "mers-cov": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "middle east respiratory syndrome": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "yellow fever": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "yellow fever virus infection": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "crimean-congo hemorrhagic fever": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "crimean-congo haemorrhagic fever": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "cchf": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        "lassa fever": PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,

        # Tier 3: Severe Epidemic / High Morbidity-Mortality
        "cholera": PathogenThreatTier.TIER_3_SEVERE,
        "kyasanur forest disease": PathogenThreatTier.TIER_3_SEVERE,
        "kfd": PathogenThreatTier.TIER_3_SEVERE,
        "rabies": PathogenThreatTier.TIER_3_SEVERE,
        "japanese encephalitis": PathogenThreatTier.TIER_3_SEVERE,
        "leptospirosis": PathogenThreatTier.TIER_3_SEVERE,
        "meningococcal disease": PathogenThreatTier.TIER_3_SEVERE,
        "meningitis": PathogenThreatTier.TIER_3_SEVERE,
        "anthrax": PathogenThreatTier.TIER_3_SEVERE,
        "diphtheria": PathogenThreatTier.TIER_3_SEVERE,
        "plague": PathogenThreatTier.TIER_3_SEVERE,

        # Tier 2: Endemic Outbreak-Prone / Vector-Borne
        "dengue": PathogenThreatTier.TIER_2_MODERATE,
        "dengue fever": PathogenThreatTier.TIER_2_MODERATE,
        "malaria": PathogenThreatTier.TIER_2_MODERATE,
        "malaria (falciparum)": PathogenThreatTier.TIER_2_MODERATE,
        "chikungunya": PathogenThreatTier.TIER_2_MODERATE,
        "scrub typhus": PathogenThreatTier.TIER_2_MODERATE,
        "measles": PathogenThreatTier.TIER_2_MODERATE,
        "zika": PathogenThreatTier.TIER_2_MODERATE,
        "zika virus disease": PathogenThreatTier.TIER_2_MODERATE,
        "mpox": PathogenThreatTier.TIER_2_MODERATE,
        "monkeypox": PathogenThreatTier.TIER_2_MODERATE,
        "typhoid": PathogenThreatTier.TIER_2_MODERATE,
        "enteric fever": PathogenThreatTier.TIER_2_MODERATE,
        "hepatitis a": PathogenThreatTier.TIER_2_MODERATE,
        "hepatitis e": PathogenThreatTier.TIER_2_MODERATE,
        "pertussis": PathogenThreatTier.TIER_2_MODERATE,
        "mumps": PathogenThreatTier.TIER_2_MODERATE,
        "rubella": PathogenThreatTier.TIER_2_MODERATE,

        # Tier 1: Mild / Syndromic / Generic Endemic
        "disease/illness": PathogenThreatTier.TIER_1_MILD,
        "infection": PathogenThreatTier.TIER_1_MILD,
        "viral fever": PathogenThreatTier.TIER_1_MILD,
        "respiratory syncytial virus": PathogenThreatTier.TIER_1_MILD,
        "rsv": PathogenThreatTier.TIER_1_MILD,
        "influenza": PathogenThreatTier.TIER_1_MILD,
        "influenza a(h1n1)": PathogenThreatTier.TIER_1_MILD,
        "focal disease": PathogenThreatTier.TIER_1_MILD,
        "enteric disease": PathogenThreatTier.TIER_1_MILD,
        "syndrome": PathogenThreatTier.TIER_1_MILD,
        "sudden high fever": PathogenThreatTier.TIER_1_MILD,
        "persistent fever": PathogenThreatTier.TIER_1_MILD,
    }

    TIER_SCORES: Dict[PathogenThreatTier, float] = {
        PathogenThreatTier.NONE: 0.00,
        PathogenThreatTier.TIER_1_MILD: 0.25,
        PathogenThreatTier.TIER_2_MODERATE: 0.50,
        PathogenThreatTier.TIER_3_SEVERE: 0.75,
        PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE: 1.00,
    }

    def __init__(self, custom_map: Optional[Dict[str, PathogenThreatTier]] = None):
        self.mapping = dict(self.THREAT_MAP)
        if custom_map:
            self.mapping.update(custom_map)

    def classify(self, disease_key: str) -> PathogenThreatTier:
        """
        Classifies a disease key into a PathogenThreatTier deterministically.
        """
        cleaned = disease_key.lower().strip()

        # Check structured taxonomy match first
        match = DEFAULT_TAXONOMY_REGISTRY.resolve(cleaned)
        if match:
            if not match.can_cause_outbreak or match.category == TaxonomyCategory.NON_COMMUNICABLE_CONDITION:
                return PathogenThreatTier.NONE
            return match.pathogen_tier

        if cleaned in self.mapping:
            return self.mapping[cleaned]

        # Substring / keyword match fallback
        for k, tier in self.mapping.items():
            if k in cleaned or cleaned in k:
                return tier

        # Default fallback for unknown pathogens: Tier 1 (Cautious baseline)
        return PathogenThreatTier.TIER_1_MILD

    def get_score(self, threat_tier: PathogenThreatTier) -> float:
        """
        Returns normalized threat score [0.0, 1.0] for the threat tier.
        """
        return self.TIER_SCORES.get(threat_tier, 0.25)

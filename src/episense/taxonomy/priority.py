"""
Authoritative 8 Priority Disease Registry for EpiSense Research Surveillance.

Defines the single source of truth for the eight canonical priority surveillance diseases:
1. Dengue
2. Malaria
3. Chikungunya
4. Leptospirosis
5. Cholera
6. Acute diarrhoeal disease (ADD)
7. Japanese encephalitis (JE)
8. Scrub typhus

This module is reused across backend ingestion, analytical services, data-sufficiency profiler,
forecasting feasibility gates, API endpoints, and frontend dashboard views.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel
from episense.schemas.alert import PathogenThreatTier
from episense.taxonomy.models import TaxonomyCategory


class PriorityDiseaseId(str, Enum):
    DENGUE = "dengue"
    MALARIA = "malaria"
    CHIKUNGUNYA = "chikungunya"
    LEPTOSPIROSIS = "leptospirosis"
    CHOLERA = "cholera"
    ACUTE_DIARRHOEAL_DISEASE = "acute_diarrhoeal_disease"
    JAPANESE_ENCEPHALITIS = "japanese_encephalitis"
    SCRUB_TYPHUS = "scrub_typhus"


class PriorityDiseaseMetadata(EpiSenseBaseModel):
    """Authoritative metadata record for a canonical priority surveillance disease."""
    canonical_id: PriorityDiseaseId
    canonical_name: str
    icd10_code: str
    category: TaxonomyCategory
    pathogen_tier: PathogenThreatTier
    transmission_mode: str
    is_syndromic: bool = False
    aliases: List[str] = Field(default_factory=list)
    description: str


# Master 8 Canonical Priority Diseases Catalog
PRIORITY_DISEASES: List[PriorityDiseaseMetadata] = [
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.DENGUE,
        canonical_name="Dengue",
        icd10_code="ICD10:A90",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        transmission_mode="Vector-borne (Aedes aegypti / albopictus)",
        is_syndromic=False,
        aliases=[
            "dengue",
            "dengue fever",
            "suspected dengue",
            "breakbone fever",
            "dengue hemorrhagic fever",
            "dhf",
            "dengue shock syndrome",
            "dss",
            "severe dengue",
        ],
        description="Endemic arboviral flavivirus causing acute febrile illness, plasma leakage, and hemorrhagic manifestations.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.MALARIA,
        canonical_name="Malaria",
        icd10_code="ICD10:B54",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        transmission_mode="Vector-borne (Anopheles mosquitoes)",
        is_syndromic=False,
        aliases=[
            "malaria",
            "plasmodium falciparum",
            "plasmodium vivax",
            "falciparum malaria",
            "vivax malaria",
            "p. falciparum",
            "p. vivax",
        ],
        description="Parasitic protozoan infection caused by Plasmodium species presenting with paroxysmal fever and chills.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.CHIKUNGUNYA,
        canonical_name="Chikungunya",
        icd10_code="ICD10:A92.0",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        transmission_mode="Vector-borne (Aedes aegypti / albopictus)",
        is_syndromic=False,
        aliases=[
            "chikungunya",
            "chikungunya fever",
            "chikv",
        ],
        description="Alphaviral febrile illness featuring debilitating, prolonged polyarthralgia and rash.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.LEPTOSPIROSIS,
        canonical_name="Leptospirosis",
        icd10_code="ICD10:A27",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        transmission_mode="Zoonotic / exposure to water/soil contaminated with rodent urine",
        is_syndromic=False,
        aliases=[
            "leptospirosis",
            "weil's disease",
            "rat fever",
            "leptospira",
        ],
        description="Bacterial spirochetal zoonosis frequent during post-monsoon urban flooding and paddy cultivation.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.CHOLERA,
        canonical_name="Cholera",
        icd10_code="ICD10:A00",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        transmission_mode="Waterborne / foodborne ingestion (Vibrio cholerae)",
        is_syndromic=False,
        aliases=[
            "cholera",
            "vibrio cholerae",
            "vibrio cholerae infection",
            "v. cholerae",
        ],
        description="Acute toxigenic intestinal infection causing rapid dehydration, rice-water stools, and hypovolemic shock.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.ACUTE_DIARRHOEAL_DISEASE,
        canonical_name="Acute Diarrhoeal Disease",
        icd10_code="ICD10:A09",
        category=TaxonomyCategory.SYNDROME,
        pathogen_tier=PathogenThreatTier.TIER_1_MILD,
        transmission_mode="Fecal-oral ingestion / waterborne",
        is_syndromic=True,
        aliases=[
            "acute diarrhoeal disease",
            "acute diarrheal disease",
            "acute diarrhea",
            "acute diarrhoea",
            "add",
            "diarrheal outbreak",
            "diarrhoeal outbreak",
            "acute gastroenteritis",
            "gastroenteritis",
            "age",
        ],
        description="Syndromic presentation of acute water/electrolyte loss without confirmed microbial isolation.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.JAPANESE_ENCEPHALITIS,
        canonical_name="Japanese Encephalitis",
        icd10_code="ICD10:A83.0",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_3_SEVERE,
        transmission_mode="Vector-borne (Culex tritaeniorhynchus / wading birds / swine)",
        is_syndromic=False,
        aliases=[
            "japanese encephalitis",
            "je",
            "japanese encephalitis virus",
            "jev",
        ],
        description="Flavivirus neuroinvasive encephalitis with high pediatric case-fatality and long-term neurological sequelae.",
    ),
    PriorityDiseaseMetadata(
        canonical_id=PriorityDiseaseId.SCRUB_TYPHUS,
        canonical_name="Scrub Typhus",
        icd10_code="ICD10:A75.3",
        category=TaxonomyCategory.INFECTIOUS_DISEASE,
        pathogen_tier=PathogenThreatTier.TIER_2_MODERATE,
        transmission_mode="Vector-borne (Leptotrombidium mite larvae / chiggers)",
        is_syndromic=False,
        aliases=[
            "scrub typhus",
            "bush typhus",
            "orientia tsutsugamushi",
            "o. tsutsugamushi",
        ],
        description="Acute febrile rickettsial illness transmitted by larval trombiculid mites, often presenting with an eschar.",
    ),
]

# Fast Lookup Maps
PRIORITY_BY_ID: Dict[str, PriorityDiseaseMetadata] = {
    d.canonical_id.value: d for d in PRIORITY_DISEASES
}
PRIORITY_BY_NAME: Dict[str, PriorityDiseaseMetadata] = {
    d.canonical_name.lower(): d for d in PRIORITY_DISEASES
}

# Inverted Alias Map
_ALIAS_TO_METADATA: Dict[str, PriorityDiseaseMetadata] = {}
for _entry in PRIORITY_DISEASES:
    _ALIAS_TO_METADATA[_entry.canonical_name.lower().strip()] = _entry
    for _alias in _entry.aliases:
        _ALIAS_TO_METADATA[_alias.lower().strip()] = _entry

PRIORITY_CANONICAL_NAMES: List[str] = [d.canonical_name for d in PRIORITY_DISEASES]
PRIORITY_CANONICAL_IDS: List[str] = [d.canonical_id.value for d in PRIORITY_DISEASES]


def resolve_priority_disease(mention_or_key: str) -> Optional[PriorityDiseaseMetadata]:
    """
    Deterministically resolves a raw mention or key to its canonical priority disease metadata.
    Returns None if the entity is not one of the eight priority diseases.
    NEVER silently coerces an ambiguous, unspecified, or non-priority condition.
    """
    clean = (mention_or_key or "").strip().lower()
    if not clean:
        return None

    # 1. Exact alias or key match
    if clean in _ALIAS_TO_METADATA:
        return _ALIAS_TO_METADATA[clean]
    if clean in PRIORITY_BY_ID:
        return PRIORITY_BY_ID[clean]

    # 2. Substring matching (longest alias first, with word boundaries where feasible)
    sorted_aliases = sorted(_ALIAS_TO_METADATA.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if len(alias) >= 4 and (f" {alias} " in f" {clean} " or clean == alias):
            return _ALIAS_TO_METADATA[alias]

    return None


def is_priority_disease(mention_or_key: str) -> bool:
    """Returns True if the entity resolves to one of the 8 canonical priority diseases."""
    return resolve_priority_disease(mention_or_key) is not None


def get_canonical_priority_name(mention_or_key: str) -> Optional[str]:
    """Returns the canonical display name if entity is a priority disease, else None."""
    meta = resolve_priority_disease(mention_or_key)
    return meta.canonical_name if meta else None


def list_priority_disease_metadata() -> List[Dict[str, Any]]:
    """Returns serialization-ready dictionary representations of all 8 priority diseases."""
    return [d.model_dump() for d in PRIORITY_DISEASES]

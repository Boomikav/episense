"""
Epidemiological Taxonomy Models for EpiSense.
Defines formal classifications for infectious diseases, pathogens, syndromes,
public health event categories, and non-communicable conditions.
"""

from enum import Enum
from typing import List, Optional
from pydantic import Field

from episense.schemas.base import EpiSenseBaseModel
from episense.schemas.alert import PathogenThreatTier


class TaxonomyCategory(str, Enum):
    """
    Formal epidemiological category for biomedical concepts.
    Prevents category errors (e.g. conflating non-communicable diseases or syndromes with infectious pathogens).
    """
    INFECTIOUS_DISEASE = "infectious_disease"          # Acute communicable disease entity (e.g. Dengue, Nipah Virus Disease)
    PATHOGEN = "pathogen"                              # Specific etiological biological agent (e.g. SARS-CoV-2, Vibrio cholerae)
    SYNDROME = "syndrome"                              # Clinical symptom complex without identified etiology (e.g. Acute Diarrheal Disease)
    EVENT_CATEGORY = "event_category"                  # Public health outbreak category / incident type (e.g. Food Poisoning)
    NON_COMMUNICABLE_CONDITION = "non_communicable_condition"  # Chronic or non-infectious pathology (e.g. Cardiovascular Disease)
    ALIAS = "alias"                                    # Alternate lexical surface form or abbreviation


class CanonicalTaxonomyEntry(EpiSenseBaseModel):
    """
    Standardized taxonomy entry linking surface terms to canonical definitions,
    ICD-10 codings, outbreak eligibility, and clinical threat tiers.
    """
    canonical_id: str
    canonical_name: str
    category: TaxonomyCategory
    icd10_code: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    pathogen_tier: PathogenThreatTier = PathogenThreatTier.TIER_1_MILD
    can_cause_outbreak: bool = True
    transmission_mode: Optional[str] = None
    description: Optional[str] = None


class TaxonomyMatch(EpiSenseBaseModel):
    """
    Result of resolving an entity mention against the canonical taxonomy.
    Preserves verbatim surface form and normalization provenance.
    """
    raw_span: str
    canonical_id: str
    canonical_name: str
    category: TaxonomyCategory
    icd10_code: Optional[str] = None
    matched_alias: str
    can_cause_outbreak: bool
    pathogen_tier: PathogenThreatTier

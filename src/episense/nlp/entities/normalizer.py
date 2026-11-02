"""
Entity Normalization Layer for EpiSense NLP Pipeline.
Maps canonical health entities to standardized codes (ICD-10) without fabricating IDs.
"""

from typing import Optional, Tuple
from episense.nlp.entities.taxonomy import DISEASE_LEXICON
from episense.taxonomy.models import TaxonomyMatch
from episense.taxonomy.registry import DEFAULT_TAXONOMY_REGISTRY


class EntityNormalizer:
    """
    Normalizes recognized entities to canonical standard concept representations.
    If an entity cannot be reliably mapped to a verified standard, retains
    the surface form and leaves normalized_value as None.
    """

    @staticmethod
    def normalize_disease(text_span: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (canonical_name, icd10_code).
        If unresolved, returns (None, None).
        """
        match = DEFAULT_TAXONOMY_REGISTRY.resolve(text_span)
        if match:
            return match.canonical_name, match.icd10_code

        clean = text_span.strip().lower()
        if clean in DISEASE_LEXICON:
            canonical_name, icd_code = DISEASE_LEXICON[clean]
            return canonical_name, icd_code

        # Sub-phrase match
        for term, (canonical_name, icd_code) in DISEASE_LEXICON.items():
            if term in clean:
                return canonical_name, icd_code

        return None, None

    @staticmethod
    def normalize_concept(text_span: str) -> Optional[TaxonomyMatch]:
        """
        Returns rich structured TaxonomyMatch with category and outbreak eligibility.
        """
        return DEFAULT_TAXONOMY_REGISTRY.resolve(text_span)

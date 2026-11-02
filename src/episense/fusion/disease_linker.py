"""
Deterministic Disease Linking and Canonicalization for EpiSense Event Fusion.
Evaluates semantic disease compatibility across observations.
"""

from typing import Optional, Tuple
from episense.nlp.entities.normalizer import EntityNormalizer
from episense.nlp.entities.taxonomy import DISEASE_LEXICON


class DiseaseLinker:
    """
    Evaluates whether two disease mentions refer to the same underlying condition.
    """

    def __init__(self):
        self.normalizer = EntityNormalizer()

    def canonicalize(self, mention: str) -> Tuple[str, Optional[str]]:
        """
        Returns (canonical_name, icd10_code).
        """
        canon, icd = self.normalizer.normalize_disease(mention)
        if canon:
            return canon, icd
        return mention.strip().title(), None

    def are_compatible(
        self, disease_a: str, icd_a: Optional[str], disease_b: str, icd_b: Optional[str]
    ) -> Tuple[bool, float, str]:
        """
        Evaluates disease compatibility.
        Returns (is_compatible, confidence_score, rationale).
        """
        clean_a = disease_a.strip().lower()
        clean_b = disease_b.strip().lower()

        # 1. Exact canonical name match
        if clean_a == clean_b:
            return True, 1.0, f"Exact canonical disease match: '{disease_a}'"

        # 2. ICD-10 code match
        if icd_a and icd_b and icd_a == icd_b:
            return True, 1.0, f"Matching ICD-10 ontology code: {icd_a}"

        # 3. Synonym dictionary lookup
        canon_a, _ = self.canonicalize(disease_a)
        canon_b, _ = self.canonicalize(disease_b)
        if canon_a.lower() == canon_b.lower():
            return True, 0.95, f"Synonym resolution to canonical: '{canon_a}'"

        # 4. Incompatible
        return False, 0.0, f"Diseases are distinct: '{disease_a}' vs '{disease_b}'"

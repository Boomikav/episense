"""
Health Named Entity Recognition Engine for EpiSense.
Implements EntityExtractor using a hybrid scispaCy candidate generator,
domain taxonomy classification, and strict character offset verification.
"""

import re
from typing import List, Optional, Tuple
from uuid import UUID

from spacy.language import Language
from spacy.tokens import Doc

from episense.interfaces.nlp import EntityExtractor
from episense.schemas.entity import Entity, EntityType
from episense.nlp.models import ModelManager
from episense.nlp.entities.taxonomy import DISEASE_LEXICON, SYMPTOM_LEXICON, POPULATION_LEXICON
from episense.nlp.entities.normalizer import EntityNormalizer
from episense.exceptions import NLPExtractionError


class HybridHealthEntityExtractor(EntityExtractor):
    """
    Hybrid Health Named Entity Extractor combining scispaCy candidate extraction,
    lexicon-based domain classification, and strict character-level provenance validation.
    """

    def __init__(self, sci_nlp: Optional[Language] = None, web_nlp: Optional[Language] = None):
        self.sci_nlp = sci_nlp or ModelManager.get_sci_model()
        self.web_nlp = web_nlp or ModelManager.get_web_model()
        self.normalizer = EntityNormalizer()

    def extract(self, text: str, document_id: UUID) -> List[Entity]:
        """
        Extracts health entities (diseases, symptoms, quantities, populations).
        Strictly guarantees text[e.start_char:e.end_char] == e.text_span.
        """
        if not text or not text.strip():
            return []

        candidates: List[Tuple[int, int, str, EntityType, Optional[str], float, str]] = []

        # 1. Direct Domain Lexicon Exact Pattern Search (Highest precision for known surveillance terms)
        candidates.extend(self._find_lexicon_matches(text))

        # 2. scispaCy candidate generation and classification
        sci_doc = self.sci_nlp(text)
        for ent in sci_doc.ents:
            classified = self._classify_biomedical_candidate(ent.text, ent.start_char, ent.end_char, text)
            if classified is not None:
                candidates.append(classified)

        # 3. Resolve overlaps deterministically
        resolved_candidates = self._resolve_overlaps(candidates)

        # 4. Construct Entity domain objects and strictly verify offsets
        entities: List[Entity] = []
        for start_char, end_char, span_text, ent_type, norm_val, conf, model_info in resolved_candidates:
            # Character offset safety check
            slice_text = text[start_char:end_char]
            if slice_text != span_text:
                raise NLPExtractionError(
                    f"Offset invariant violated for doc {document_id}: "
                    f"text[{start_char}:{end_char}]='{slice_text}' != '{span_text}'"
                )

            entity = Entity(
                document_id=document_id,
                entity_type=ent_type,
                text_span=span_text,
                normalized_value=norm_val,
                start_char=start_char,
                end_char=end_char,
                extraction_confidence=conf,
                model_info=model_info,
            )
            entities.append(entity)

        # Sort entities by start_char
        entities.sort(key=lambda e: (e.start_char, e.end_char))
        return entities

    def _find_lexicon_matches(self, text: str) -> List[Tuple[int, int, str, EntityType, Optional[str], float, str]]:
        matches = []

        # Diseases
        # Sort terms by descending length to match longest multi-word phrases first
        disease_terms = sorted(DISEASE_LEXICON.keys(), key=len, reverse=True)
        for term in disease_terms:
            if term.lower() in self.ADMINISTRATIVE_PROGRAM_BLACKLIST:
                continue
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
            for m in re.finditer(pattern, text, re.IGNORECASE):
                start, end = m.span()
                matched_text = text[start:end]
                _, icd_code = self.normalizer.normalize_disease(matched_text)
                matches.append((
                    start, end, matched_text, EntityType.DISEASE, icd_code, 0.95, "lexicon:disease"
                ))

        # Symptoms
        symptom_terms = sorted(SYMPTOM_LEXICON, key=len, reverse=True)
        for term in symptom_terms:
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
            for m in re.finditer(pattern, text, re.IGNORECASE):
                start, end = m.span()
                matched_text = text[start:end]
                matches.append((
                    start, end, matched_text, EntityType.SYMPTOM, None, 0.90, "lexicon:symptom"
                ))

        # Populations
        population_terms = sorted(POPULATION_LEXICON, key=len, reverse=True)
        for term in population_terms:
            pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
            for m in re.finditer(pattern, text, re.IGNORECASE):
                start, end = m.span()
                matched_text = text[start:end]
                matches.append((
                    start, end, matched_text, EntityType.POPULATION, None, 0.90, "lexicon:population"
                ))

        return matches

    ADMINISTRATIVE_PROGRAM_BLACKLIST = {
        "idsp", "ncdc", "ihip", "nvbdcp", "sari network", "ili network",
        "surveillance network", "health mission", "who", "mohfw", "cdc",
        "icmr", "niv", "nhm", "dgghs", "disease/illness", "disease", "illness",
        "infection prevention", "infection control", "infection prevention and control",
        "tested positive", "tested negative", "laboratory confirmed", "laboratory tested",
        "fear of infection", "hospital outbreak", "disease surveillance", "fever survey",
        "house fever survey", "fever with", "house to house survey",
    }

    def _classify_biomedical_candidate(
        self, span_text: str, start: int, end: int, full_text: str
    ) -> Optional[Tuple[int, int, str, EntityType, Optional[str], float, str]]:
        clean = span_text.strip().lower()

        # Blacklist administrative surveillance programs and agencies
        if clean in self.ADMINISTRATIVE_PROGRAM_BLACKLIST:
            return None

        # Blacklist clinical structures, facilities, and biological specimens
        if clean.endswith(("clinics", "clinic", "hospital", "hospitals", "center", "centres", "ward", "wards", "facility", "facilities")):
            return None
        if clean.endswith(("rna", "dna", "antigen", "antibody", "antibodies", "test", "tests", "sample", "samples", "specimen")):
            return None
        if clean.endswith(("survey", "surveys", "investigation", "surveillance", "screening", "activity", "activities", "control", "eradication")):
            return None
        if clean.endswith(("with", "of", "and", "or", "in", "for", "by", "to")):
            return None
        if clean in {"infection", "disease", "illness", "epidemic-prone disease", "vector-borne disease", "communicable disease", "infectious disease"}:
            return None

        # Symptoms containing fever (e.g. persistent fever, high fever, sudden high fever, acute fever)
        if re.search(r"\b(?:persistent|sudden|high|mild|intermittent|unexplained|acute)\s+fever\b", clean):
            return (start, end, span_text, EntityType.SYMPTOM, None, 0.88, "scispacy+heuristic:symptom")

        # Check if span contains disease cue
        if clean in DISEASE_LEXICON:
            _, icd = self.normalizer.normalize_disease(clean)
            return (start, end, span_text, EntityType.DISEASE, icd, 0.92, "scispacy+lexicon:disease")

        # Check if span contains symptom cue
        if clean in SYMPTOM_LEXICON:
            return (start, end, span_text, EntityType.SYMPTOM, None, 0.88, "scispacy+lexicon:symptom")

        # Check if span contains population cue
        if clean in POPULATION_LEXICON:
            return (start, end, span_text, EntityType.POPULATION, None, 0.85, "scispacy+lexicon:population")

        # Contextual heuristic for virus / disease / infection suffix (fever alone is a symptom)
        if re.search(r"\b(virus|syndrome|infection|disease)\b", clean):
            # Check if likely a disease
            _, icd = self.normalizer.normalize_disease(clean)
            return (start, end, span_text, EntityType.DISEASE, icd, 0.80, "scispacy:biomedical_disease")

        return None

    def _resolve_overlaps(
        self, candidates: List[Tuple[int, int, str, EntityType, Optional[str], float, str]]
    ) -> List[Tuple[int, int, str, EntityType, Optional[str], float, str]]:
        """
        Deterministic overlap resolution.
        Priority:
        1. Higher confidence / specificity
        2. Longer span length
        3. Earlier start_char
        """
        if not candidates:
            return []

        # Sort by start ascending, length descending, confidence descending
        candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), -c[5]))

        resolved: List[Tuple[int, int, str, EntityType, Optional[str], float, str]] = []

        for cand in candidates:
            c_start, c_end, c_text, c_type, c_norm, c_conf, c_src = cand
            overlap = False

            for i, res in enumerate(resolved):
                r_start, r_end, r_text, r_type, r_norm, r_conf, r_src = res

                # Check if spans overlap
                if max(c_start, r_start) < min(c_end, r_end):
                    overlap = True
                    # If current candidate is strictly longer and higher/equal confidence, replace
                    if (c_end - c_start) > (r_end - r_start) and c_conf >= r_conf:
                        resolved[i] = cand
                    break

            if not overlap:
                resolved.append(cand)

        return resolved

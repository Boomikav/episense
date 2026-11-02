"""
Geographic Toponym Extraction and Resolution Engine for EpiSense.
Implements LocationResolver with explicit resolved/ambiguous/unresolved states.
"""

import re
from typing import List, Optional
from spacy.language import Language

from episense.interfaces.nlp import LocationResolver
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.nlp import ResolvedLocation, ResolutionState
from episense.nlp.models import ModelManager
from episense.nlp.geospatial.gazetteer import LocalGazetteer, VERIFIED_RECORDS
from episense.exceptions import NLPExtractionError


class CautiousLocationResolver(LocationResolver):
    """
    Extracts geographic mentions using general English NER and resolves them
    against the verified local SQLite gazetteer without fabricating identifiers.
    """

    CLINICAL_TERM_BLACKLIST = {
        "microcephaly", "encephalitis", "fever", "syndrome", "infection",
        "disease", "illness", "outbreak", "cases", "deaths", "virus", "vaccine",
        "rt-pcr", "pcr", "sergentomyia", "elisa", "igm", "igg", "swab", "sample",
        "specimen", "qdenga", "nairo", "cchfv",
    }

    def __init__(self, gazetteer: Optional[LocalGazetteer] = None, nlp: Optional[Language] = None):
        self.gazetteer = gazetteer or LocalGazetteer()
        self.nlp = nlp or ModelManager.get_web_model()

    def resolve(self, text: str, context_hints: Optional[List[str]] = None) -> List[Location]:
        """
        Implements LocationResolver interface returning successfully resolved locations.
        """
        resolved_mentions = self.resolve_mentions(text, context_hints)
        locations: List[Location] = []
        for rm in resolved_mentions:
            if rm.resolution_state == ResolutionState.RESOLVED and rm.resolved_location:
                locations.append(rm.resolved_location)
        return locations

    def resolve_mentions(
        self, text: str, context_hints: Optional[List[str]] = None
    ) -> List[ResolvedLocation]:
        """
        Extracts toponym mentions, validates character offsets, and determines
        explicit resolution state (resolved, ambiguous, unresolved).
        """
        if not text or not text.strip():
            return []

        candidates = []

        # 1. Exact matches from verified local gazetteer (longest match first)
        gaz_names = sorted(list({r[0] for r in VERIFIED_RECORDS}), key=len, reverse=True)
        for name in gaz_names:
            pat = rf"(?<!\w){re.escape(name)}(?!\w)"
            for m in re.finditer(pat, text, re.IGNORECASE):
                c_start, c_end = m.span()
                # Exclude reference laboratory mentions (e.g. "NIV Pune", "CMC Vellore")
                prec_window = text[max(0, c_start - 35):c_start].lower()
                if re.search(r"\b(?:niv|icmr-niv|national institute of virology|cmc)\s*$", prec_window):
                    continue
                candidates.append((c_start, c_end, text[c_start:c_end]))

        # 1b. Tabular field extraction: "District: <District Name>" and "State: <State Name>"
        for table_pat in [
            re.compile(r"(?:District|Dist\.?)\s*:\s*([A-Za-z\s\-]+?)(?=\s*[\|,\n\.]|\s*$)", re.IGNORECASE),
            re.compile(r"(?:State)\s*:\s*([A-Za-z\s\-]+?)(?=\s*[\|,\n\.]|\s*$)", re.IGNORECASE),
        ]:
            for m in table_pat.finditer(text):
                val_start, val_end = m.span(1)
                val_text = text[val_start:val_end].strip()
                if val_text and len(val_text) > 2 and val_text.lower() not in self.CLINICAL_TERM_BLACKLIST:
                    # Strip trailing whitespace and match exact slice
                    stripped_val = val_text
                    actual_end = val_start + len(stripped_val)
                    candidates.append((val_start, actual_end, text[val_start:actual_end]))

        # 2. General NER extraction for other locations
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC"):
                start = ent.start_char
                end = ent.end_char
                span_text = text[start:end]

                # Strip leading "the "
                if span_text.lower().startswith("the "):
                    start += 4
                    span_text = text[start:end]

                # Strip trailing punctuation
                while end > start and text[end - 1] in (",", ".", ";", ":"):
                    end -= 1
                    span_text = text[start:end]

                span_text = span_text.strip()
                if not span_text or span_text.lower() in self.CLINICAL_TERM_BLACKLIST:
                    continue

                # Exclude reference laboratory mentions (e.g. "NIV Pune", "CMC Vellore")
                prec_window = text[max(0, start - 35):start].lower()
                if re.search(r"\b(?:niv|icmr-niv|national institute of virology|cmc)\s*$", prec_window):
                    continue

                # Exclude pathogen prefixes (e.g. "Nairo virus", "Chandipura virus", "Ebola virus")
                succ_window = text[end:min(len(text), end + 25)].lower()
                if re.match(r"^\s*(?:virus|pathogen|bacteria|strain|genus|serovar)\b", succ_window):
                    continue

                candidates.append((start, end, span_text))

        # Deduplicate candidates with longest span taking precedence
        candidates.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        deduped = []
        for cand in candidates:
            c_start, c_end, c_text = cand
            overlap = False
            for i, prev in enumerate(deduped):
                p_start, p_end, p_text = prev
                if max(c_start, p_start) < min(c_end, p_end):
                    overlap = True
                    if (c_end - c_start) > (p_end - p_start):
                        deduped[i] = cand
                    break
            if not overlap:
                deduped.append(cand)

        candidates = sorted(deduped, key=lambda x: x[0])

        results: List[ResolvedLocation] = []
        for start, end, span_text in candidates:
            slice_text = text[start:end]
            if slice_text != span_text:
                raise NLPExtractionError(
                    f"Geographic offset invariant violated: text[{start}:{end}]='{slice_text}' != '{span_text}'"
                )

            # Query gazetteer
            matches = self.gazetteer.lookup(span_text)

            if len(matches) == 1:
                state = ResolutionState.RESOLVED
                res_loc = matches[0]
                alt_locs = []
                conf = res_loc.confidence
            elif len(matches) > 1:
                # Check if all matches share the same parent or if truly ambiguous
                parents = {m.parent_location for m in matches}
                if len(parents) == 1:
                    # Consistent administrative parent
                    state = ResolutionState.RESOLVED
                    res_loc = matches[0]
                    alt_locs = matches[1:]
                    conf = 0.90
                else:
                    state = ResolutionState.AMBIGUOUS
                    res_loc = None
                    alt_locs = matches
                    conf = 0.50
            else:
                state = ResolutionState.UNRESOLVED
                res_loc = None
                alt_locs = []
                conf = 0.0

            results.append(
                ResolvedLocation(
                    raw_text=span_text,
                    start_char=start,
                    end_char=end,
                    resolution_state=state,
                    resolved_location=res_loc,
                    candidate_alternatives=alt_locs,
                    confidence=conf,
                )
            )

        return results

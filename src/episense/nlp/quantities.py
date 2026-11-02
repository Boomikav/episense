"""
Quantity and Epidemiological Case Count Extraction for EpiSense.
Extracts numeric counts, fatalities, hospital admissions, contacts, cohort sizes,
and durations with exact character offsets and strict semantic typing.
"""

import re
from typing import List, Optional, Tuple
from spacy.language import Language

from episense.schemas.nlp import QuantityMention, QuantitySemanticType
from episense.nlp.models import ModelManager
from episense.exceptions import NLPExtractionError

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100, "thousand": 1000
}


class QuantityExtractor:
    """
    Extracts structured epidemiological counts with units, semantic typing,
    and character provenance.
    """

    _WORD_KEYS = list(WORD_NUMBERS.keys())
    _COMPOUND_WORDS = rf"(?:(?:{'|'.join(_WORD_KEYS)})-(?:{'|'.join(_WORD_KEYS)}))"
    _NUMBER_TOKEN = rf"(?:\d{{1,3}}(?:,\d{{3}})+|\d+|{_COMPOUND_WORDS}|{'|'.join(_WORD_KEYS)})"

    COUNT_QUALIFIERS = (
        r"(?:(?:laboratory-confirmed|lab-confirmed|confirmed|suspected|probable|presumed|acute)\s+)?"
        r"(?:(?:pediatric|adult|clinical|child|infant|cerebrospinal\s+fluid|[a-zA-Z-]+)\s+){0,3}"
    )

    BASE_COUNT_UNITS = (
        r"(?:cases?|deaths?|fatalities?|admissions?|hospitalizations?|people tested|samples?|specimens?|contacts?|high-risk contacts?|"
        r"individuals?|participants?|subjects?|patients?|infections?)"
    )

    COUNT_UNITS = rf"(?:{COUNT_QUALIFIERS}{BASE_COUNT_UNITS})"

    NUMERIC_PATTERN = re.compile(
        rf"(?:(?:over|at least|more than|approximately|nearly)\s+)?"
        rf"(\b{_NUMBER_TOKEN}\b)\s+"
        rf"({COUNT_UNITS})",
        re.IGNORECASE,
    )

    STANDALONE_DIGIT_PATTERN = re.compile(r"\b(?:\d{1,3}(?:,\d{3})+|\d+)\b")

    def __init__(self, nlp: Optional[Language] = None):
        self.nlp = nlp or ModelManager.get_web_model()

    @staticmethod
    def classify_semantic_type(unit: str, context: str) -> QuantitySemanticType:
        """
        Assigns formal epidemiological semantics to extracted quantity units.
        Prevents population cohort sizes, test counts, and durations from being
        falsely aggregated into disease case counts.
        """
        u = (unit or "").lower()
        ctx = (context or "").lower()

        if any(k in u for k in ["death", "fatalit"]):
            return QuantitySemanticType.DEATH_COUNT
        if any(k in u for k in ["admit", "hospital"]):
            return QuantitySemanticType.HOSPITALIZATION
        if any(k in u for k in ["tested", "sample", "specimen", "swab"]):
            return QuantitySemanticType.TEST_COUNT
        if any(k in u for k in ["individual", "participant", "subject", "cohort", "population", "enrolled"]):
            return QuantitySemanticType.POPULATION_OR_COHORT
        if any(k in u for k in ["percent", "%", "rate", "ratio"]):
            return QuantitySemanticType.PERCENTAGE_OR_RATE
        if any(k in u for k in ["month", "year", "week", "day", "hour"]):
            return QuantitySemanticType.DURATION
        if "contact" in u:
            return QuantitySemanticType.OTHER_MEASUREMENT
        if any(k in u for k in ["case", "infection"]):
            # Check context: if preceded by "cohort of", "study of", "population of"
            if re.search(r"\b(?:cohort|study|sample|follow[- ]up|population)\s+(?:of\s+)?$", ctx):
                return QuantitySemanticType.POPULATION_OR_COHORT
            return QuantitySemanticType.CASE_COUNT
        if "patient" in u:
            if re.search(r"\b(?:cohort|study|sample|enrolled)\b", ctx):
                return QuantitySemanticType.POPULATION_OR_COHORT
            return QuantitySemanticType.CASE_COUNT

        return QuantitySemanticType.UNKNOWN

    def extract(self, text: str) -> List[QuantityMention]:
        """
        Extracts quantity mentions and guarantees text[start:end] == span_text.
        """
        if not text or not text.strip():
            return []

        candidates = []

        # 1. Regex pattern with explicit unit
        for m in self.NUMERIC_PATTERN.finditer(text):
            start, end = m.span(1)
            span_text = text[start:end]
            num_str, unit = m.groups()
            num_val = self._parse_number(num_str)

            # Prevent 4-digit calendar years (1900-2099) from being extracted as case counts
            if 1900 <= num_val <= 2099:
                prec_window = text[max(0, start - 25):start].lower()
                # Reject if preceded by temporal prepositions, dates, or punctuation
                if re.search(r"\b(?:in|during|since|until|from|for|year|dated|annual|season|between|throughout|as\s+of)\s+$", prec_window) or re.search(r"[,;:\(]\s*$", prec_window):
                    continue
                # Also reject if unit is generic "cases" rather than explicitly qualified "confirmed cases", "admissions", etc.
                if unit.lower() in ("cases", "infections", "patients", "count"):
                    continue

            # Check if part of hyphenated or slashed date (e.g. 2023-01-29)
            if start > 0 and text[start - 1] in "-/":
                continue
            if end < len(text) and text[end] in "-/":
                continue

            candidates.append((start, end, span_text, num_val, unit.lower()))

        # 2. Match standalone numbers in surveillance context (e.g. IDSP tables or bullet points: "178", "450")
        for m in self.STANDALONE_DIGIT_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]

            # Reject numbers that are part of dates or hyphenated codes (e.g. 2023-01-29, 12/04/2023)
            if start > 0 and text[start - 1] in "-/.":
                continue
            if end < len(text) and text[end] in "-/.":
                continue

            num_val = float(span_text.replace(",", ""))

            # Ignore 4-digit years (1900-2099) when matching standalone numbers without explicit count units
            if len(span_text) == 4 and 1900 <= num_val <= 2099:
                continue

            # Skip numbers immediately followed by non-clinical units (e.g., "140 districts", "18 States", "36 months")
            following_text = text[end:min(len(text), end + 25)].strip().lower()
            if re.match(r"^(?:districts?|states?|months?|years?|weeks?|days?|hours?|percent|%|pages?|centres?|facilities|doses|times|runs)", following_text):
                continue

            # Skip numbers immediately followed by calendar months (e.g. "15 August", "21 July", "28 April")
            if re.match(r"^(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b", following_text):
                continue

            prec_window = text[max(0, start - 30):start].lower()
            # Skip numbers preceded by temporal range prepositions
            if re.search(r"\b(?:between|from|dated|on|in|since)\s+(?:\d{1,2}\s+(?:and|to)\s+)?$", prec_window):
                if re.match(r"^(?:and|-)\s+\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", following_text):
                    continue

            # For small digits 0, 1, 2 without unit, only accept in tabular contexts (e.g. "No. of Cases: 0")
            if num_val in (0, 1, 2):
                if not re.search(r"(?:cases?|deaths?|fatalities?|admissions?)\s*:\s*$", prec_window):
                    continue

            # Check if immediately adjacent context contains epidemiological keywords
            context_window = text[max(0, start - 40):min(len(text), end + 40)].lower()
            if any(k in context_window for k in ["case", "death", "contact", "patient", "test", "admit", "positive"]):
                unit = "count"
                if "case" in context_window:
                    unit = "cases"
                elif "death" in context_window:
                    unit = "deaths"
                elif "contact" in context_window:
                    unit = "contacts"
                candidates.append((start, end, span_text, num_val, unit))

        # Resolve overlaps
        resolved = self._resolve_overlaps(candidates)

        results: List[QuantityMention] = []
        for start, end, span_text, num_val, unit in resolved:
            slice_text = text[start:end]
            if slice_text != span_text:
                raise NLPExtractionError(
                    f"Quantity offset invariant violated: text[{start}:{end}]='{slice_text}' != '{span_text}'"
                )

            # Extract surrounding context
            c_start = max(0, start - 30)
            c_end = min(len(text), end + 30)
            context = text[c_start:c_end]
            prec_text = text[max(0, start - 35):start]

            qty_type = self.classify_semantic_type(unit, prec_text)

            results.append(
                QuantityMention(
                    raw_text=span_text,
                    numeric_value=num_val,
                    unit=unit,
                    quantity_type=qty_type,
                    start_char=start,
                    end_char=end,
                    surrounding_context=context,
                )
            )

        results.sort(key=lambda q: (q.start_char, q.end_char))
        return results

    def _parse_number(self, num_str: str) -> Optional[float]:
        clean = num_str.strip().lower().replace(",", "")
        if clean.isdigit():
            return float(clean)
        if clean in WORD_NUMBERS:
            return float(WORD_NUMBERS[clean])
        if "-" in clean:
            parts = clean.split("-")
            if all(p in WORD_NUMBERS for p in parts):
                return float(sum(WORD_NUMBERS[p] for p in parts))
        return None

    def _resolve_overlaps(self, candidates):
        if not candidates:
            return []
        candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
        resolved = []
        for cand in candidates:
            c_start, c_end = cand[0], cand[1]
            overlap = False
            for i, res in enumerate(resolved):
                r_start, r_end = res[0], res[1]
                if max(c_start, r_start) < min(c_end, r_end):
                    overlap = True
                    if (c_end - c_start) > (r_end - r_start):
                        resolved[i] = cand
                    break
            if not overlap:
                resolved.append(cand)
        return resolved

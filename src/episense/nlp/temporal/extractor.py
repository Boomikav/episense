"""
Deterministic Temporal Expression Extraction and Normalization for EpiSense.
Implements TemporalExtractor using regex interval rules, explicit date formats,
duration semantics, and dateparser.
Prevents durations (e.g. "36 months", "14 days") from being falsely converted to calendar point dates.
"""

import calendar
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
from uuid import UUID

import dateparser
from spacy.language import Language

from episense.interfaces.nlp import TemporalExtractor
from episense.schemas.temporal import TemporalExpression, TemporalType, DatePrecision
from episense.nlp.models import ModelManager
from episense.exceptions import NLPExtractionError


class RuleBasedTemporalExtractor(TemporalExtractor):
    """
    Extracts explicit dates, relative dates, intervals, durations, and years with
    strict character offset validation.
    """

    MONTH_NAMES = (
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    )

    # Patterns for intervals, e.g., "12 and 18 January 2026", "between 12 and 15 September 2023"
    INTERVAL_PATTERN = re.compile(
        rf"(?:between\s+)?(?P<dates>(\d{{1,2}})\s+(?:and|to|-)\s+(\d{{1,2}})\s+({MONTH_NAMES})\s+(\d{{4}}))",
        re.IGNORECASE,
    )

    CROSS_MONTH_INTERVAL_PATTERN = re.compile(
        rf"(?:between\s+)?(?P<dates>(\d{{1,2}}\s+{MONTH_NAMES})\s+(?:through|to|and|-)\s+(\d{{1,2}}\s+{MONTH_NAMES}\s+\d{{4}}))",
        re.IGNORECASE,
    )

    # Standard explicit dates: "18 June 2026", "22 May 2024"
    EXPLICIT_DATE_PATTERN = re.compile(
        rf"(\b\d{{1,2}}\s+{MONTH_NAMES}\s+\d{{4}}\b)",
        re.IGNORECASE,
    )

    # Month Year: "August 2024"
    MONTH_YEAR_PATTERN = re.compile(
        rf"(\b{MONTH_NAMES}\s+\d{{4}}\b)",
        re.IGNORECASE,
    )

    # Numeric full dates: "30-12-2025", "01/01/2026", "30.12.2025"
    NUMERIC_DATE_PATTERN = re.compile(
        r"\b(?P<day>\d{1,2})[-/\.](?P<month>\d{1,2})[-/\.](?P<year>\d{4})\b"
    )

    # ISO numeric dates: "2025-12-30"
    ISO_DATE_PATTERN = re.compile(
        r"\b(?P<year>\d{4})[-/\.](?P<month>\d{1,2})[-/\.](?P<day>\d{1,2})\b"
    )

    # Standalone Year: "2004", "2023"
    STANDALONE_YEAR_PATTERN = re.compile(
        r"\b(19\d\d|20\d\d)\b"
    )

    # Season / Multi-year range: e.g. "2025–2026 season", "2025-2026", "2024-2025 influenza season"
    SEASON_RANGE_PATTERN = re.compile(
        r"\b(?P<y1>19\d\d|20\d\d)\s*[-–—/]\s*(?P<y2>19\d\d|20\d\d|\d{2})(?:\s+(?P<label>season|influenza season|epidemic season|period))?\b",
        re.IGNORECASE,
    )

    # Durations: "36 months", "14 days", "3 weeks"
    DURATION_PATTERN = re.compile(
        r"\b(?P<val>\d+)\s+(?P<unit>days?|weeks?|months?|years?|hours?)\b",
        re.IGNORECASE,
    )

    def __init__(self, web_nlp: Optional[Language] = None):
        self.nlp = web_nlp or ModelManager.get_web_model()

    def extract(self, text: str, reference_date: datetime) -> List[TemporalExpression]:
        """
        Extracts and normalizes temporal spans relative to reference_date.
        Durations are preserved with duration semantics rather than point dates.
        """
        if not text or not text.strip():
            return []

        # Ensure reference_date is timezone-aware
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)

        # Candidate tuple: (start, end, span_text, t_start, t_end, t_type, is_rel, conf, is_dur, dur_unit, dur_val, date_prec, p_start, p_end)
        candidates: List[Tuple[int, int, str, datetime, datetime, TemporalType, bool, float, bool, Optional[str], Optional[float], DatePrecision, datetime, datetime]] = []

        # 1. Regex interval pattern (highest priority for multi-date ranges)
        for m in self.CROSS_MONTH_INTERVAL_PATTERN.finditer(text):
            start, end = m.span("dates")
            span_text = text[start:end]
            g = m.groups()
            d1_month_str, d2_month_year_str = g[1], g[2]
            year = d2_month_year_str.split()[-1]
            t_start = dateparser.parse(f"{d1_month_str} {year}", settings={"TIMEZONE": "UTC"})
            t_end = dateparser.parse(d2_month_year_str, settings={"TIMEZONE": "UTC"})
            if t_start and t_end:
                if t_start.tzinfo is None:
                    t_start = t_start.replace(tzinfo=timezone.utc)
                if t_end.tzinfo is None:
                    t_end = t_end.replace(tzinfo=timezone.utc)
                candidates.append((start, end, span_text, t_start, t_end, TemporalType.INTERVAL, False, 0.95, False, None, None, DatePrecision.DAY, t_start, t_end))

        # 1a. Season / Multi-year range (e.g. "2025–2026 season", "2025-2026")
        for m in self.SEASON_RANGE_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            y1 = int(m.group("y1"))
            y2_str = m.group("y2")
            y2 = int(y2_str) if len(y2_str) == 4 else (y1 // 100 * 100 + int(y2_str))
            if 1900 <= y1 <= 2100 and 1900 <= y2 <= 2100 and y1 <= y2:
                dt_start = datetime(y1, 1, 1, tzinfo=timezone.utc)
                dt_end = datetime(y2, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                candidates.append((start, end, span_text, dt_start, dt_end, TemporalType.INTERVAL, False, 0.95, False, None, None, DatePrecision.YEAR, dt_start, dt_end))

        for m in self.INTERVAL_PATTERN.finditer(text):
            start, end = m.span("dates")
            span_text = text[start:end]
            g = m.groups()
            d1, d2, month, year = g[1], g[2], g[3], g[4]
            t_start = dateparser.parse(f"{d1} {month} {year}", settings={"TIMEZONE": "UTC"})
            t_end = dateparser.parse(f"{d2} {month} {year}", settings={"TIMEZONE": "UTC"})
            if t_start and t_end:
                if t_start.tzinfo is None:
                    t_start = t_start.replace(tzinfo=timezone.utc)
                if t_end.tzinfo is None:
                    t_end = t_end.replace(tzinfo=timezone.utc)
                candidates.append((start, end, span_text, t_start, t_end, TemporalType.INTERVAL, False, 0.95, False, None, None, DatePrecision.DAY, t_start, t_end))

        # 2. Explicit full dates (e.g., "25 July 2024", "18 June 2026")
        for m in self.EXPLICIT_DATE_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            dt = dateparser.parse(span_text, settings={"TIMEZONE": "UTC"})
            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                dt_end = dt.replace(hour=23, minute=59, second=59, microsecond=0)
                candidates.append((start, end, span_text, dt_start, dt_end, TemporalType.POINT, False, 0.95, False, None, None, DatePrecision.DAY, dt_start, dt_end))

        # 2a. Numeric dates (DD-MM-YYYY or DD/MM/YYYY)
        for m in self.NUMERIC_DATE_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            d = int(m.group("day"))
            mo = int(m.group("month"))
            y = int(m.group("year"))
            if 1 <= d <= 31 and 1 <= mo <= 12 and 1900 <= y <= 2100:
                dt_start = datetime(y, mo, d, 0, 0, 0, tzinfo=timezone.utc)
                dt_end = datetime(y, mo, d, 23, 59, 59, tzinfo=timezone.utc)
                candidates.append((start, end, span_text, dt_start, dt_end, TemporalType.POINT, False, 0.95, False, None, None, DatePrecision.DAY, dt_start, dt_end))

        # 2b. ISO numeric dates (YYYY-MM-DD)
        for m in self.ISO_DATE_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            d = int(m.group("day"))
            mo = int(m.group("month"))
            y = int(m.group("year"))
            if 1 <= d <= 31 and 1 <= mo <= 12 and 1900 <= y <= 2100:
                dt_start = datetime(y, mo, d, 0, 0, 0, tzinfo=timezone.utc)
                dt_end = datetime(y, mo, d, 23, 59, 59, tzinfo=timezone.utc)
                candidates.append((start, end, span_text, dt_start, dt_end, TemporalType.POINT, False, 0.95, False, None, None, DatePrecision.DAY, dt_start, dt_end))

        # 3. Month + Year (e.g. "August 2024", "July 2024")
        for m in self.MONTH_YEAR_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            dt = dateparser.parse(span_text, settings={"TIMEZONE": "UTC"})
            if dt:
                y = dt.year
                mo = dt.month
                _, last_day = calendar.monthrange(y, mo)
                p_start = datetime(y, mo, 1, 0, 0, 0, tzinfo=timezone.utc)
                p_end = datetime(y, mo, last_day, 23, 59, 59, tzinfo=timezone.utc)
                candidates.append((start, end, span_text, p_start, p_end, TemporalType.INTERVAL, False, 0.90, False, None, None, DatePrecision.MONTH, p_start, p_end))

        # 4. Standalone 4-digit years
        for m in self.STANDALONE_YEAR_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            year = int(span_text)

            # Reject future policy target years (e.g., "towards the 2030 target", "vision 2030")
            preceding_context = text[max(0, start - 30):start].lower()
            if year > reference_date.year + 1 or any(k in preceding_context for k in ["target", "vision", "goal", "towards"]):
                continue

            dt_start = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            dt_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            candidates.append((start, end, span_text, dt_start, dt_end, TemporalType.INTERVAL, False, 0.85, False, None, None, DatePrecision.YEAR, dt_start, dt_end))

        # 5. Regex explicit duration pattern: "36 months", "14 days", "3 weeks"
        for m in self.DURATION_PATTERN.finditer(text):
            start, end = m.span()
            span_text = text[start:end]
            val = float(m.group("val"))
            unit = m.group("unit").lower()
            # Durations are explicitly NOT point calendar dates!
            candidates.append((start, end, span_text, reference_date, reference_date, TemporalType.DURATION, False, 0.95, True, unit, val, DatePrecision.DAY, reference_date, reference_date))

        # 6. spaCy general date entity candidates (to catch relative terms like "yesterday", "last week")
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("DATE", "TIME"):
                span_text = ent.text.strip()
                start, end = ent.start_char, ent.end_char
                # Clean punctuation if at the edge
                while end > start and text[end - 1] in (",", ".", ";", ":"):
                    end -= 1
                    span_text = text[start:end]

                # Ignore pure digits with fewer than 4 characters (e.g. "42", "21")
                if span_text.isdigit() and len(span_text) < 4:
                    continue

                # If span matches a duration (e.g., "36 months"), handle as duration, NOT a calendar date!
                dur_match = self.DURATION_PATTERN.match(span_text)
                if dur_match:
                    val = float(dur_match.group("val"))
                    unit = dur_match.group("unit").lower()
                    candidates.append((start, end, span_text, reference_date, reference_date, TemporalType.DURATION, False, 0.95, True, unit, val, DatePrecision.DAY, reference_date, reference_date))
                    continue

                parsed = dateparser.parse(
                    span_text,
                    settings={
                        "RELATIVE_BASE": reference_date,
                        "PREFER_DATES_FROM": "past",
                        "TIMEZONE": "UTC",
                        "RETURN_AS_TIMEZONE_AWARE": True,
                    },
                )
                if parsed is not None:
                    # Reject future policy target years or unrealistic future years
                    preceding_context = text[max(0, start - 30):start].lower()
                    following_context = text[end:min(len(text), end + 30)].lower()
                    combined_ctx = f"{preceding_context} {following_context}"
                    if parsed.year > reference_date.year + 1 or any(k in combined_ctx for k in ["target", "vision", "goal", "milestone", "towards"]):
                        continue

                    is_rel = any(w in span_text.lower() for w in ["yesterday", "today", "ago", "last", "past", "recent"])
                    t_type = TemporalType.RELATIVE if is_rel else TemporalType.POINT
                    candidates.append((start, end, span_text, parsed, parsed, t_type, is_rel, 0.85, False, None, None, DatePrecision.DAY, parsed, parsed))

        # Resolve overlaps
        resolved = self._resolve_overlaps(candidates)

        # Build TemporalExpression objects with offset verification
        results: List[TemporalExpression] = []
        for start, end, span_text, t_start, t_end, t_type, is_rel, conf, is_dur, dur_unit, dur_val, date_prec, p_start, p_end in resolved:
            slice_text = text[start:end]
            if slice_text != span_text:
                raise NLPExtractionError(
                    f"Temporal offset invariant violated: text[{start}:{end}]='{slice_text}' != '{span_text}'"
                )

            expr = TemporalExpression(
                original_expression=span_text,
                normalized_start=t_start,
                normalized_end=t_end,
                start_char=start,
                end_char=end,
                temporal_type=t_type,
                date_precision=date_prec,
                event_date_precision=date_prec,
                event_period_start=p_start,
                event_period_end=p_end,
                is_relative=is_rel,
                is_duration=is_dur,
                duration_unit=dur_unit,
                duration_value=dur_val,
                confidence=conf,
            )
            results.append(expr)

        results.sort(key=lambda t: (t.start_char, t.end_char))
        return results

    def _resolve_overlaps(self, candidates):
        if not candidates:
            return []
        candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), -c[7]))
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

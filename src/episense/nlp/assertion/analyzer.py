"""
Rule-based Contextual Assertion and Negation Analyzer for EpiSense.
Implements AssertionAnalyzer distinguishing CONFIRMED, SUSPECTED, NEGATED,
HISTORICAL, and HYPOTHETICAL statuses with syntactic context.
"""

import re
from typing import List, Optional, Tuple
from spacy.language import Language

from episense.interfaces.nlp import AssertionAnalyzer
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.entity import Entity
from episense.nlp.models import ModelManager


class ContextualAssertionAnalyzer(AssertionAnalyzer):
    """
    Analyzes contextual epistemic assertion for extracted health entities
    using sentence-level and clause-level dependency cues.
    """

    NEGATION_TRIGGERS = [
        # Strict negation: exclude abbreviation "No." / "No:" for counts/tables (e.g. "No. of Cases: 28", "No. 12")
        r"\bno\b(?!\s*[\.:]\s*(?:of\s+)?(?:cases|deaths|patients|samples|admissions|affected|reports|specimens)\b)(?!\s*[\.:]\s*\d+)(?!\s*\.\s*of\b)",
        r"\bnot\b", r"\bneither\b", r"\bnever\b",
        r"\bnegative\b", r"\btested negative\b", r"\bruled out\b",
        r"\brefuted\b", r"\bdenied\b", r"\babsence of\b",
        r"\bno evidence of\b", r"\bfree from\b", r"\bzero cases\b",
        r"\bwithout\b"
    ]

    CONFIRMATION_TRIGGERS = [
        r"\bconfirmed\b", r"\blaboratory[- ]confirmed\b", r"\brt[- ]pcr confirmed\b",
        r"\btested positive\b", r"\bpositive for\b", r"\bdiagnosed\b",
        r"\bverified\b", r"\bsubstantiated\b", r"\bproven\b"
    ]

    SUSPECTED_TRIGGERS = [
        r"\bsuspected\b", r"\bprobable\b", r"\bpossible\b",
        r"\bunder investigation\b", r"\bpresumptive\b", r"\blikely\b",
        r"\bunidentified\b", r"\bunknown origin\b", r"\bclinical presentation\b"
    ]

    HISTORICAL_TRIGGERS = [
        r"\bpreviously\b", r"\bprevious outbreak\b", r"\bhistorical\b",
        r"\b(?:in|on|dated|during|since)\s+(?:[0-3]?\d\s+[a-zA-Z]+\s+)?\b(19\d\d|20[0-1]\d|202[0-5])\b",
        r"\bpast season\b",
        r"\blargest outbreak since\b", r"\bearlier episode\b", r"\bpast years\b",
        r"\bwas reported\b", r"\bwere reported\b",
        r"\bwas reported in \b(19\d\d|20[0-1]\d|202[0-5])\b",
    ]

    HYPOTHETICAL_TRIGGERS = [
        r"\bprevents?\b", r"\bprevention\b", r"\bpreparedness\b",
        r"\badvisory\b", r"\breview meeting\b", r"\bguidelines\b",
        r"\bvaccination\b", r"\broutine surveillance\b", r"\bprecaution\b",
        r"\bcontingency\b", r"\brisk of\b"
    ]

    def __init__(self, nlp: Optional[Language] = None):
        self.nlp = nlp or ModelManager.get_web_model()

    def analyze(self, text: str, entities: List[Entity]) -> List[Assertion]:
        """
        Determines epistemic status for each entity in context.
        Returns a corresponding list of Assertion objects aligned with entities.
        """
        if not entities:
            return []

        doc = self.nlp(text)
        assertions: List[Assertion] = []

        for entity in entities:
            assertion = self._analyze_entity(doc, entity, text)
            assertions.append(assertion)

        return assertions

    def _analyze_entity(self, doc, entity: Entity, raw_text: str) -> Assertion:
        # Find sentence containing the entity
        sent_span = None
        for s in doc.sents:
            if s.start_char <= entity.start_char and s.end_char >= entity.end_char:
                sent_span = s
                break

        if sent_span is None:
            # Fallback: extract window around entity
            w_start = max(0, entity.start_char - 100)
            w_end = min(len(raw_text), entity.end_char + 100)
            context_text = raw_text[w_start:w_end]
        else:
            context_text = sent_span.text

        # Find closest clause or local token window (15 tokens before and after entity)
        ent_start = entity.start_char
        ent_end = entity.end_char

        # Check for local clause boundary (commas, semicolons, conjunctions)
        local_window = self._extract_local_clause(raw_text, ent_start, ent_end)

        # 1. Negation detection
        is_negated, neg_evidence = self._check_triggers(local_window, self.NEGATION_TRIGGERS)

        # 2. Historical context detection
        is_historical, hist_evidence = self._check_triggers(context_text, self.HISTORICAL_TRIGGERS)

        # 3. Hypothetical / Advisory detection
        is_hypothetical, hypo_evidence = self._check_triggers(context_text, self.HYPOTHETICAL_TRIGGERS)

        # 4. Suspected detection
        is_suspected, susp_evidence = self._check_triggers(local_window, self.SUSPECTED_TRIGGERS)

        # 5. Confirmed detection
        is_confirmed, conf_evidence = self._check_triggers(local_window, self.CONFIRMATION_TRIGGERS)

        # Decision hierarchy:
        # Negation takes precedence for active status determination
        if is_negated:
            status = AssertionStatus.NEGATED
            certainty = CertaintyLevel.DEFINITE
            evidence = neg_evidence or context_text
            conf = 0.95
        elif is_confirmed:
            status = AssertionStatus.CONFIRMED
            certainty = CertaintyLevel.DEFINITE
            evidence = conf_evidence or context_text
            conf = 0.95
        elif is_suspected:
            status = AssertionStatus.SUSPECTED
            certainty = CertaintyLevel.POSSIBLE
            evidence = susp_evidence or context_text
            conf = 0.90
        elif is_historical:
            status = AssertionStatus.HISTORICAL
            certainty = CertaintyLevel.DEFINITE
            evidence = hist_evidence or context_text
            conf = 0.90
        elif is_hypothetical:
            status = AssertionStatus.HYPOTHETICAL
            certainty = CertaintyLevel.POSSIBLE
            evidence = hypo_evidence or context_text
            conf = 0.85
        else:
            # Default assumption for reported health events in surveillance reports: CONFIRMED / PROBABLE
            status = AssertionStatus.CONFIRMED
            certainty = CertaintyLevel.PROBABLE
            evidence = context_text
            conf = 0.80

        return Assertion(
            assertion_status=status,
            certainty=certainty,
            is_negated=is_negated,
            is_historical=is_historical,
            evidence_span=evidence[:300] if evidence else None,
            confidence=conf,
        )

    def _extract_local_clause(self, text: str, start: int, end: int) -> str:
        # Extract clause around the span bounded by punctuation and adversative conjunctions
        pre = text[:start]
        post = text[end:]

        delimiters = [
            ".", ";", "\n", "|", "\t",
            ", but ", ", however ", ", while ", ", whereas ", ", although ",
            " but ", " however ", " while ", " whereas ",
        ]

        clause_start = max(0, start - 120)
        for delim in delimiters:
            pos = pre.rfind(delim)
            if pos != -1:
                candidate_start = pos + len(delim)
                if candidate_start > clause_start:
                    clause_start = candidate_start

        clause_end = min(len(text), end + 120)
        for delim in delimiters:
            pos = post.find(delim)
            if pos != -1:
                candidate_end = end + pos
                if candidate_end < clause_end:
                    clause_end = candidate_end

        return text[clause_start:clause_end]

    def _check_triggers(self, text: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return True, m.group(0)
        return False, None

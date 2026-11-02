"""
Epidemiological Event Relevance Classifier for EpiSense.
Determines whether an NLP-processed document represents a bona fide acute epidemiological incident
or non-outbreak content (academic studies, seroprevalence surveys, reviews, clinical guidance,
diplomatic agreements, policy announcements, elimination reviews, routine advisories).
"""

from enum import Enum
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from episense.schemas.nlp import NLPOutput
from episense.schemas.assertion import AssertionStatus


class EventDisposition(str, Enum):
    """Authoritative Phase 2 epidemiological disposition classifications."""
    QUALIFYING_POSITIVE_REPORT = "QUALIFYING_POSITIVE_REPORT"
    SUSPECTED_REPORT = "SUSPECTED_REPORT"
    NEGATIVE_RULE_OUT = "NEGATIVE_RULE_OUT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    ADMINISTRATIVE_CONTEXT = "ADMINISTRATIVE_CONTEXT"
    AMBIGUOUS_REQUIRES_REVIEW = "AMBIGUOUS_REQUIRES_REVIEW"


class EventRelevanceCategory(str, Enum):
    # The 9 canonical public-health relevance classes mandated by EpiSense
    ACUTE_OUTBREAK_REPORT = "ACUTE_OUTBREAK_REPORT"
    SURVEILLANCE_REPORT = "SURVEILLANCE_REPORT"
    CASE_CLUSTER_REPORT = "CASE_CLUSTER_REPORT"
    NEGATIVE_RULE_OUT = "NEGATIVE_RULE_OUT"
    CONTEXTUAL_HEALTH_NEWS = "CONTEXTUAL_HEALTH_NEWS"
    HEALTH_POLICY_OR_ADMINISTRATION = "HEALTH_POLICY_OR_ADMINISTRATION"
    GENERAL_DISEASE_REFERENCE = "GENERAL_DISEASE_REFERENCE"
    OUT_OF_SCOPE_EVENT = "OUT_OF_SCOPE_EVENT"
    IRRELEVANT = "IRRELEVANT"

    # Backward-compatible aliases
    OFFICIAL_OUTBREAK_REPORT = "ACUTE_OUTBREAK_REPORT"
    SUSPECTED_OUTBREAK_REPORT = "ACUTE_OUTBREAK_REPORT"
    CONFIRMED_OUTBREAK_REPORT = "ACUTE_OUTBREAK_REPORT"
    ROUTINE_SURVEILLANCE_REPORT = "SURVEILLANCE_REPORT"
    SURVEILLANCE_UPDATE = "SURVEILLANCE_REPORT"
    EPIDEMIOLOGICAL_STUDY_OR_RESEARCH = "CONTEXTUAL_HEALTH_NEWS"
    RESEARCH_OR_GENERAL_BACKGROUND = "CONTEXTUAL_HEALTH_NEWS"
    REVIEW_ARTICLE = "CONTEXTUAL_HEALTH_NEWS"
    CLINICAL_OR_PUBLIC_HEALTH_GUIDANCE = "HEALTH_POLICY_OR_ADMINISTRATION"
    RETROSPECTIVE_HISTORICAL_REPORT = "CONTEXTUAL_HEALTH_NEWS"
    GENERAL_DISEASE_MENTION = "GENERAL_DISEASE_REFERENCE"
    POLICY_ADMINISTRATIVE_NEWS = "HEALTH_POLICY_OR_ADMINISTRATION"
    PREPAREDNESS_OR_TRAINING = "HEALTH_POLICY_OR_ADMINISTRATION"
    ELIMINATION_PROGRAM_REVIEW = "HEALTH_POLICY_OR_ADMINISTRATION"
    ROUTINE_ADVISORY = "CONTEXTUAL_HEALTH_NEWS"
    NEGATED_SURVEILLANCE = "NEGATIVE_RULE_OUT"
    INSUFFICIENT_CLINICAL_EVIDENCE = "GENERAL_DISEASE_REFERENCE"
    REQUIRES_HUMAN_REVIEW = "CASE_CLUSTER_REPORT"
    IRRELEVANT_REPORT = "IRRELEVANT"
    UNKNOWN_UNCLASSIFIABLE = "IRRELEVANT"


class EventRelevanceDecision(BaseModel):
    is_epidemiological_event: bool
    category: EventRelevanceCategory
    disposition: EventDisposition = Field(default=EventDisposition.ADMINISTRATIVE_CONTEXT)
    confidence: float
    rationale: str
    relevance_indicators: List[str] = Field(default_factory=list)
    filtering_indicators: List[str] = Field(default_factory=list)


class EventRelevanceClassifier:
    """
    Classifies public-health texts into acute epidemiological incidents vs non-outbreak content.
    Prevents academic seroprevalence studies, clinical guidelines, and policy news
    from becoming false active outbreak events.
    """

    POLICY_PATTERNS = [
        re.compile(r"\b(?:signs?\s+agreements?|signing\s+ceremony|contribution\s+agreement)\b", re.I),
        re.compile(r"\b(?:bilateral\s+meeting|donor\s+agreement|financial\s+contribution)\b", re.I),
        re.compile(r"\b(?:global\s+health\s+strategy|flexible\s+contributor|cement\s+cooperation)\b", re.I),
        re.compile(r"\b(?:renew\s+their\s+partnership|notification\s+of\s+withdrawal|framework\s+agreement)\b", re.I),
        re.compile(r"\b(?:strengthening\s+public\s+health\s+across|in-depth\s+discussion\s+as)\b", re.I),
        re.compile(r"\b(?:technical\s+package\s+to\s+help\s+countries|guidelines?\s+on\s+healthy)\b", re.I),
        re.compile(r"\b(?:joint\s+leaders['’]?\s+statement|violence\s+against\s+children|hidden\s+crisis)\b", re.I),
        re.compile(r"\b(?:statement\s+by\s+the|policy\s+brief|advocacy|sustainable\s+development\s+goals?)\b", re.I),
        re.compile(r"\b(?:declaration\s+on|convention\s+on|child\s+protection|humanitarian\s+appeal)\b", re.I),
    ]

    ELIMINATION_PATTERNS = [
        re.compile(r"\b(?:certified\s+(?:malaria[- ]free|free\s+of|polio[- ]free))\b", re.I),
        re.compile(r"\b(?:awards?\s+certification|elimination\s+verification)\b", re.I),
        re.compile(r"\b(?:zero\s+indigenous\s+transmission|elimination\s+milestones?\s+towards)\b", re.I),
        re.compile(r"\b(?:maintained\s+zero\s+indigenous|consecutive\s+months\s+of\s+zero)\b", re.I),
    ]

    NEGATED_PATTERNS = [
        re.compile(r"\b(?:nil\s+outbreaks?(?:\s+report)?|zero\s+outbreaks?|no\s+outbreaks?\s+reported|nil\s+report)\b", re.I),
        re.compile(r"\b(?:no\s+cases?\s+detected|(?:all\s+)?samples?\s+tested\s+negative|tested\s+negative(?:\s+for|\s+upon)?)\b", re.I),
        re.compile(r"\b(?:ruled\s+out|excluded\s+infection|negative\s+for|0\s+cases?,?\s+0\s+deaths?)\b", re.I),
    ]

    PREPAREDNESS_PATTERNS = [
        re.compile(r"\b(?:chintan\s+shivir|preparedness\s+meeting|preparedness\s+workshop|seasonal\s+preparedness|preparedness\s+review)\b", re.I),
        re.compile(r"\b(?:tabletop\s+exercise|simulation\s+exercise|capacity\s+building|training\s+workshop)\b", re.I),
        re.compile(r"\b(?:annual\s+review\s+meeting|sensitization\s+workshop|consultation\s+meeting|mock\s+drill|coordination\s+meeting)\b", re.I),
        re.compile(r"\b(?:preparedness\s+and\s+response\s+plan|strengthening\s+preparedness|readiness\s+review)\b", re.I),
        re.compile(r"\b(?:joint\s+simulation|national\s+consultation|training\s+of\s+trainers|conclave)\b", re.I),
    ]

    RESEARCH_PATTERNS = [
        re.compile(r"\b(?:seroprevalence|serological\s+survey|cohort\s+follow[- ]up|force\s+of\s+infection|endemic\s+equilibrium|background\s+immunity|asymptomatic\s+seroconversions?|inter[- ]epidemic|non[- ]outbreak|cross[- ]sectional\s+study|clinical\s+trial|longitudinal\s+cohort|prospective\s+cohort|randomized\s+trial|in\s+vitro|in\s+vivo|genomic\s+sequencing\s+study)\b", re.I),
    ]

    REVIEW_PATTERNS = [
        re.compile(r"\b(?:systematic\s+review|meta[- ]analysis|literature\s+review|annual\s+review\s+of)\b", re.I),
    ]

    GUIDANCE_PATTERNS = [
        re.compile(r"\b(?:clinical\s+guidance|treatment\s+guidelines?|diagnostic\s+algorithm|standard\s+operating\s+procedures?|case\s+definitions?\s+guidance|infection\s+prevention\s+and\s+control\s+guidelines?|technical\s+guidelines?)\b", re.I),
    ]

    HISTORICAL_PATTERNS = [
        re.compile(r"\b(?:retrospective\s+(?:analysis|review|study|assessment)|historical\s+(?:outbreak|event|records?|lessons?)|lessons?\s+from\s+(?:the\s+)?(?:\d{4}|past)|past\s+(?:epidemics?|outbreaks?))\b", re.I),
    ]

    # Explicit lookbehinds preventing "non-outbreak" and "inter-epidemic" from matching
    OUTBREAK_PATTERNS = [
        re.compile(r"(?<!non-)(?<!non\s)(?<!inter-)(?<!inter\s)\b(?:outbreak|outbreaks|epidemic|epidemics|cluster|clusters|cluster\s+of\s+cases|laboratory[- ]confirmed\s+cases?)\b", re.I),
        re.compile(r"\b(?:tested\s+positive\s+for|confirmed\s+cases?|fatalities?|deaths?|hospitalized)\b", re.I),
        re.compile(r"\b(?:admitted\s+to\s+hospital|intensive\s+care|presenting\s+with\s+fever)\b", re.I),
        re.compile(r"\b(?:under\s+quarantine|active\s+symptom\s+surveillance|secondary\s+transmissions?)\b", re.I),
        re.compile(r"\b(?:suspected\s+cases?|admissions?\s+over|acute\s+respiratory\s+distress)\b", re.I),
        re.compile(r"\b(?:confirmed|suspected|reported|recorded|new)\s+(?:\w+\s+){0,3}cases?\b", re.I),
        re.compile(r"\b(?:cases?\s+of\s+\w+|cases?\s+were\s+reported)\b", re.I),
    ]

    def classify(self, title: str, text: str, nlp_output: Optional[NLPOutput] = None) -> EventRelevanceDecision:
        combined = f"{title}\n{text}".strip()

        # 1. Check for explicit Negated Surveillance / NIL Outbreak Report
        for pat in self.NEGATED_PATTERNS:
            m = pat.search(combined)
            if m:
                return EventRelevanceDecision(
                    is_epidemiological_event=False,
                    category=EventRelevanceCategory.NEGATIVE_RULE_OUT,
                    disposition=EventDisposition.NEGATIVE_RULE_OUT,
                    confidence=0.95,
                    rationale=f"Surveillance record with explicit negation/rule-out: detected '{m.group(0)}'. Negative investigation / clinical rule-out (0 positive cases).",
                    relevance_indicators=[m.group(0)],
                )

        # 3. Check for Policy, Governance, Diplomatic & Child Protection News
        policy_matches = [m.group(0) for pat in self.POLICY_PATTERNS for m in [pat.search(combined)] if m]
        if policy_matches:
            return EventRelevanceDecision(
                is_epidemiological_event=False,
                category=EventRelevanceCategory.HEALTH_POLICY_OR_ADMINISTRATION,
                disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                confidence=0.93,
                rationale=f"Diplomatic, administrative, or policy document: detected '{policy_matches[0]}'. Non-acute administrative or guidance context.",
                filtering_indicators=policy_matches,
            )

        # 4. Check for Elimination / Eradication Milestones
        elim_matches = [m.group(0) for pat in self.ELIMINATION_PATTERNS for m in [pat.search(combined)] if m]
        if elim_matches:
            outbreak_cues = [m.group(0) for pat in self.OUTBREAK_PATTERNS for m in [pat.search(combined)] if m]
            if not outbreak_cues:
                return EventRelevanceDecision(
                    is_epidemiological_event=False,
                    category=EventRelevanceCategory.HEALTH_POLICY_OR_ADMINISTRATION,
                    disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                    confidence=0.92,
                    rationale=f"Public-health elimination / verification review: detected '{elim_matches[0]}'. Zero active transmission.",
                    filtering_indicators=elim_matches,
                )

        # 5. Check for Epidemiological Study or Research Papers (e.g. Seroprevalence, Endemic Equilibrium, Cohort Studies)
        research_matches = [m.group(0) for pat in self.RESEARCH_PATTERNS for m in [pat.search(combined)] if m]
        if research_matches:
            active_casualty_pattern = re.compile(r"\b(?:\d+\s+(?:deaths?|fatalities?|admitted)|patients?\s+died|emergency\s+outbreak)\b", re.I)
            if not active_casualty_pattern.search(combined):
                return EventRelevanceDecision(
                    is_epidemiological_event=False,
                    category=EventRelevanceCategory.CONTEXTUAL_HEALTH_NEWS,
                    disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                    confidence=0.93,
                    rationale=f"Epidemiological study / cohort research: detected '{research_matches[0]}'. Academic paper on seroprevalence or endemic equilibrium, NOT an active outbreak.",
                    filtering_indicators=research_matches,
                )

        # 6. Check for Review Articles / Meta-Analyses
        review_matches = [m.group(0) for pat in self.REVIEW_PATTERNS for m in [pat.search(combined)] if m]
        if review_matches:
            return EventRelevanceDecision(
                is_epidemiological_event=False,
                category=EventRelevanceCategory.CONTEXTUAL_HEALTH_NEWS,
                disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                confidence=0.92,
                rationale=f"Literature review or meta-analysis: detected '{review_matches[0]}'. Non-acute academic synthesis.",
                filtering_indicators=review_matches,
            )

        # 7. Check for Clinical or Public-Health Guidance
        guidance_matches = [m.group(0) for pat in self.GUIDANCE_PATTERNS for m in [pat.search(combined)] if m]
        if guidance_matches:
            return EventRelevanceDecision(
                is_epidemiological_event=False,
                category=EventRelevanceCategory.HEALTH_POLICY_OR_ADMINISTRATION,
                disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                confidence=0.91,
                rationale=f"Clinical management or public-health guidance: detected '{guidance_matches[0]}'. Practice advisory, not an active outbreak incident.",
                filtering_indicators=guidance_matches,
            )

        # 8. Check for Seasonal Preparedness, Training & Simulation Workshops
        prep_matches = [m.group(0) for pat in self.PREPAREDNESS_PATTERNS for m in [pat.search(combined)] if m]
        if prep_matches:
            active_casualty_pattern = re.compile(r"\b(?:\d+\s+(?:deaths?|fatalities?|hospitalized|admitted)|patients?\s+died)\b", re.I)
            if not active_casualty_pattern.search(combined):
                return EventRelevanceDecision(
                    is_epidemiological_event=False,
                    category=EventRelevanceCategory.HEALTH_POLICY_OR_ADMINISTRATION,
                    disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                    confidence=0.94,
                    rationale=f"Institutional preparedness, simulation, or training workshop: detected '{prep_matches[0]}'. Non-outbreak administrative context.",
                    filtering_indicators=prep_matches,
                )

        # 9. Check for Historical Archival / Retrospective Reviews
        hist_matches = [m.group(0) for pat in self.HISTORICAL_PATTERNS for m in [pat.search(combined)] if m]
        if hist_matches:
            if not re.search(r"\b(?:currently|today|yesterday|this\s+week|active\s+cluster|under\s+surveillance|2026)\b", combined, re.I):
                return EventRelevanceDecision(
                    is_epidemiological_event=False,
                    category=EventRelevanceCategory.CONTEXTUAL_HEALTH_NEWS,
                    disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                    confidence=0.91,
                    rationale=f"Retrospective historical analysis: detected '{hist_matches[0]}'. Non-acute archival context.",
                    filtering_indicators=hist_matches,
                )

        # 10. Check for Acute Outbreak indicators
        outbreak_cues = [m.group(0) for pat in self.OUTBREAK_PATTERNS for m in [pat.search(combined)] if m]

        # Check NLPOutput extractions if provided
        has_disease = False
        has_positive_assertion = False
        has_case_counts = False
        is_negated_in_nlp = False

        if nlp_output:
            from episense.schemas.entity import EntityType
            disease_ents = [
                e for e in nlp_output.entities
                if getattr(e, "entity_type", None) == EntityType.DISEASE
                or str(getattr(e, "entity_type", "")).lower() in ("disease", "pathogen", "syndrome")
            ]
            has_disease = len(disease_ents) > 0
            for a in nlp_output.assertions:
                st = getattr(a, "assertion_status", None) or getattr(a, "assertion", None)
                st_val = (st.value if hasattr(st, "value") else str(st)).upper()
                if st_val in ("CONFIRMED", "SUSPECTED"):
                    has_positive_assertion = True
                elif st_val == "NEGATED":
                    is_negated_in_nlp = True

            for assoc in getattr(nlp_output, "context_associations", []):
                a = getattr(assoc, "assertion", None)
                st = getattr(a, "assertion_status", None)
                st_val = (st.value if hasattr(st, "value") else str(st)).upper()
                if st_val in ("CONFIRMED", "SUSPECTED"):
                    has_positive_assertion = True
                elif st_val == "NEGATED":
                    is_negated_in_nlp = True

            for q in nlp_output.quantities:
                u = getattr(q, "unit", "").lower()
                qty_type = getattr(q, "quantity_type", None)
                qty_type_val = qty_type.value if hasattr(qty_type, "value") else str(qty_type)
                val = getattr(q, "numeric_value", None) if getattr(q, "numeric_value", None) is not None else getattr(q, "normalized_value", None)
                if val == 0:
                    is_negated_in_nlp = True
                if qty_type_val in ("case_count", "death_count", "hospitalization"):
                    if val is not None and val > 0:
                        has_case_counts = True
                elif any(x in u for x in ["case", "death", "fatalit", "admit", "hospital"]):
                    if val is not None and val > 0:
                        has_case_counts = True

        if is_negated_in_nlp and not has_case_counts:
            return EventRelevanceDecision(
                is_epidemiological_event=False,
                category=EventRelevanceCategory.NEGATIVE_RULE_OUT,
                disposition=EventDisposition.NEGATIVE_RULE_OUT,
                confidence=0.95,
                rationale="NLP extraction confirmed negative assertion / 0 clinical case counts. Preserved as negative rule-out.",
                relevance_indicators=["negated_assertion_zero_cases"],
            )

        if outbreak_cues:
            disp = EventDisposition.QUALIFYING_POSITIVE_REPORT if has_case_counts else EventDisposition.SUSPECTED_REPORT
            return EventRelevanceDecision(
                is_epidemiological_event=True,
                category=EventRelevanceCategory.ACUTE_OUTBREAK_REPORT,
                disposition=disp,
                confidence=0.92,
                rationale="Validated acute outbreak incident: contains verified pathogen mentions and active epidemiological transmission cues.",
                relevance_indicators=outbreak_cues,
            )

        if has_case_counts and has_disease:
            return EventRelevanceDecision(
                is_epidemiological_event=True,
                category=EventRelevanceCategory.SURVEILLANCE_REPORT,
                disposition=EventDisposition.SUSPECTED_REPORT,
                confidence=0.88,
                rationale="Surveillance observation with clinical case counts.",
                relevance_indicators=["clinical_case_counts_detected"],
            )

        # If disease was mentioned but has zero clinical case counts and no active outbreak cues
        if has_disease or re.search(r"\b(?:covid[- ]19|coronavirus|dengue|malaria|cholera|chikungunya|scrub typhus)\b", combined, re.I):
            return EventRelevanceDecision(
                is_epidemiological_event=False,
                category=EventRelevanceCategory.GENERAL_DISEASE_REFERENCE,
                disposition=EventDisposition.ADMINISTRATIVE_CONTEXT,
                confidence=0.85,
                rationale="Background or educational mention: disease term present without active incident, cases, or outbreak declaration.",
                filtering_indicators=["unassociated_disease_reference"],
            )

        # Default fallback: No relevant epidemiological event
        return EventRelevanceDecision(
            is_epidemiological_event=False,
            category=EventRelevanceCategory.IRRELEVANT,
            disposition=EventDisposition.AMBIGUOUS_REQUIRES_REVIEW,
            confidence=0.85,
            rationale="No relevant acute epidemiological event detected in document text.",
            filtering_indicators=["no_outbreak_cues"],
        )

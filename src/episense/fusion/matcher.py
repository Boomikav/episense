"""
Deterministic Cross-Document Event Matcher for EpiSense.
Evaluates candidate pairs across disease, geography, temporality, assertions, and quantities.
"""

import re
from typing import Optional, Set, Tuple
from episense.schemas.event import EventCandidate, EventObservation, MatchDecision, MatchEvaluation
from episense.schemas.assertion import AssertionStatus
from episense.schemas.location import GeographicLevel
from episense.fusion.disease_linker import DiseaseLinker
from episense.fusion.geo_linker import GeographicLinker
from episense.fusion.temporal_linker import TemporalLinker


class EventMatcher:
    """
    Evaluates whether two EventCandidates represent the same underlying epidemiological incident.
    """

    def __init__(self, window_days: int = 7):
        self.disease_linker = DiseaseLinker()
        self.geo_linker = GeographicLinker()
        self.temporal_linker = TemporalLinker(window_days=window_days)

    def match(self, candidate_a: EventCandidate, candidate_b: EventCandidate) -> MatchEvaluation:
        """
        Computes compatibility across all dimensions and emits a structured MatchEvaluation.
        """
        obs_a = candidate_a.observation
        obs_b = candidate_b.observation

        rationales = []

        # 1. Disease Compatibility
        dis_compat, dis_score, dis_rat = self.disease_linker.are_compatible(
            obs_a.canonical_disease, obs_a.icd10_code,
            obs_b.canonical_disease, obs_b.icd10_code,
        )
        rationales.append(dis_rat)

        if not dis_compat:
            return MatchEvaluation(
                decision=MatchDecision.NO_MATCH,
                score=0.0,
                disease_compatible=False,
                geo_compatible=False,
                temporal_compatible=False,
                assertion_compatible=False,
                rationale="; ".join(rationales),
            )

        # 2. Geographic Compatibility
        geo_compat, geo_score, _, _, geo_rat = self.geo_linker.evaluate_compatibility(
            obs_a.location, obs_b.location
        )
        rationales.append(geo_rat)

        if not geo_compat:
            return MatchEvaluation(
                decision=MatchDecision.NO_MATCH,
                score=0.0,
                disease_compatible=True,
                geo_compatible=False,
                temporal_compatible=False,
                assertion_compatible=False,
                rationale="; ".join(rationales),
            )

        # 2b. Institutional Compatibility (Different institutions must not be merged)
        inst_compat, inst_rat = self._evaluate_institution_compatibility(obs_a, obs_b)
        if not inst_compat:
            rationales.append(inst_rat)
            return MatchEvaluation(
                decision=MatchDecision.NO_MATCH,
                score=0.0,
                disease_compatible=True,
                geo_compatible=False,
                temporal_compatible=False,
                assertion_compatible=False,
                rationale="; ".join(rationales),
            )

        # 2c. Geographic Hierarchy / District vs Sub-district Check
        # Shared district alone does not establish outbreak identity across distinct subdistricts/localities
        if obs_a.location and obs_b.location:
            loc_a_res = obs_a.location.resolved_location
            loc_b_res = obs_b.location.resolved_location
            if loc_a_res and loc_b_res:
                if (
                    loc_a_res.geographic_level in (GeographicLevel.SUBDISTRICT, GeographicLevel.CITY, GeographicLevel.POINT)
                    and loc_b_res.geographic_level in (GeographicLevel.SUBDISTRICT, GeographicLevel.CITY, GeographicLevel.POINT)
                ):
                    if loc_a_res.normalized_name.lower().strip() != loc_b_res.normalized_name.lower().strip():
                        rationales.append(
                            f"Distinct localities in same district ({loc_a_res.normalized_name} vs {loc_b_res.normalized_name}): shared district does not establish outbreak identity."
                        )
                        return MatchEvaluation(
                            decision=MatchDecision.NO_MATCH,
                            score=0.0,
                            disease_compatible=True,
                            geo_compatible=False,
                            temporal_compatible=False,
                            assertion_compatible=False,
                            rationale="; ".join(rationales),
                        )

        # 3. Temporal Compatibility
        temp_compat, temp_score, _, _, _, temp_rat = self.temporal_linker.evaluate_compatibility(
            obs_a.event_time, obs_a.publication_time,
            obs_b.event_time, obs_b.publication_time,
        )
        rationales.append(temp_rat)

        if not temp_compat:
            return MatchEvaluation(
                decision=MatchDecision.NO_MATCH,
                score=0.0,
                disease_compatible=True,
                geo_compatible=True,
                temporal_compatible=False,
                assertion_compatible=False,
                rationale="; ".join(rationales),
            )

        # 4. Assertion Compatibility
        ass_a = obs_a.assertion.assertion_status
        ass_b = obs_b.assertion.assertion_status
        ass_compat, ass_score, ass_rat = self._evaluate_assertion_compatibility(ass_a, ass_b)
        rationales.append(ass_rat)

        if not ass_compat:
            return MatchEvaluation(
                decision=MatchDecision.NO_MATCH,
                score=0.0,
                disease_compatible=True,
                geo_compatible=True,
                temporal_compatible=True,
                assertion_compatible=False,
                rationale="; ".join(rationales),
            )

        # 5. Composite Score Calculation
        composite_score = round(dis_score * 0.35 + geo_score * 0.30 + temp_score * 0.25 + ass_score * 0.10, 3)

        # 5b. Shared village without explicit transmission linkage check
        # Shared village alone across distinct reporting dates does not establish transmission linkage
        has_temporal_gap = False
        if obs_a.event_time and obs_b.event_time:
            if obs_a.event_time.normalized_start != obs_b.event_time.normalized_start:
                has_temporal_gap = True
        else:
            diff_pub_hours = abs((obs_a.publication_time - obs_b.publication_time).total_seconds()) / 3600.0
            if diff_pub_hours > 24.0:
                has_temporal_gap = True

        is_local_village = False
        if obs_a.location and obs_b.location:
            loc_a_res = obs_a.location.resolved_location
            loc_b_res = obs_b.location.resolved_location
            if loc_a_res and loc_b_res:
                if (
                    loc_a_res.geographic_level in (GeographicLevel.SUBDISTRICT, GeographicLevel.CITY, GeographicLevel.POINT)
                    and loc_b_res.geographic_level in (GeographicLevel.SUBDISTRICT, GeographicLevel.CITY, GeographicLevel.POINT)
                ):
                    is_local_village = True
            raw_a = (obs_a.location.raw_text or "").lower()
            raw_b = (obs_b.location.raw_text or "").lower()
            if "village" in raw_a and "village" in raw_b:
                is_local_village = True

        has_explicit_linkage = self._has_explicit_transmission_linkage(obs_a, obs_b)

        if has_temporal_gap and is_local_village and not has_explicit_linkage:
            rationales.append(
                "Shared village/locality across distinct reporting periods without explicit transmission linkage: candidate retained as provisional association, not merged."
            )
            return MatchEvaluation(
                decision=MatchDecision.POSSIBLE_MATCH,
                score=min(composite_score, 0.75),
                disease_compatible=dis_compat,
                geo_compatible=geo_compat,
                temporal_compatible=temp_compat,
                assertion_compatible=ass_compat,
                rationale="; ".join(rationales),
            )

        # Decision Thresholds
        if composite_score >= 0.78 and dis_score >= 0.90 and geo_score >= 0.80 and temp_score >= 0.60:
            decision = MatchDecision.MATCH
        elif composite_score >= 0.50:
            decision = MatchDecision.POSSIBLE_MATCH
        else:
            decision = MatchDecision.NO_MATCH

        return MatchEvaluation(
            decision=decision,
            score=composite_score,
            disease_compatible=dis_compat,
            geo_compatible=geo_compat,
            temporal_compatible=temp_compat,
            assertion_compatible=ass_compat,
            rationale="; ".join(rationales),
        )

    def _extract_institution_keywords(self, obs: EventObservation) -> Set[str]:
        """Extracts distinctive institutional name tokens from location raw text, population, and evidence references."""
        text_sources = []
        if obs.location and obs.location.raw_text:
            text_sources.append(obs.location.raw_text)
        if obs.population and obs.population.text_span:
            text_sources.append(obs.population.text_span)
        for ref in obs.evidence_references:
            if ref.span_text:
                text_sources.append(ref.span_text)
        combined = " ".join(text_sources).lower()

        facility_markers = [
            "school", "hostel", "college", "hospital", "vidyalaya",
            "vidyanikethan", "ashram", "campus", "academy", "university",
            "mess", "residential", "girls hostel", "boys hostel", "jail", "prison"
        ]
        has_facility = any(marker in combined for marker in facility_markers)
        if not has_facility:
            return set()

        stop_words = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
            "from", "by", "as", "is", "was", "were", "are", "cases", "reported", "rural",
            "urban", "village", "sub-district", "district", "state", "status", "control",
            "surveillance", "under", "pre-metric", "post-metric", "government", "govt",
            "school", "hostel", "college", "vidyalaya", "vidyanikethan", "residential",
            "facility", "hospital", "mess", "girls", "boys", "students", "staff"
        }
        if obs.location and obs.location.resolved_location:
            res_loc = obs.location.resolved_location
            if res_loc.normalized_name:
                for part in res_loc.normalized_name.lower().split():
                    stop_words.add(part)
            if res_loc.parent_location:
                for part in res_loc.parent_location.lower().split():
                    stop_words.add(part)

        tokens = set(re.findall(r"[a-z0-9]{3,}", combined))
        distinctive = tokens - stop_words
        return distinctive

    def _evaluate_institution_compatibility(
        self, obs_a: EventObservation, obs_b: EventObservation
    ) -> Tuple[bool, str]:
        """Verifies that candidate observations do not originate from different named institutions."""
        inst_a = self._extract_institution_keywords(obs_a)
        inst_b = self._extract_institution_keywords(obs_b)

        if inst_a and inst_b:
            overlap = inst_a.intersection(inst_b)
            if not overlap:
                a_desc = ", ".join(sorted(inst_a)[:3])
                b_desc = ", ".join(sorted(inst_b)[:3])
                return False, f"Distinct institutions identified ({a_desc} vs {b_desc}): different facilities/cohorts cannot be merged."

        return True, "Institutional contexts compatible"

    def _has_explicit_transmission_linkage(
        self, obs_a: EventObservation, obs_b: EventObservation
    ) -> bool:
        """Checks for explicit follow-up, serial continuity, or contact transmission cues."""
        text_sources = []
        if obs_a.location and obs_a.location.raw_text:
            text_sources.append(obs_a.location.raw_text)
        for ref in obs_a.evidence_references:
            if ref.span_text:
                text_sources.append(ref.span_text)
        if obs_b.location and obs_b.location.raw_text:
            text_sources.append(obs_b.location.raw_text)
        for ref in obs_b.evidence_references:
            if ref.span_text:
                text_sources.append(ref.span_text)
        combined = " ".join(text_sources).lower()

        linkage_cues = [
            "follow-up", "follow up", "continuation", "ongoing outbreak",
            "secondary cases", "contact tracing linked", "serial testing of index",
            "previously reported outbreak", "earlier reported outbreak"
        ]
        return any(cue in combined for cue in linkage_cues)

    def _evaluate_assertion_compatibility(
        self, status_a: AssertionStatus, status_b: AssertionStatus
    ) -> Tuple[bool, float, str]:
        # Both same status
        if status_a == status_b:
            return True, 1.0, f"Identical assertion status: {status_a.value}"

        # Confirmed + Suspected (compatible evolution / investigation)
        active_statuses = {AssertionStatus.CONFIRMED, AssertionStatus.SUSPECTED}
        if status_a in active_statuses and status_b in active_statuses:
            return True, 0.85, f"Compatible active assertions: {status_a.value} and {status_b.value}"

        # Negated + Confirmed/Suspected -> Contradiction!
        if AssertionStatus.NEGATED in (status_a, status_b):
            return False, 0.0, f"Contradictory assertions: {status_a.value} vs {status_b.value}"

        # Historical + Confirmed -> Different temporal episodes!
        if AssertionStatus.HISTORICAL in (status_a, status_b):
            return False, 0.0, f"Historical mention cannot merge with contemporary report: {status_a.value} vs {status_b.value}"

        # Hypothetical / Advisory + Confirmed
        if AssertionStatus.HYPOTHETICAL in (status_a, status_b):
            return False, 0.0, f"Hypothetical advisory cannot merge with active case report: {status_a.value} vs {status_b.value}"

        return False, 0.0, f"Incompatible assertions: {status_a.value} vs {status_b.value}"

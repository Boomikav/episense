"""
Event Fusion Engine for EpiSense.
Clusters compatible EventCandidates into canonical FusedEvents with
anti-inflation quantity aggregation and full evidence provenance.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid5, NAMESPACE_DNS

from episense.schemas.document import OriginClassification
from episense.schemas.event import (
    EventCandidate,
    EventObservation,
    FusedEvent,
    MatchDecision,
    MatchEvaluation,
    SourceGroup,
    EpidemiologicalQuantities,
    EvidenceReference,
)
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.location import Location
from episense.fusion.matcher import EventMatcher
from episense.fusion.geo_linker import GeographicLinker
from episense.fusion.temporal_linker import TemporalLinker
from episense.fusion.source_independence import SourceIndependenceTracker
from episense.fusion.quantities import QuantityAggregator


class EventFusionEngine:
    """
    Synthesizes canonical FusedEvent entities from candidate event observations.
    """

    def __init__(self, window_days: int = 7):
        self.matcher = EventMatcher(window_days=window_days)
        self.geo_linker = GeographicLinker()
        self.temporal_linker = TemporalLinker(window_days=window_days)
        self.source_tracker = SourceIndependenceTracker()
        self.quantity_aggregator = QuantityAggregator()

    def fuse(self, candidates: List[EventCandidate]) -> List[FusedEvent]:
        """
        Deterministically clusters candidates into canonical FusedEvents.
        """
        if not candidates:
            return []

        # Sort candidates deterministically by disease_key, start time, doc_id
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (
                c.disease_key,
                c.temporal_window_start.isoformat() if c.temporal_window_start else "",
                str(c.observation.document_id),
                c.observation.evidence_references[0].start_char if c.observation.evidence_references else 0,
                c.observation.raw_disease_span,
                str(c.candidate_id),
            ),
        )

        # Build clusters (connected components based on MatchDecision.MATCH)
        # We start with each candidate in its own cluster, then merge if MATCH.
        clusters: List[List[EventCandidate]] = []
        cluster_rationales: Dict[int, List[str]] = {}

        for cand in sorted_candidates:
            matched_cluster_idx = None

            for idx, cluster in enumerate(clusters):
                # Compare against the representative (first) candidate of the cluster
                rep = cluster[0]
                eval_res = self.matcher.match(rep, cand)

                if eval_res.decision == MatchDecision.MATCH:
                    matched_cluster_idx = idx
                    cluster_rationales[idx].append(eval_res.rationale)
                    break

            if matched_cluster_idx is not None:
                clusters[matched_cluster_idx].append(cand)
            else:
                new_idx = len(clusters)
                clusters.append([cand])
                cluster_rationales[new_idx] = []

        # Synthesize each cluster into a FusedEvent
        fused_events: List[FusedEvent] = []
        for idx, cluster in enumerate(clusters):
            fused = self._synthesize_cluster(cluster, cluster_rationales.get(idx, []))
            fused_events.append(fused)

        # Sort fused events by date ascending
        fused_events.sort(key=lambda fe: (fe.event_window_start, fe.canonical_disease))
        return fused_events

    def _synthesize_cluster(
        self, cluster: List[EventCandidate], rationales: List[str]
    ) -> FusedEvent:
        observations = [c.observation for c in cluster]

        # 1. Canonical Disease
        # Pick the most detailed canonical disease name and ICD-10 code
        canonical_disease = observations[0].canonical_disease
        icd10_code = observations[0].icd10_code
        for obs in observations[1:]:
            if not icd10_code and obs.icd10_code:
                icd10_code = obs.icd10_code
                canonical_disease = obs.canonical_disease
            elif len(obs.canonical_disease) > len(canonical_disease):
                canonical_disease = obs.canonical_disease

        # 2. Canonical Location & Hierarchy
        canonical_location: Optional[Location] = None
        hierarchy: Dict[str, Optional[str]] = {
            "country": None, "region": None, "district": None, "subdistrict": None, "city": None
        }

        # Resolve lowest common administrative level
        for obs in observations:
            if obs.location and obs.location.resolved_location:
                res_loc = obs.location.resolved_location
                if canonical_location is None:
                    canonical_location = res_loc
                    hierarchy = self.geo_linker._build_hierarchy(res_loc)
                else:
                    # Prefer more specific (higher rank) location
                    rank_curr = self.geo_linker.LEVEL_RANK.get(canonical_location.geographic_level, 0)
                    rank_new = self.geo_linker.LEVEL_RANK.get(res_loc.geographic_level, 0)
                    if rank_new > rank_curr:
                        canonical_location = res_loc
                        hierarchy = self.geo_linker._build_hierarchy(res_loc)

        # 3. Canonical Event Window
        # Prioritize specific dates over broad full-year (>=360 days) fallback intervals
        specific_starts = [
            c.temporal_window_start for c in cluster
            if c.temporal_window_start and c.temporal_window_end
            and (c.temporal_window_end - c.temporal_window_start).total_seconds() < 360 * 86400
        ]
        if specific_starts:
            window_start = min(specific_starts)
            ends_for_specific = [
                c.temporal_window_end for c in cluster
                if c.temporal_window_start and c.temporal_window_end
                and (c.temporal_window_end - c.temporal_window_start).total_seconds() < 360 * 86400
            ]
            window_end = max(ends_for_specific) if ends_for_specific else window_start
        else:
            starts = [c.temporal_window_start for c in cluster if c.temporal_window_start]
            ends = [c.temporal_window_end for c in cluster if c.temporal_window_end]
            window_start = min(starts) if starts else observations[0].publication_time
            window_end = max(ends) if ends else observations[0].publication_time
        is_estimated = any(obs.event_time is None for obs in observations)

        # 4. Canonical Assertion Status
        # Priority: CONFIRMED > SUSPECTED > HISTORICAL > HYPOTHETICAL > NEGATED
        assertion_statuses = [obs.assertion.assertion_status for obs in observations]
        if AssertionStatus.CONFIRMED in assertion_statuses:
            status = AssertionStatus.CONFIRMED
            certainty = CertaintyLevel.DEFINITE if len(cluster) > 1 else CertaintyLevel.PROBABLE
        elif AssertionStatus.SUSPECTED in assertion_statuses:
            status = AssertionStatus.SUSPECTED
            certainty = CertaintyLevel.POSSIBLE
        elif AssertionStatus.HISTORICAL in assertion_statuses:
            status = AssertionStatus.HISTORICAL
            certainty = CertaintyLevel.DEFINITE
        elif AssertionStatus.NEGATED in assertion_statuses:
            status = AssertionStatus.NEGATED
            certainty = CertaintyLevel.DEFINITE
        else:
            status = AssertionStatus.HYPOTHETICAL
            certainty = CertaintyLevel.POSSIBLE

        # 5. Anti-Inflation Quantity Aggregation & Conflict Detection
        aggregated_quantities, has_conflicts, conflict_summary = self.quantity_aggregator.aggregate(
            observations
        )

        # 6. Source Independence Tracking
        source_groups: List[SourceGroup] = [
            self.source_tracker.assign_group(obs.source_id) for obs in observations
        ]
        # Deduplicate source groups by source_id
        unique_source_groups = list({sg.source_id: sg for sg in source_groups}.values())
        independent_count = self.source_tracker.count_independent_sources(unique_source_groups)

        # 7. Evidence Provenance Union
        evidence_refs: List[EvidenceReference] = []
        for obs in observations:
            evidence_refs.extend(obs.evidence_references)

        # 8. Deterministic Multi-Component Fusion Confidence
        extract_conf = sum(obs.extraction_confidence for obs in observations) / len(observations)
        geo_conf = 1.0 if canonical_location else 0.70
        temp_conf = 1.0 if not is_estimated else 0.75
        # Source corroboration bonus: 1 source = 1.0, 2 sources = 1.05, 3+ sources = 1.10 (capped at 1.0 overall)
        source_bonus = 1.0 + min(0.10, (independent_count - 1) * 0.05)

        base_conf = extract_conf * geo_conf * temp_conf
        final_conf = round(min(1.0, base_conf * source_bonus), 3)

        confidence_breakdown = {
            "extraction_confidence": round(extract_conf, 3),
            "geographic_confidence": round(geo_conf, 3),
            "temporal_confidence": round(temp_conf, 3),
            "source_corroboration_factor": round(source_bonus, 3),
            "final_fusion_confidence": final_conf,
        }

        # 9. Deterministic Fused Event ID
        # Generated from disease, location, and window start for reproducibility
        loc_str = canonical_location.normalized_name if canonical_location else "unknown_loc"
        seed = f"{canonical_disease}:{loc_str}:{window_start.isoformat()[:10]}"
        fused_id = uuid5(NAMESPACE_DNS, seed)

        # Determine primary origin from constituent observations
        obs_origins = {getattr(obs, "origin", None) for obs in observations}
        if OriginClassification.LIVE_EXTERNAL in obs_origins:
            primary_origin = OriginClassification.LIVE_EXTERNAL
        elif OriginClassification.MANUAL_SUBMISSION in obs_origins:
            primary_origin = OriginClassification.MANUAL_SUBMISSION
        elif OriginClassification.BENCHMARK in obs_origins:
            primary_origin = OriginClassification.BENCHMARK
        else:
            primary_origin = OriginClassification.HISTORICAL_CORPUS

        pub_times = [obs.publication_time for obs in observations if obs.publication_time]
        max_pub_time = max(pub_times) if pub_times else window_end

        return FusedEvent(
            fused_event_id=fused_id,
            canonical_disease=canonical_disease,
            icd10_code=icd10_code,
            canonical_location=canonical_location,
            primary_origin=primary_origin,
            geographic_hierarchy=hierarchy,
            event_window_start=window_start,
            event_window_end=window_end,
            publication_timestamp=max_pub_time,
            is_event_time_estimated=is_estimated,
            assertion_status=status,
            certainty=certainty,
            aggregated_quantities=aggregated_quantities,
            contributing_observation_ids=[obs.observation_id for obs in observations],
            supporting_observation_count=len(observations),
            independent_sources=unique_source_groups,
            independent_source_count=independent_count,
            evidence_references=evidence_refs,
            fusion_confidence=final_conf,
            confidence_breakdown=confidence_breakdown,
            linkage_rationale=rationales,
            has_conflicts=has_conflicts,
            conflict_summary=conflict_summary,
            created_at=window_end,
            updated_at=window_end,
        )

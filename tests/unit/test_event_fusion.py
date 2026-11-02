"""
Comprehensive Unit Tests for EpiSense Event Fusion & Epidemiological Signal Construction (Phase 7).
Verifies candidate construction, disease/geo/temporal linking, anti-inflation quantity rules,
conflict detection, source independence, provenance, and deterministic fusion.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
import pytest

from episense.schemas.document import Document, SourceType
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.temporal import TemporalExpression, TemporalType
from episense.schemas.nlp import ResolvedLocation, ResolutionState, ContextAssociation, QuantityMention, NLPOutput
from episense.schemas.event import (
    EventObservation,
    EventCandidate,
    FusedEvent,
    MatchDecision,
    MatchEvaluation,
    EpidemiologicalQuantities,
)
from episense.events.builder import EventCandidateBuilder
from episense.events.batch import EventBatchRunner
from episense.fusion.disease_linker import DiseaseLinker
from episense.fusion.geo_linker import GeographicLinker
from episense.fusion.temporal_linker import TemporalLinker
from episense.fusion.source_independence import SourceIndependenceTracker
from episense.fusion.quantities import QuantityAggregator
from episense.fusion.matcher import EventMatcher
from episense.fusion.engine import EventFusionEngine


class TestEventFusion:

    @pytest.fixture
    def builder(self):
        return EventCandidateBuilder()

    @pytest.fixture
    def disease_linker(self):
        return DiseaseLinker()

    @pytest.fixture
    def geo_linker(self):
        return GeographicLinker()

    @pytest.fixture
    def temporal_linker(self):
        return TemporalLinker(window_days=7)

    @pytest.fixture
    def source_tracker(self):
        return SourceIndependenceTracker()

    @pytest.fixture
    def quantity_aggregator(self):
        return QuantityAggregator()

    @pytest.fixture
    def matcher(self):
        return EventMatcher(window_days=7)

    @pytest.fixture
    def fusion_engine(self):
        return EventFusionEngine(window_days=7)

    # 1. Candidate Construction from NLPOutput
    def test_candidate_construction_from_nlp_output(self, builder):
        doc_id = uuid4()
        pub_time = datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)
        disease_ent = Entity(
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span="Nipah virus disease",
            start_char=0,
            end_char=19,
        )
        location_obj = Location(
            original_text="Kozhikode",
            normalized_name="Kozhikode",
            geographic_level=GeographicLevel.DISTRICT,
            parent_location="Kerala",
        )
        resolved_loc = ResolvedLocation(
            raw_text="Kozhikode",
            start_char=35,
            end_char=44,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=location_obj,
        )
        temporal_expr = TemporalExpression(
            original_expression="18 June 2026",
            normalized_start=pub_time,
            normalized_end=pub_time,
            start_char=48,
            end_char=60,
        )
        quantity_men = QuantityMention(
            raw_text="2 cases",
            numeric_value=2.0,
            unit="cases",
            start_char=20,
            end_char=27,
        )
        assoc = ContextAssociation(
            sentence_index=0,
            start_char=0,
            end_char=61,
            primary_disease=disease_ent,
            assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
            location=resolved_loc,
            temporal=temporal_expr,
            quantity=quantity_men,
        )

        nlp_out = NLPOutput(
            document_id=doc_id,
            context_associations=[assoc],
            entities=[disease_ent],
        )

        candidates = builder.build_candidates(nlp_out, source_id="who_don", publication_time=pub_time)
        assert len(candidates) == 1
        cand = candidates[0]

        assert cand.disease_key == "nipah virus disease"
        assert cand.geo_key == "kozhikode"
        assert cand.observation.canonical_disease == "Nipah virus disease"
        assert cand.observation.icd10_code is None
        assert cand.observation.quantities.case_count == 2
        assert len(cand.observation.evidence_references) >= 4

    # 2. Disease Linking & Canonicalization
    def test_disease_linking_and_synonyms(self, disease_linker):
        compat, score, _ = disease_linker.are_compatible("Nipah", None, "Nipah virus disease", None)
        assert compat is True
        assert score >= 0.95

        compat_d, score_d, _ = disease_linker.are_compatible("dengue", None, "Dengue fever", "ICD10:A90")
        assert compat_d is True
        assert score_d >= 0.90

        # Incompatible diseases
        compat_diff, score_diff, _ = disease_linker.are_compatible("Cholera", "ICD10:A00", "Measles", "ICD10:B05")
        assert compat_diff is False
        assert score_diff == 0.0

    # 3. Geographic Compatibility & False-Merge Protection
    def test_geographic_compatibility_and_unresolved_protection(self, geo_linker):
        loc_kozhikode = ResolvedLocation(
            raw_text="Kozhikode",
            start_char=0,
            end_char=9,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Kozhikode",
                normalized_name="Kozhikode",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
            ),
        )
        loc_kerala = ResolvedLocation(
            raw_text="Kerala",
            start_char=0,
            end_char=6,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Kerala",
                normalized_name="Kerala",
                geographic_level=GeographicLevel.REGION,
                parent_location="India",
            ),
        )
        loc_bengal = ResolvedLocation(
            raw_text="West Bengal",
            start_char=0,
            end_char=11,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="West Bengal",
                normalized_name="West Bengal",
                geographic_level=GeographicLevel.REGION,
                parent_location="India",
            ),
        )
        loc_unresolved_a = ResolvedLocation(
            raw_text="Rural Hamlet X",
            start_char=0,
            end_char=14,
            resolution_state=ResolutionState.UNRESOLVED,
        )
        loc_unresolved_b = ResolvedLocation(
            raw_text="Rural Hamlet X",
            start_char=0,
            end_char=14,
            resolution_state=ResolutionState.UNRESOLVED,
        )

        # Exact match
        compat_exact, score_exact, canon_loc, _, _ = geo_linker.evaluate_compatibility(loc_kozhikode, loc_kozhikode)
        assert compat_exact is True
        assert score_exact == 1.0
        assert canon_loc.normalized_name == "Kozhikode"

        # Parent-child match (Kozhikode district in Kerala state)
        compat_pc, score_pc, canon_pc, hier_pc, _ = geo_linker.evaluate_compatibility(loc_kozhikode, loc_kerala)
        assert compat_pc is True
        assert score_pc == 0.90
        assert canon_pc.normalized_name == "Kozhikode"  # Resolves to child
        assert hier_pc["region"] == "Kerala"

        # Conflicting jurisdictions
        compat_diff, score_diff, _, _, _ = geo_linker.evaluate_compatibility(loc_kerala, loc_bengal)
        assert compat_diff is False
        assert score_diff == 0.0

        # False-merge protection on unresolved locations (never merge solely on text similarity)
        compat_unres, _, _, _, _ = geo_linker.evaluate_compatibility(loc_unresolved_a, loc_unresolved_b)
        assert compat_unres is False

    # 4. Temporal Compatibility & Window Enforcement
    def test_temporal_compatibility_and_window(self, temporal_linker):
        t0 = datetime(2026, 6, 18, tzinfo=timezone.utc)
        t_overlap = datetime(2026, 6, 19, tzinfo=timezone.utc)
        t_distant = datetime(2026, 8, 15, tzinfo=timezone.utc)

        expr_0 = TemporalExpression(
            original_expression="18 June 2026",
            normalized_start=t0,
            normalized_end=t0,
            start_char=0,
            end_char=12,
        )
        expr_overlap = TemporalExpression(
            original_expression="19 June 2026",
            normalized_start=t_overlap,
            normalized_end=t_overlap,
            start_char=0,
            end_char=12,
        )
        expr_distant = TemporalExpression(
            original_expression="15 August 2026",
            normalized_start=t_distant,
            normalized_end=t_distant,
            start_char=0,
            end_char=14,
        )

        # Proximate event dates (1 day apart, within 7-day window)
        compat, score, m_start, m_end, _, _ = temporal_linker.evaluate_compatibility(expr_0, t0, expr_overlap, t_overlap)
        assert compat is True
        assert score >= 0.80
        assert m_start == t0
        assert m_end == t_overlap

        # Distant event dates (exceeds 7-day window)
        compat_dist, score_dist, _, _, _, _ = temporal_linker.evaluate_compatibility(expr_0, t0, expr_distant, t_distant)
        assert compat_dist is False
        assert score_dist == 0.0

    # 5. Same-Event Matching vs Different-Event Separation
    def test_matcher_decisions(self, matcher):
        t = datetime(2026, 6, 18, tzinfo=timezone.utc)
        loc = ResolvedLocation(
            raw_text="Kozhikode",
            start_char=0,
            end_char=9,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Kozhikode",
                normalized_name="Kozhikode",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
            ),
        )

        cand_a = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="who_don",
                canonical_disease="Nipah virus disease",
                raw_disease_span="Nipah",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
            ),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        cand_b = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="promed_mail",
                canonical_disease="Nipah virus disease",
                raw_disease_span="Nipah virus",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
            ),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        # Incompatible candidate (different disease)
        cand_diff_disease = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="news_media",
                canonical_disease="Cholera",
                raw_disease_span="Cholera",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
            ),
            disease_key="cholera",
            geo_key="kozhikode",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        # Same event matches
        match_ab = matcher.match(cand_a, cand_b)
        assert match_ab.decision == MatchDecision.MATCH
        assert match_ab.disease_compatible is True
        assert match_ab.geo_compatible is True
        assert match_ab.temporal_compatible is True

        # Different disease separates
        match_diff = matcher.match(cand_a, cand_diff_disease)
        assert match_diff.decision == MatchDecision.NO_MATCH
        assert match_diff.disease_compatible is False

    # 6. Anti-Inflation Invariant: 2 + 2 + 2 != 6
    def test_anti_inflation_repeated_count_invariant(self, fusion_engine):
        t = datetime(2026, 6, 18, tzinfo=timezone.utc)
        loc = ResolvedLocation(
            raw_text="Kozhikode",
            start_char=0,
            end_char=9,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Kozhikode",
                normalized_name="Kozhikode",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
            ),
        )

        # Three distinct documents all reporting 2 cases of Nipah in Kozhikode
        sources = ["who_don", "pib_mohfw_india", "promed_mail"]
        candidates = []
        for src in sources:
            candidates.append(
                EventCandidate(
                    observation=EventObservation(
                        document_id=uuid4(),
                        source_id=src,
                        canonical_disease="Nipah virus disease",
                        raw_disease_span="Nipah",
                        assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                        location=loc,
                        publication_time=t,
                        quantities=EpidemiologicalQuantities(case_count=2),
                    ),
                    disease_key="nipah virus disease",
                    geo_key="kozhikode",
                    temporal_window_start=t,
                    temporal_window_end=t,
                )
            )

        fused_events = fusion_engine.fuse(candidates)
        assert len(fused_events) == 1
        event = fused_events[0]

        # Critical invariant checks
        assert event.aggregated_quantities.case_count == 2  # MUST NOT BE 6!
        assert event.supporting_observation_count == 3
        assert event.independent_source_count >= 2
        assert event.aggregated_quantities.is_conflicting is False

    # 7. Conflicting Quantity Handling & Conflict Log
    def test_conflicting_quantity_handling(self, fusion_engine):
        t = datetime(2026, 6, 18, tzinfo=timezone.utc)
        loc = ResolvedLocation(
            raw_text="Kozhikode",
            start_char=0,
            end_char=9,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Kozhikode",
                normalized_name="Kozhikode",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
            ),
        )

        # Document A reports 2 cases, Document B reports 5 cases
        cand_a = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="source_a",
                canonical_disease="Nipah virus disease",
                raw_disease_span="Nipah",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
                quantities=EpidemiologicalQuantities(case_count=2),
            ),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            temporal_window_start=t,
            temporal_window_end=t,
        )
        cand_b = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="source_b",
                canonical_disease="Nipah virus disease",
                raw_disease_span="Nipah",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
                quantities=EpidemiologicalQuantities(case_count=5),
            ),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        fused_events = fusion_engine.fuse([cand_a, cand_b])
        assert len(fused_events) == 1
        event = fused_events[0]

        assert event.has_conflicts is True
        assert event.conflict_summary is not None
        assert "Conflicting cases counts reported" in event.conflict_summary
        assert event.aggregated_quantities.is_conflicting is True
        assert event.aggregated_quantities.reported_values["cases"] == [2.0, 5.0]
        assert event.aggregated_quantities.max_reported_estimate == 5
        assert event.aggregated_quantities.conflict_details is not None
        assert len(event.aggregated_quantities.individual_observations) == 2
        obs_sources = {o["source_id"]: o["case_count"] for o in event.aggregated_quantities.individual_observations}
        assert obs_sources == {"source_a": 2, "source_b": 5}

    def test_quantity_aggregation_preserves_scope_and_individual_observations(self, fusion_engine):
        """
        Phase 4 Invariant: Preserves each source-reported quantity with its original unit,
        event period, affected population, geography, and provenance without summing copies.
        """
        t1 = datetime(2026, 7, 10, tzinfo=timezone.utc)
        t2 = datetime(2026, 7, 12, tzinfo=timezone.utc)
        loc = ResolvedLocation(
            raw_text="Malda",
            start_char=0,
            end_char=5,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Malda",
                normalized_name="Malda",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="West Bengal",
            ),
        )

        cand_initial = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="local_health_bulletin",
                canonical_disease="Cholera",
                raw_disease_span="Cholera",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t1,
                quantities=EpidemiologicalQuantities(case_count=12, death_count=1),
            ),
            disease_key="cholera",
            geo_key="malda",
            temporal_window_start=t1,
            temporal_window_end=t1,
        )

        cand_update = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="state_epi_update",
                canonical_disease="Cholera",
                raw_disease_span="Vibrio cholerae",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t2,
                quantities=EpidemiologicalQuantities(case_count=28, death_count=2),
            ),
            disease_key="cholera",
            geo_key="malda",
            temporal_window_start=t1,
            temporal_window_end=t2,
        )

        fused = fusion_engine.fuse([cand_initial, cand_update])
        assert len(fused) == 1
        fe = fused[0]

        # Invariant 1: Quantities are NOT summed blindly (12 + 28 != 40)
        assert fe.aggregated_quantities.case_count == 28
        assert fe.aggregated_quantities.death_count == 2
        assert fe.aggregated_quantities.max_reported_estimate == 28
        assert fe.aggregated_quantities.is_conflicting is True

        # Invariant 2: Individual source observations retained with distinct provenance
        obs = fe.aggregated_quantities.individual_observations
        assert len(obs) == 2
        obs_map = {o["source_id"]: o["case_count"] for o in obs}
        assert obs_map == {"local_health_bulletin": 12, "state_epi_update": 28}

    # 8. Source Independence Grouping
    def test_source_independence(self, source_tracker):
        # Two PIB releases belonging to MOHFW
        g1 = source_tracker.assign_group("pib_mohfw_india")
        g2 = source_tracker.assign_group("ncdc_idsp_india")
        assert g1.independence_group == g2.independence_group  # Same agency group

        count = source_tracker.count_independent_sources([g1, g2])
        assert count == 1  # Not two independent sources!

        # WHO is independent
        g3 = source_tracker.assign_group("who_don")
        assert g3.independence_group != g1.independence_group
        count_with_who = source_tracker.count_independent_sources([g1, g2, g3])
        assert count_with_who == 2

        # Syndicated wire clippings from same network (PTI bureaus)
        w1 = source_tracker.assign_group("pti_delhi")
        w2 = source_tracker.assign_group("pti_punjab")
        w3 = source_tracker.assign_group("pti_haryana")
        assert w1.independence_group == w2.independence_group == w3.independence_group == "syndication:pti"
        assert source_tracker.count_independent_sources([w1, w2, w3]) == 1

        # Reuters wire syndication
        r1 = source_tracker.assign_group("reuters_health")
        r2 = source_tracker.assign_group("reuters_india")
        assert r1.independence_group == r2.independence_group == "syndication:reuters"
        assert source_tracker.count_independent_sources([r1, r2]) == 1

    # 9. Historical vs Contemporary Assertion Separation
    def test_historical_vs_contemporary_separation(self, matcher):
        t = datetime(2026, 6, 18, tzinfo=timezone.utc)
        cand_curr = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="source_a",
                canonical_disease="Dengue",
                raw_disease_span="Dengue",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                publication_time=t,
            ),
            disease_key="dengue",
            temporal_window_start=t,
            temporal_window_end=t,
        )
        cand_hist = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="source_b",
                canonical_disease="Dengue",
                raw_disease_span="Dengue",
                assertion=Assertion(assertion_status=AssertionStatus.HISTORICAL),
                publication_time=t,
            ),
            disease_key="dengue",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        match_res = matcher.match(cand_curr, cand_hist)
        assert match_res.decision == MatchDecision.NO_MATCH
        assert match_res.assertion_compatible is False

    # 10. Deterministic Repeatability
    def test_deterministic_fusion(self, fusion_engine):
        t = datetime(2026, 6, 18, tzinfo=timezone.utc)
        loc = ResolvedLocation(
            raw_text="Vellore",
            start_char=0,
            end_char=7,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                original_text="Vellore",
                normalized_name="Vellore",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Tamil Nadu",
            ),
        )

        cand1 = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="src1",
                canonical_disease="Dengue",
                raw_disease_span="dengue",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
                quantities=EpidemiologicalQuantities(case_count=12),
            ),
            disease_key="dengue",
            geo_key="vellore",
            temporal_window_start=t,
            temporal_window_end=t,
        )
        cand2 = EventCandidate(
            observation=EventObservation(
                document_id=uuid4(),
                source_id="src2",
                canonical_disease="Dengue",
                raw_disease_span="dengue fever",
                assertion=Assertion(assertion_status=AssertionStatus.CONFIRMED),
                location=loc,
                publication_time=t,
                quantities=EpidemiologicalQuantities(case_count=12),
            ),
            disease_key="dengue",
            geo_key="vellore",
            temporal_window_start=t,
            temporal_window_end=t,
        )

        run1 = fusion_engine.fuse([cand1, cand2])
        run2 = fusion_engine.fuse([cand2, cand1])

        assert len(run1) == len(run2) == 1
        assert run1[0].fused_event_id == run2[0].fused_event_id
        assert run1[0].canonical_disease == run2[0].canonical_disease
        assert run1[0].aggregated_quantities.case_count == run2[0].aggregated_quantities.case_count

    # 11. Batch Runner Execution Test
    def test_event_batch_runner_execution(self, tmp_path):
        runner = EventBatchRunner(output_dir=str(tmp_path))
        # Point to the existing benchmark corpus
        report, fused_events, candidates = runner.process_corpus(
            corpus_paths=["data/benchmarks/episense_benchmark_v1.json"],
            run_name="test_bench_fusion",
        )

        assert report.total_documents_processed == 52
        assert report.total_candidates_extracted >= 52
        assert report.total_fused_events > 0
        assert len(fused_events) == report.total_fused_events

        # Check serialization output
        report_file = tmp_path / f"test_bench_fusion_{int(report.elapsed_seconds)}"
        assert len(list(tmp_path.glob("test_bench_fusion_*"))) >= 1

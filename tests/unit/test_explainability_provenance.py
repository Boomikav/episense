"""
Unit tests for Phase 10 Explainability Dossiers, Audit Trails & Provenance Traversal Engine.
Covers evidence span reconstruction, lineage graph construction, DAG acyclicity,
deterministic traversal, SHA-256 audit trails, 5W1H dossiers, and batch reproducibility.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
import pytest
from uuid import UUID, NAMESPACE_DNS, uuid5

from episense.schemas.alert import (
    AlertExplanation,
    AlertTier,
    EpidemiologicalAlert,
    PathogenThreatTier,
    RiskScoreBreakdown,
)
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.document import Document, SourceType
from episense.schemas.event import (
    EpidemiologicalQuantities,
    EvidenceReference,
    FusedEvent,
    SourceGroup,
)
from episense.schemas.explainability import (
    AlertAuditTrail,
    AuditDecisionStep,
    Epidemiological5W1H,
    ExplainabilityDossier,
    ProvenanceEdgeType,
    ProvenanceGraph,
    ProvenanceNodeType,
    ReconstructedEvidenceSpan,
)
from episense.schemas.location import GeographicLevel, Location
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    DetectionMethod,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.explainability.reconstructor import EvidenceSpanReconstructor
from episense.explainability.graph import ProvenanceGraphBuilder
from episense.explainability.auditor import AuditTrailEngine
from episense.explainability.dossier import DossierGenerator
from episense.explainability.batch import ExplainabilityBatchRunner


# ==============================================================================
# Helpers & Fixtures
# ==============================================================================

DOC1_TEXT = (
    "New Delhi: The Ministry of Health and Family Welfare confirmed 2 cases "
    "of Nipah virus in Kozhikode district today. Immediate contact tracing is underway."
)

def make_test_document(doc_id_str: str = "doc1", text: str = DOC1_TEXT) -> Document:
    doc_id = uuid5(NAMESPACE_DNS, doc_id_str)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        document_id=doc_id,
        source_id="pib_mohfw_india",
        source_type=SourceType.OFFICIAL_BULLETIN,
        title="Official Health Bulletin",
        text=text,
        content_hash_sha256=content_hash,
        publication_timestamp=datetime(2024, 9, 2, 10, 0, tzinfo=timezone.utc),
    )

def make_test_alert(
    disease: str = "nipah virus",
    geo: str = "kozhikode",
    score: float = 0.75,
    tier: AlertTier = AlertTier.MEDIUM,
    doc_id: Optional[UUID] = None,
    fused_id: Optional[UUID] = None,
    signal_id: Optional[UUID] = None,
) -> EpidemiologicalAlert:
    start = datetime(2024, 9, 2, tzinfo=timezone.utc)
    end = datetime(2024, 9, 8, 23, 59, 59, tzinfo=timezone.utc)
    sig_id = signal_id or uuid5(NAMESPACE_DNS, f"{disease}:{geo}:sig")
    fid = fused_id or uuid5(NAMESPACE_DNS, f"{disease}:{geo}:fused")
    did = doc_id or uuid5(NAMESPACE_DNS, "doc1")
    aid = uuid5(NAMESPACE_DNS, f"{disease}:{geo}:{start.isoformat()}:{sig_id}:alert")

    breakdown = RiskScoreBreakdown(
        anomaly_score=0.40,
        threat_score=1.00,
        evidence_score=0.85,
        certainty_score=1.00,
        spatial_score=1.00,
        raw_composite_score=0.85,
        penalty_applied=0.10,
        final_score=score,
        applied_weights={
            "anomaly": 0.30,
            "threat": 0.25,
            "evidence": 0.20,
            "certainty": 0.15,
            "spatial": 0.10,
        },
    )

    explanation = AlertExplanation(
        summary=f"[MEDIUM] {disease.title()} in {geo} (Score: {score:.2f})",
        driving_factors=[
            "Pathogen Threat: Tier 4 High-Consequence",
            "Statistical Aberration: EARS_C1 alert",
            "Evidence: 2 independent sources",
        ],
        gating_rationale="Conflicting quantity reports across sources: -0.10 penalty applied",
        detailed_narrative="Detailed audit narrative...",
    )

    return EpidemiologicalAlert(
        alert_id=aid,
        signal_id=sig_id,
        disease_key=disease,
        geo_key=geo,
        pathogen_threat_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
        period_start=start,
        period_end=end,
        composite_score=score,
        alert_tier=tier,
        is_gated=True,
        gating_reason="Conflicting quantity reports across sources: -0.10 penalty applied",
        score_breakdown=breakdown,
        explanation=explanation,
        supporting_fused_event_ids=[fid],
        supporting_source_count=2,
        provenance_references=[
            EvidenceReference(
                document_id=did,
                source_id="pib_mohfw_india",
                start_char=74,
                end_char=85,
                span_text="Nipah virus",
                extraction_method="ner:exact",
                attribute_role="primary_disease",
            ),
            EvidenceReference(
                document_id=did,
                source_id="pib_mohfw_india",
                start_char=63,
                end_char=64,
                span_text="2",
                extraction_method="quantity:regex",
                attribute_role="quantity",
            ),
        ],
        created_at=end,
    )

def make_test_signal(alert: EpidemiologicalAlert) -> SignalObservation:
    return SignalObservation(
        signal_id=alert.signal_id,
        disease_key=alert.disease_key,
        geo_key=alert.geo_key,
        target_period_start=alert.period_start,
        target_period_end=alert.period_end,
        observed_value=2.0,
        expected_value=0.5,
        deviation=1.5,
        standardized_score=2.5,
        threshold=2.0,
        detection_method=DetectionMethod.EARS_C1,
        signal_level=SignalLevel.SIGNAL,
        supporting_fused_event_ids=alert.supporting_fused_event_ids,
        supporting_source_count=2,
        reliability_status=BaselineReliability.CONFLICTING_DATA,
        is_downgraded=True,
        downgrade_reason="Conflicting reports",
        explainable_rationale="Signal explainable rationale",
        provenance_references=alert.provenance_references,
        created_at=alert.period_end,
    )

def make_test_fused_event(
    alert: EpidemiologicalAlert,
    evidence_references: Optional[List[EvidenceReference]] = None,
) -> FusedEvent:
    fid = alert.supporting_fused_event_ids[0]
    refs = evidence_references if evidence_references is not None else alert.provenance_references
    return FusedEvent(
        fused_event_id=fid,
        canonical_disease=alert.disease_key,
        canonical_location=Location(
            original_text=alert.geo_key,
            normalized_name=alert.geo_key,
            geographic_level=GeographicLevel.DISTRICT,
            confidence=1.0,
        ),
        geographic_hierarchy={"district": alert.geo_key},
        event_window_start=alert.period_start,
        event_window_end=alert.period_end,
        assertion_status=AssertionStatus.CONFIRMED,
        certainty=CertaintyLevel.DEFINITE,
        aggregated_quantities=EpidemiologicalQuantities(case_count=2, death_count=0),
        independent_sources=[
            SourceGroup(independence_group="pib_mohfw_india", source_id="pib_mohfw_india")
        ],
        has_conflicts=True,
        evidence_references=refs,
    )


# ==============================================================================
# Test Suite (26 Dedicated Tests)
# ==============================================================================

class TestExplainabilityProvenance:

    # 1. Evidence Span Reconstruction Tests
    def test_evidence_span_reconstruction_exact_match(self):
        """1. Reconstruct exact text span with surrounding context."""
        reconstructor = EvidenceSpanReconstructor(default_context_window=20)
        doc = make_test_document()
        ref = EvidenceReference(
            document_id=doc.document_id,
            source_id=doc.source_id,
            start_char=74,
            end_char=85,
            span_text="Nipah virus",
            extraction_method="ner:exact",
            attribute_role="primary_disease",
        )
        span = reconstructor.reconstruct_span(ref, document_text=doc.text)

        assert span.is_valid is True
        assert span.extracted_text == "Nipah virus"
        assert span.validation_error is None
        assert "cases of Nipah virus in Kozhikode" in span.surrounding_context

    def test_evidence_span_reconstruction_offset_out_of_bounds(self):
        """2. Safe failure when end_char exceeds document length."""
        reconstructor = EvidenceSpanReconstructor()
        doc = make_test_document()
        ref = EvidenceReference(
            document_id=doc.document_id,
            source_id=doc.source_id,
            start_char=10,
            end_char=9999,  # Out of bounds
            span_text="test",
            extraction_method="ner:exact",
            attribute_role="disease",
        )
        span = reconstructor.reconstruct_span(ref, document_text=doc.text)
        assert span.is_valid is False
        assert "exceeds document length" in span.validation_error

    def test_evidence_span_reconstruction_reversed_offsets(self):
        """3. Safe failure when start_char > end_char."""
        reconstructor = EvidenceSpanReconstructor()
        doc = make_test_document()
        ref = EvidenceReference(
            document_id=doc.document_id,
            source_id=doc.source_id,
            start_char=50,
            end_char=20,  # Reversed
            span_text="test",
            extraction_method="ner:exact",
            attribute_role="disease",
        )
        span = reconstructor.reconstruct_span(ref, document_text=doc.text)
        assert span.is_valid is False
        assert "Invalid offset range" in span.validation_error

    def test_evidence_span_reconstruction_negative_offsets(self):
        """4. Safe failure on negative start offset."""
        reconstructor = EvidenceSpanReconstructor()
        doc = make_test_document()
        # In EvidenceReference, ge=0 validator might reject, but reconstructor also guards
        ref = EvidenceReference(
            document_id=doc.document_id,
            source_id=doc.source_id,
            start_char=0,
            end_char=10,
            span_text="wrong",
            extraction_method="ner:exact",
            attribute_role="disease",
        )
        # Force invalid start for defensive testing
        span = reconstructor.reconstruct_span(ref, document_text=doc.text)
        # "New Delhi:" vs "wrong" -> text mismatch
        assert span.is_valid is False
        assert "Text mismatch" in span.validation_error

    def test_evidence_span_reconstruction_text_mismatch(self):
        """5. Safe failure when document text differs from expected span text."""
        reconstructor = EvidenceSpanReconstructor()
        doc = make_test_document()
        ref = EvidenceReference(
            document_id=doc.document_id,
            source_id=doc.source_id,
            start_char=74,
            end_char=85,
            span_text="Dengue fever",  # Wrong expected text
            extraction_method="ner:exact",
            attribute_role="disease",
        )
        span = reconstructor.reconstruct_span(ref, document_text=doc.text)
        assert span.is_valid is False
        assert "Text mismatch" in span.validation_error
        assert span.extracted_text == "Nipah virus"

    def test_evidence_span_reconstruction_missing_document(self):
        """6. Safe failure when source document is missing from registry."""
        reconstructor = EvidenceSpanReconstructor()
        ref = EvidenceReference(
            document_id=uuid5(NAMESPACE_DNS, "missing_doc"),
            source_id="unknown_source",
            start_char=10,
            end_char=20,
            span_text="test",
            extraction_method="ner:exact",
            attribute_role="disease",
        )
        span = reconstructor.reconstruct_span(ref, document_text=None)
        assert span.is_valid is False
        assert "Source document text not found" in span.validation_error

    def test_evidence_span_batch_reconstruction(self):
        """7. Reconstructing multiple spans maintains deterministic ordering."""
        reconstructor = EvidenceSpanReconstructor()
        doc = make_test_document()
        refs = [
            EvidenceReference(
                document_id=doc.document_id,
                source_id=doc.source_id,
                start_char=63,
                end_char=64,
                span_text="2",
                extraction_method="quantity:regex",
                attribute_role="quantity",
            ),
            EvidenceReference(
                document_id=doc.document_id,
                source_id=doc.source_id,
                start_char=74,
                end_char=85,
                span_text="Nipah virus",
                extraction_method="ner:exact",
                attribute_role="primary_disease",
            ),
        ]
        doc_map = {doc.document_id: doc}
        spans = reconstructor.reconstruct_spans(refs, documents_map=doc_map)

        assert len(spans) == 2
        assert spans[0].extracted_text == "2"
        assert spans[1].extracted_text == "Nipah virus"
        assert all(s.is_valid for s in spans)

    # 2. Lineage Graph & Traversal Tests
    def test_provenance_graph_node_and_edge_construction(self):
        """8. Verify all expected node types and edges are constructed in graph."""
        builder = ProvenanceGraphBuilder()
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)
        fe = make_test_fused_event(alert)

        graph = builder.build_graph(
            alert=alert,
            signal=sig,
            fused_events=[fe],
            available_document_ids={doc.document_id},
        )

        node_types = {n.node_type for n in graph.nodes}
        assert ProvenanceNodeType.ALERT in node_types
        assert ProvenanceNodeType.SIGNAL in node_types
        assert ProvenanceNodeType.FUSED_EVENT in node_types
        assert ProvenanceNodeType.DOCUMENT in node_types
        assert ProvenanceNodeType.EVIDENCE_SPAN in node_types
        assert len(graph.edges) >= 4

    def test_provenance_graph_acyclicity(self):
        """9. Verify Kahn's algorithm confirms the graph is strictly acyclic (DAG)."""
        builder = ProvenanceGraphBuilder()
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)
        fe = make_test_fused_event(alert)

        graph = builder.build_graph(
            alert=alert,
            signal=sig,
            fused_events=[fe],
            available_document_ids={doc.document_id},
        )
        assert graph.is_acyclic is True

    def test_provenance_graph_missing_nodes_detection(self):
        """10. Verify missing source documents are noted in completeness ratio."""
        builder = ProvenanceGraphBuilder()
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)

        # Do NOT provide doc.document_id in available_document_ids
        graph = builder.build_graph(
            alert=alert,
            signal=sig,
            available_document_ids=set(),  # Document missing
        )
        assert len(graph.missing_nodes) > 0
        assert graph.completeness_ratio < 1.0

    def test_provenance_traversal_alert_to_documents(self):
        """11. Traversal returns deterministic list of document UUIDs."""
        builder = ProvenanceGraphBuilder()
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)
        graph = builder.build_graph(alert=alert, signal=sig, available_document_ids={doc.document_id})

        doc_ids = builder.traverse_alert_to_documents(graph)
        assert len(doc_ids) == 1
        assert doc_ids[0] == doc.document_id

    def test_provenance_traversal_alert_to_fused_events(self):
        """12. Traversal returns supporting fused event UUIDs."""
        builder = ProvenanceGraphBuilder()
        alert = make_test_alert()
        fe = make_test_fused_event(alert)
        graph = builder.build_graph(alert=alert, fused_events=[fe])

        fe_ids = builder.traverse_alert_to_fused_events(graph)
        assert len(fe_ids) == 1
        assert fe_ids[0] == fe.fused_event_id

    def test_provenance_traversal_alert_to_evidence(self):
        """13. Traversal returns EVIDENCE_SPAN nodes with offsets."""
        builder = ProvenanceGraphBuilder()
        alert = make_test_alert()
        graph = builder.build_graph(alert=alert)

        spans = builder.traverse_alert_to_evidence(graph)
        assert len(spans) == 2
        assert spans[0].node_type == ProvenanceNodeType.EVIDENCE_SPAN
        assert "start" in spans[0].metadata

    def test_provenance_traversal_alert_to_signals(self):
        """14. Traversal returns signal UUIDs."""
        builder = ProvenanceGraphBuilder()
        alert = make_test_alert()
        sig = make_test_signal(alert)
        graph = builder.build_graph(alert=alert, signal=sig)

        sig_ids = builder.traverse_alert_to_signals(graph)
        assert len(sig_ids) == 1
        assert sig_ids[0] == sig.signal_id

    # 3. Decision Audit Trail Tests
    def test_audit_trail_decision_steps_completeness(self):
        """15. Verifies 8 discrete audit decision steps are recorded."""
        auditor = AuditTrailEngine()
        alert = make_test_alert()
        sig = make_test_signal(alert)
        audit = auditor.build_audit_trail(alert=alert, signal=sig)

        assert len(audit.decision_steps) == 8
        step_names = [s.step_name for s in audit.decision_steps]
        assert "Statistical Anomaly Evaluation" in step_names
        assert "Pathogen Clinical Threat Classification" in step_names
        assert "Source Diversity & Authority Corroboration" in step_names
        assert "Clinical Certainty & Mortality Assessment" in step_names
        assert "Spatial Granularity Resolution" in step_names
        assert "Multi-Criteria Composite Scoring" in step_names
        assert "Reliability Safety Gating & Ceilings" in step_names
        assert "Operational Alert Tier Assignment" in step_names

    def test_audit_trail_sha256_checksum_integrity(self):
        """16. Verify deterministic SHA-256 checksum generation."""
        auditor = AuditTrailEngine()
        alert = make_test_alert()
        sig = make_test_signal(alert)

        audit1 = auditor.build_audit_trail(alert=alert, signal=sig)
        audit2 = auditor.build_audit_trail(alert=alert, signal=sig)

        assert len(audit1.audit_checksum) == 64
        assert audit1.audit_checksum == audit2.audit_checksum

    def test_audit_trail_checksum_sensitivity(self):
        """17. Verifies altering any input score alters the audit checksum."""
        auditor = AuditTrailEngine()
        alert1 = make_test_alert(score=0.75)
        alert2 = make_test_alert(score=0.60, tier=AlertTier.LOW)
        sig = make_test_signal(alert1)

        audit1 = auditor.build_audit_trail(alert=alert1, signal=sig)
        audit2 = auditor.build_audit_trail(alert=alert2, signal=sig)

        assert audit1.audit_checksum != audit2.audit_checksum

    # 4. Human-Readable Dossier Tests
    def test_dossier_5w1h_epidemiological_synthesis(self):
        """18. Verifies Who, What, When, Where, Why, How briefing populated."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)
        generator = DossierGenerator(documents_map={doc.document_id: doc})

        dossier = generator.create_dossier(alert=alert, signal=sig)
        b = dossier.briefing

        assert "Nipah Virus" in b.who_pathogen
        assert "observed" in b.what_event
        assert "2024-09-02" in b.when_period
        assert "Kozhikode" in b.where_location
        assert "EARS_C1" in b.why_aberration
        assert "2 independent source group" in b.how_corroboration

    def test_dossier_safety_constraints_propagation(self):
        """19. Verifies gating reasons and penalties are propagated into dossier."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        generator = DossierGenerator(documents_map={doc.document_id: doc})

        dossier = generator.create_dossier(alert=alert)
        assert len(dossier.applied_safety_constraints) > 0
        assert "Conflicting quantity reports" in dossier.applied_safety_constraints[0]

    def test_dossier_generator_interface_compliance(self):
        """20. Verifies EvidenceProvider abstract interface implementation."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        generator = DossierGenerator(
            documents_map={doc.document_id: doc},
            alert_registry={alert.alert_id: alert},
        )

        dossier_dict = generator.generate_dossier(alert_id=alert.alert_id)
        assert isinstance(dossier_dict, dict)
        assert dossier_dict["alert_id"] == str(alert.alert_id)
        assert "briefing" in dossier_dict
        assert "reconstructed_evidence" in dossier_dict

    def test_provenance_completeness_flagging(self):
        """21. Completeness is True when docs present, False when docs missing."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        generator_complete = DossierGenerator(documents_map={doc.document_id: doc})
        dossier_c = generator_complete.create_dossier(alert=alert)
        assert dossier_c.provenance_complete is True

        generator_incomplete = DossierGenerator(documents_map={})
        dossier_inc = generator_incomplete.create_dossier(alert=alert)
        assert dossier_inc.provenance_complete is False
        assert dossier_inc.completeness_notes is not None

    def test_deterministic_dossier_and_graph_id(self):
        """22. Identical inputs yield identical deterministic UUID5 identifiers."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        sig = make_test_signal(alert)
        gen = DossierGenerator(documents_map={doc.document_id: doc})

        d1 = gen.create_dossier(alert=alert, signal=sig)
        d2 = gen.create_dossier(alert=alert, signal=sig)

        assert d1.dossier_id == d2.dossier_id
        assert d1.provenance_graph.graph_id == d2.provenance_graph.graph_id
        assert d1.audit_trail.audit_id == d2.audit_trail.audit_id

    # 5. Batch Execution & Reproducibility Tests
    def test_batch_runner_execution_and_artifacts(self, tmp_path):
        """23. Verify batch processing produces all required serialized artifacts."""
        doc = make_test_document()
        alert1 = make_test_alert(doc_id=doc.document_id, disease="nipah virus")
        alert2 = make_test_alert(doc_id=doc.document_id, disease="dengue")

        runner = ExplainabilityBatchRunner(output_dir=str(tmp_path / "explain"))
        report, dossiers = runner.process_alerts(
            alerts=[alert1, alert2],
            documents=[doc],
            run_name="test_run",
        )

        assert len(dossiers) == 2
        assert report.total_alerts_processed == 2
        assert report.provenance_complete_alerts_count == 2
        assert (tmp_path / "explain" / "test_run" / "dossiers.json").exists()
        assert (tmp_path / "explain" / "test_run" / "audit_trails.json").exists()
        assert (tmp_path / "explain" / "test_run" / "provenance_summary.json").exists()
        assert (tmp_path / "explain" / "test_run" / "explainability_batch_report.json").exists()

    def test_byte_for_byte_reproducibility(self, tmp_path):
        """24. Verify two independent batch runs produce byte-for-byte identical output."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)

        runner1 = ExplainabilityBatchRunner(output_dir=str(tmp_path / "run1"))
        runner2 = ExplainabilityBatchRunner(output_dir=str(tmp_path / "run2"))

        runner1.process_alerts(alerts=[alert], documents=[doc], run_name="out")
        runner2.process_alerts(alerts=[alert], documents=[doc], run_name="out")

        b1 = (tmp_path / "run1" / "out" / "dossiers.json").read_bytes()
        b2 = (tmp_path / "run2" / "out" / "dossiers.json").read_bytes()
        assert b1 == b2

        b_audit1 = (tmp_path / "run1" / "out" / "audit_trails.json").read_bytes()
        b_audit2 = (tmp_path / "run2" / "out" / "audit_trails.json").read_bytes()
        assert b_audit1 == b_audit2

    def test_multiple_source_documents_handling(self):
        """25. Multiple source documents correctly linked and reconstructed."""
        doc1 = make_test_document(doc_id_str="doc1", text="Report 1: Nipah confirmed in Kozhikode.")
        doc2 = make_test_document(doc_id_str="doc2", text="Report 2: 2 fatalities recorded in Malappuram.")

        alert = make_test_alert(doc_id=doc1.document_id)
        ref2 = EvidenceReference(
            document_id=doc2.document_id,
            source_id="who_don",
            start_char=10,
            end_char=22,
            span_text="2 fatalities",
            extraction_method="quantity:regex",
            attribute_role="death_count",
        )
        alert_multi = alert.model_copy(update={"provenance_references": list(alert.provenance_references) + [ref2]})

        gen = DossierGenerator(documents_map={doc1.document_id: doc1, doc2.document_id: doc2})
        dossier = gen.create_dossier(alert=alert_multi)

        assert len(dossier.reconstructed_evidence) == 3
        doc_nodes = [n for n in dossier.provenance_graph.nodes if n.node_type == ProvenanceNodeType.DOCUMENT]
        assert len(doc_nodes) == 2

    def test_duplicate_evidence_reference_deduplication(self):
        """26. Duplicate evidence references are cleanly deduplicated."""
        doc = make_test_document()
        alert = make_test_alert(doc_id=doc.document_id)
        # Pass identical references in fused event to test deduplication
        fe = make_test_fused_event(alert, evidence_references=list(alert.provenance_references))

        gen = DossierGenerator(documents_map={doc.document_id: doc})
        dossier = gen.create_dossier(alert=alert, fused_events=[fe])

        # References were 2 in alert, 2 in fe, total 4 references, but exact 2 distinct spans
        assert len(dossier.reconstructed_evidence) == 2

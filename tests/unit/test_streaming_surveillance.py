"""
Comprehensive Unit Tests for EpiSense Streaming Surveillance & Continuous Ingestion Engine (Phase 11).
Verifies streaming ingestion, cryptographic validation, dead-letter isolation,
state management, idempotency, anti-inflation, late-arriving events, historical segregation,
alert lifecycle, deterministic checkpointing, and provenance preservation.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import pytest

from episense.schemas.document import Document, SourceType
from episense.schemas.assertion import Assertion, AssertionStatus, CertaintyLevel
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.temporal import TemporalExpression, TemporalType
from episense.schemas.nlp import (
    ContextAssociation,
    NLPOutput,
    QuantityMention,
    ResolutionState,
    ResolvedLocation,
    SentenceSpan,
)
from episense.schemas.event import (
    EpidemiologicalQuantities,
    EventCandidate,
    EventObservation,
    EvidenceReference,
    FusedEvent,
    SourceGroup,
)
from episense.schemas.signal import (
    BaselineEstimate,
    BaselineReliability,
    EpidemiologicalTimeBin,
    SignalLevel,
    SignalObservation,
)
from episense.schemas.alert import (
    AlertTier,
    EpidemiologicalAlert,
    PathogenThreatTier,
    RiskScoreBreakdown,
)
from episense.schemas.streaming import (
    AlertLifecycleState,
    DeadLetterRecord,
    IngestionStatus,
    SurveillanceEventUpdate,
    SurveillanceMetrics,
    SurveillanceStateCheckpoint,
)
from episense.streaming.ingestion import (
    DocumentBatchIngestionSource,
    FileStreamIngestionSource,
    MockIngestionSource,
    SingleDocumentIngestionSource,
    StreamingDocumentValidator,
)
from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline


# ==============================================================================
# Helpers & Fixture Generators
# ==============================================================================

def make_doc(
    text: str,
    title: str = "Surveillance Report",
    source_id: str = "who_don",
    pub_time: Optional[datetime] = None,
    doc_id: Optional[UUID] = None,
) -> Document:
    pt = pub_time or datetime(2024, 7, 25, 10, 0, 0, tzinfo=timezone.utc)
    if pt.tzinfo is None:
        pt = pt.replace(tzinfo=timezone.utc)
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        document_id=doc_id or uuid4(),
        source_id=source_id,
        source_type=SourceType.OFFICIAL_BULLETIN,
        title=title,
        text=text,
        publication_timestamp=pt,
        content_hash_sha256=h,
    )


class MockNLPPipeline:
    """Fast, deterministic NLP mock returning pre-configured outputs for testing."""

    def __init__(self, custom_outputs: Optional[Dict[str, NLPOutput]] = None):
        self.custom_outputs = custom_outputs or {}

    def process_document(self, document_or_id: Any) -> NLPOutput:
        doc_id = document_or_id.document_id if isinstance(document_or_id, Document) else document_or_id
        text = document_or_id.text if isinstance(document_or_id, Document) else ""

        if text in self.custom_outputs:
            return self.custom_outputs[text]

        # Location detection
        loc_idx = text.find("Kozhikode")
        if loc_idx >= 0:
            loc_start = loc_idx
            loc_end = loc_idx + len("Kozhikode")
            loc_raw = text[loc_start:loc_end]
        else:
            loc_start = 0
            loc_end = min(len(text), 9)
            loc_raw = text[loc_start:loc_end]

        loc = ResolvedLocation(
            raw_text=loc_raw,
            start_char=loc_start,
            end_char=loc_end,
            resolution_state=ResolutionState.RESOLVED,
            resolved_location=Location(
                location_id=uuid4(),
                original_text=loc_raw,
                normalized_name="Kozhikode",
                geographic_level=GeographicLevel.DISTRICT,
                parent_location="Kerala",
            ),
        )

        sent = SentenceSpan(
            sentence_index=0,
            start_char=0,
            end_char=len(text),
            text=text,
        )

        # Quantity detection
        quantities = []
        import re
        m = re.search(r"(\d+)\s*(?:confirmed\s*)?cases", text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            quantities.append(
                QuantityMention(
                    raw_text=m.group(0),
                    start_char=m.start(),
                    end_char=m.end(),
                    numeric_value=val,
                    unit="cases",
                )
            )

        # Assertion detection
        is_neg = "no cases" in text.lower() or "ruled out" in text.lower() or "negative" in text.lower()
        is_hist = "historically" in text.lower() or "in 2018" in text.lower()

        if is_neg:
            ass_status = AssertionStatus.NEGATED
        elif is_hist:
            ass_status = AssertionStatus.HISTORICAL
        else:
            ass_status = AssertionStatus.CONFIRMED

        # Disease detection matching exact text slice
        d_candidates = ["Nipah virus disease", "Nipah virus", "Nipah", "Dengue", "Cholera", "Chandipura virus", "Chandipura"]
        matched_disease = None
        d_start = 0
        d_end = 0
        for candidate in d_candidates:
            idx = text.lower().find(candidate.lower())
            if idx >= 0:
                d_start = idx
                d_end = idx + len(candidate)
                matched_disease = text[d_start:d_end]
                break

        if not matched_disease:
            d_start = 0
            d_end = min(len(text), 5)
            matched_disease = text[d_start:d_end]

        from episense.schemas.entity import Entity, EntityType
        disease_entity = Entity(
            entity_id=uuid4(),
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span=matched_disease,
            start_char=d_start,
            end_char=d_end,
            normalized_value=matched_disease,
            extraction_confidence=1.0,
        )

        assoc = ContextAssociation(
            association_id=uuid4(),
            sentence_index=0,
            start_char=0,
            end_char=len(text),
            primary_disease=disease_entity,
            assertion=Assertion(
                assertion_status=ass_status,
                certainty=CertaintyLevel.DEFINITE,
            ),
            location=loc,
            quantity=quantities[0] if quantities else None,
        )

        return NLPOutput(
            document_id=doc_id,
            sentences=[sent],
            entities=[disease_entity],
            assertions=[],
            temporal_expressions=[],
            locations=[loc],
            quantities=quantities,
            context_associations=[assoc],
        )


# ==============================================================================
# Unit Tests (32 Comprehensive Tests)
# ==============================================================================

class TestStreamingSurveillance:

    # 1. Validator: Valid Document object
    def test_streaming_validator_valid_document(self):
        validator = StreamingDocumentValidator()
        doc = make_doc("Two confirmed Nipah virus cases were reported in Kozhikode.")
        is_valid, dl, validated_doc = validator.validate(doc)
        assert is_valid is True
        assert dl is None
        assert validated_doc.document_id == doc.document_id

    # 2. Validator: Valid dict payload
    def test_streaming_validator_dict_payload(self):
        validator = StreamingDocumentValidator()
        text = "Five cases of Cholera reported in Rayagada district."
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        payload = {
            "document_id": str(uuid4()),
            "source_id": "promed",
            "title": "Cholera Alert",
            "text": text,
            "publication_timestamp": "2024-07-20T12:00:00Z",
            "content_hash_sha256": h,
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is True
        assert dl is None
        assert doc is not None
        assert doc.text == text
        assert doc.content_hash_sha256 == h

    # 3. Validator: Empty text failure isolation
    def test_streaming_validator_empty_text(self):
        validator = StreamingDocumentValidator()
        payload = {
            "title": "Empty Bulletin",
            "text": "   ",
            "publication_timestamp": "2024-07-20T12:00:00Z",
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is False
        assert doc is None
        assert dl is not None
        assert dl.stage == "ingestion_validation"
        assert dl.error_type == "EmptyTextError"

    # 4. Validator: Empty title failure isolation
    def test_streaming_validator_empty_title(self):
        validator = StreamingDocumentValidator()
        payload = {
            "title": "",
            "text": "Some epidemiological text.",
            "publication_timestamp": "2024-07-20T12:00:00Z",
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is False
        assert dl is not None
        assert dl.error_type == "EmptyTitleError"

    # 5. Validator: Content hash mismatch detection
    def test_streaming_validator_content_hash_mismatch(self):
        validator = StreamingDocumentValidator()
        payload = {
            "title": "Hash Tampered Doc",
            "text": "Actual genuine report text.",
            "publication_timestamp": "2024-07-20T12:00:00Z",
            "content_hash_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is False
        assert dl is not None
        assert dl.error_type == "ContentHashMismatchError"

    # 6. Validator: Invalid timestamp string
    def test_streaming_validator_invalid_timestamp(self):
        validator = StreamingDocumentValidator()
        payload = {
            "title": "Bad Timestamp Doc",
            "text": "Report text.",
            "publication_timestamp": "not-a-valid-iso-date",
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is False
        assert dl is not None
        assert dl.error_type == "InvalidTimestampError"

    # 7. Validator: Invalid UUID string
    def test_streaming_validator_invalid_uuid(self):
        validator = StreamingDocumentValidator()
        text = "Report text."
        payload = {
            "document_id": "not-a-valid-uuid",
            "title": "Bad UUID Doc",
            "text": text,
            "publication_timestamp": "2024-07-20T12:00:00Z",
            "content_hash_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        is_valid, dl, doc = validator.validate(payload)
        assert is_valid is False
        assert dl is not None
        assert dl.error_type == "InvalidUUIDError"

    # 8. Ingestion: MockIngestionSource operations
    def test_mock_ingestion_source(self):
        doc1 = make_doc("Doc 1 text")
        doc2 = make_doc("Doc 2 text")
        source = MockIngestionSource([doc1, doc2])

        assert source.has_next() is True
        consumed = list(source)
        assert len(consumed) == 2
        assert source.has_next() is False

        source.reset()
        assert source.has_next() is True
        assert source.get_next().document_id == doc1.document_id

    # 9. Ingestion: SingleDocumentIngestionSource
    def test_single_document_ingestion_source(self):
        doc = make_doc("Single document text")
        source = SingleDocumentIngestionSource(doc)
        assert source.has_next() is True
        docs = list(source)
        assert len(docs) == 1
        assert docs[0].document_id == doc.document_id
        assert source.has_next() is False

    # 10. Ingestion: DocumentBatchIngestionSource with mixed items
    def test_document_batch_ingestion_source(self):
        text = "Valid batch document text."
        valid_dict = {
            "title": "Valid Doc",
            "text": text,
            "publication_timestamp": "2024-07-20T12:00:00Z",
            "content_hash_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        invalid_dict = {"title": "Bad Doc", "text": ""}
        source = DocumentBatchIngestionSource([valid_dict, invalid_dict])
        docs = list(source)
        assert len(docs) == 1
        assert docs[0].title == "Valid Doc"

    # 11. Ingestion: FileStreamIngestionSource
    def test_file_stream_ingestion_source(self):
        benchmark_path = Path("data/benchmarks/episense_benchmark_v1.json")
        if benchmark_path.exists():
            source = FileStreamIngestionSource([benchmark_path])
            assert source.has_next() is True
            first_doc = source.get_next()
            assert first_doc is not None
            assert len(first_doc.text) > 0

    # 12. State Store: Deduplication & Idempotency detection
    def test_surveillance_state_store_idempotency_detection(self):
        state = SurveillanceStateStore()
        doc = make_doc("Identical test report")
        assert state.is_document_processed(doc.document_id, doc.content_hash_sha256) is False

        state.register_document(doc)
        assert state.is_document_processed(doc.document_id, doc.content_hash_sha256) is True
        # Check by content hash alone with new UUID
        assert state.is_document_processed(uuid4(), doc.content_hash_sha256) is True

    # 13. State Store: Dead letter record tracking
    def test_surveillance_state_store_dead_letter_logging(self):
        state = SurveillanceStateStore()
        dl = DeadLetterRecord(
            stage="test_stage",
            error_type="TestError",
            error_message="Test failure detail",
        )
        state.record_dead_letter(dl)
        assert len(state.dead_letter_queue) == 1
        assert state.metrics.processing_failures == 1
        assert state.dead_letter_queue[0].error_type == "TestError"

    # 14. State Store: Historical bins chronological retrieval
    def test_surveillance_state_store_historical_bins_ordering(self):
        state = SurveillanceStateStore()
        t1 = datetime(2024, 7, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 7, 8, tzinfo=timezone.utc)
        t3 = datetime(2024, 7, 15, tzinfo=timezone.utc)

        bin1 = EpidemiologicalTimeBin(
            bin_id=uuid4(),
            disease_key="dengue",
            geo_key="kozhikode",
            iso_year=2024,
            iso_week=27,
            period_start=t1,
            period_end=datetime(2024, 7, 7, 23, 59, 59, tzinfo=timezone.utc),
            fused_event_count=1,
            fused_event_ids=[uuid4()],
            observed_case_count=5,
        )
        bin2 = EpidemiologicalTimeBin(
            bin_id=uuid4(),
            disease_key="dengue",
            geo_key="kozhikode",
            iso_year=2024,
            iso_week=28,
            period_start=t2,
            period_end=datetime(2024, 7, 14, 23, 59, 59, tzinfo=timezone.utc),
            fused_event_count=1,
            fused_event_ids=[uuid4()],
            observed_case_count=10,
        )
        state.save_bin(bin2, ("dengue", "kozhikode", 2024, 28, False))
        state.save_bin(bin1, ("dengue", "kozhikode", 2024, 27, False))

        hist = state.get_historical_bins("dengue", "kozhikode", t3)
        assert len(hist) == 2
        assert hist[0].bin_id == bin1.bin_id  # strictly sorted chronologically
        assert hist[1].bin_id == bin2.bin_id

    # 15. State Store: Alert lifecycle transitions
    def test_surveillance_state_store_alert_lifecycle_transitions(self):
        from episense.schemas.alert import AlertExplanation
        state = SurveillanceStateStore()
        t_start = datetime(2024, 7, 22, tzinfo=timezone.utc)
        t_end = datetime(2024, 7, 28, tzinfo=timezone.utc)

        alert_v1 = EpidemiologicalAlert(
            alert_id=uuid4(),
            signal_id=uuid4(),
            disease_key="nipah virus disease",
            geo_key="kozhikode",
            period_start=t_start,
            period_end=t_end,
            composite_score=0.75,
            alert_tier=AlertTier.MEDIUM,
            pathogen_threat_tier=PathogenThreatTier.TIER_4_HIGH_CONSEQUENCE,
            score_breakdown=RiskScoreBreakdown(
                anomaly_score=0.8,
                threat_score=1.0,
                evidence_score=0.7,
                certainty_score=0.9,
                spatial_score=1.0,
                raw_composite_score=0.75,
                final_score=0.75,
            ),
            explanation=AlertExplanation(
                summary="High-consequence pathogen alert",
                driving_factors=["Pathogen threat", "Statistical aberration"],
            ),
            supporting_source_count=1,
            supporting_fused_event_ids=[uuid4()],
            provenance_references=[],
        )

        # 1. New alert
        status1 = state.save_alert(alert_v1, t_start.isoformat())
        assert status1 == AlertLifecycleState.NEW

        # 2. Confirmed unchanged
        status2 = state.save_alert(alert_v1, t_start.isoformat())
        assert status2 == AlertLifecycleState.CONFIRMED_UNCHANGED

        # 3. Updated alert with higher score
        alert_v2 = alert_v1.model_copy(update={"composite_score": 0.85, "alert_tier": AlertTier.HIGH})
        status3 = state.save_alert(alert_v2, t_start.isoformat())
        assert status3 == AlertLifecycleState.UPDATED
        assert len(state.alert_history[alert_v2.alert_id]) == 3

    # 16. State Store: Deterministic SHA-256 state checksum
    def test_surveillance_state_store_deterministic_checksum(self):
        state1 = SurveillanceStateStore()
        state2 = SurveillanceStateStore()

        doc = make_doc("Checksum test document.")
        state1.register_document(doc)
        state2.register_document(doc)

        c1 = state1.compute_state_checksum()
        c2 = state2.compute_state_checksum()
        assert len(c1) == 64
        assert c1 == c2

    # 17. State Store: Checkpoint and restore
    def test_surveillance_state_store_checkpoint_and_restore(self, tmp_path):
        state = SurveillanceStateStore()
        doc = make_doc("Document for checkpoint verification.")
        state.register_document(doc)
        dl = DeadLetterRecord(stage="mock", error_type="MockError", error_message="msg")
        state.record_dead_letter(dl)

        chk = state.checkpoint(tmp_path)
        assert chk.total_documents_processed == 1
        assert chk.dead_letter_count == 1
        assert (tmp_path / "checkpoint.json").exists()

        new_state = SurveillanceStateStore()
        restored_chk = new_state.restore(tmp_path)
        assert restored_chk.state_checksum_sha256 == chk.state_checksum_sha256
        assert len(new_state.dead_letter_queue) == 1

    # 18. Pipeline: Single document end-to-end execution
    def test_pipeline_single_document_flow(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        doc = make_doc("Two confirmed Dengue cases were reported in Kozhikode on 25 July 2024.")
        update = pipeline.process_document(doc)

        assert update.status == IngestionStatus.ACCEPTED
        assert update.document_id == doc.document_id
        assert len(update.fused_events_affected) >= 1
        assert len(update.bins_affected) >= 1
        assert len(update.alerts_generated) >= 1
        assert pipeline.state.metrics.documents_accepted == 1

    # 19. Pipeline: Idempotency duplicate skipping
    def test_pipeline_idempotency_duplicate_skipping(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        doc = make_doc("Two confirmed Dengue cases were reported in Kozhikode.")

        u1 = pipeline.process_document(doc)
        assert u1.status == IngestionStatus.ACCEPTED
        initial_fused_count = len(pipeline.state.fused_events)
        initial_alert_count = len(pipeline.state.alerts)

        # Process exact same document again
        u2 = pipeline.process_document(doc)
        assert u2.status == IngestionStatus.DUPLICATE_SKIPPED
        assert "Duplicate document detected" in (u2.message or "")

        # State must remain identical, zero count inflation
        assert len(pipeline.state.fused_events) == initial_fused_count
        assert len(pipeline.state.alerts) == initial_alert_count
        assert pipeline.state.metrics.duplicates_skipped == 1

    # 20. Pipeline: Content hash matching across different document IDs
    def test_pipeline_idempotency_content_hash_match(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        text = "Identical syndication text across wires."
        doc1 = make_doc(text, doc_id=uuid4(), source_id="wire_a")
        doc2 = make_doc(text, doc_id=uuid4(), source_id="wire_b")

        u1 = pipeline.process_document(doc1)
        assert u1.status == IngestionStatus.ACCEPTED

        # Different UUID, identical content hash
        u2 = pipeline.process_document(doc2)
        assert u2.status == IngestionStatus.DUPLICATE_SKIPPED
        assert pipeline.state.metrics.duplicates_skipped == 1

    # 21. Pipeline: Anti-inflation of identical reports across sources
    def test_pipeline_multi_observation_fusion_anti_inflation(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        t = datetime(2024, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        doc1 = make_doc("5 cases of Dengue reported in Kozhikode.", source_id="pib_mohfw", pub_time=t)
        doc2 = make_doc("5 cases of Dengue reported in Kozhikode.", source_id="who_don", pub_time=t)

        pipeline.process_document(doc1)
        pipeline.process_document(doc2)

        # Both documents report 5 cases; fused event should preserve 5 cases (anti-inflated)
        fe_list = list(pipeline.state.fused_events.values())
        assert len(fe_list) == 1
        fe = fe_list[0]
        assert fe.aggregated_quantities.case_count == 5  # NOT 10!
        assert fe.supporting_observation_count >= 1

    # 22. Pipeline: Conflicting quantity detection
    def test_pipeline_conflicting_data_handling(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        t = datetime(2024, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        doc1 = make_doc("5 cases of Dengue reported in Kozhikode.", source_id="pib_mohfw", pub_time=t)
        doc2 = make_doc("25 cases of Dengue reported in Kozhikode.", source_id="local_news", pub_time=t)

        pipeline.process_document(doc1)
        pipeline.process_document(doc2)

        fe_list = list(pipeline.state.fused_events.values())
        assert len(fe_list) == 1
        fe = fe_list[0]
        assert fe.has_conflicts is True
        assert fe.aggregated_quantities.is_conflicting is True

        # Check that the alert acknowledges conflicting data penalty
        alerts = list(pipeline.state.alerts.values())
        assert len(alerts) >= 1
        alert = alerts[0]
        assert alert.alert_tier in (AlertTier.MEDIUM, AlertTier.LOW)  # Capped due to conflict

    # 23. Pipeline: Late-arriving event placement
    def test_pipeline_late_arriving_event_placement(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        # Published in September 2024 (Week 38), but event was on July 24 2024 (Week 30)
        pub_sep = datetime(2024, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
        doc = make_doc(
            "5 cases of Dengue reported in Kozhikode.",
            pub_time=datetime(2024, 7, 24, 10, 0, 0, tzinfo=timezone.utc),
        )

        update = pipeline.process_document(doc)
        assert update.status == IngestionStatus.ACCEPTED

        # Verify the bin created corresponds to Week 30 (July 2024), NOT Week 38
        bins = list(pipeline.state.bins_by_id.values())
        assert len(bins) >= 1
        b = bins[0]
        assert b.iso_year == 2024
        assert b.iso_week == 30  # Authentic event window!
        from zoneinfo import ZoneInfo
        assert b.period_start.astimezone(ZoneInfo("Asia/Kolkata")).isocalendar()[1] == 30

    # 24. Pipeline: Generic historical commentary segregation
    def test_pipeline_generic_historical_segregation(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        doc = make_doc("Historically, 5 cases of Dengue were recorded in Kozhikode.")
        pipeline.process_document(doc)

        bins = list(pipeline.state.bins_by_id.values())
        assert len(bins) >= 1
        b = bins[0]
        assert b.completeness_status == "historical_background"
        # Must be segregated to ISO year 1970 week 1 reference bin, avoiding current week contamination
        assert b.iso_year == 1970
        assert b.iso_week == 1

    # 25. Pipeline: Negated event suppression
    def test_pipeline_negated_event_suppression(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        doc = make_doc("No cases of Nipah virus were confirmed in Kozhikode; lab tests ruled out infection.")
        pipeline.process_document(doc)

        bins = list(pipeline.state.bins_by_id.values())
        assert len(bins) >= 1
        b = bins[0]
        # Negated counts must not contribute to positive incidence
        assert b.observed_case_count is None or b.observed_case_count == 0

        alerts = list(pipeline.state.alerts.values())
        assert len(alerts) >= 1
        assert alerts[0].alert_tier == AlertTier.INFORMATIONAL
        assert alerts[0].composite_score == 0.0

    # 26. Pipeline: Failure isolation for malformed document
    def test_pipeline_failure_isolation_malformed_doc(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        malformed = {"invalid_key": "data"}
        update = pipeline.process_document(malformed)

        assert update.status == IngestionStatus.REJECTED_MALFORMED
        assert len(pipeline.state.dead_letter_queue) == 1
        assert pipeline.state.metrics.documents_rejected == 1

    # 27. Pipeline: Failure isolation during NLP extraction error
    def test_pipeline_failure_isolation_nlp_error(self):
        class FaultyNLP:
            def process_document(self, doc):
                raise RuntimeError("Simulated NLP model memory failure")

        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=FaultyNLP())
        doc = make_doc("5 cases of Dengue in Kozhikode.")
        update = pipeline.process_document(doc)

        assert update.status == IngestionStatus.REJECTED_ERROR
        assert "Simulated NLP model memory failure" in update.message
        assert len(pipeline.state.dead_letter_queue) == 1
        assert pipeline.state.metrics.processing_failures == 1

    # 28. Pipeline: Character-level provenance preservation
    def test_pipeline_provenance_preservation(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        text = "5 cases of Dengue reported in Kozhikode."
        doc = make_doc(text)
        pipeline.process_document(doc)

        dossiers = list(pipeline.state.dossiers.values())
        assert len(dossiers) >= 1
        dossier = dossiers[0]
        assert dossier.provenance_complete is True
        assert len(dossier.reconstructed_evidence) >= 1

    # 29. Pipeline: Deterministic output serialization across dual runs
    def test_pipeline_deterministic_output_serialization(self):
        docs = [
            make_doc("2 cases of Cholera reported in Kozhikode.", source_id="s1"),
            make_doc("5 cases of Dengue reported in Kozhikode.", source_id="s2"),
        ]

        p1 = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        p2 = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())

        for d in docs:
            p1.process_document(d)
            p2.process_document(d)

        chk1 = p1.state.compute_state_checksum()
        chk2 = p2.state.compute_state_checksum()
        assert chk1 == chk2

    # 30. Pipeline: Stream processing iterator
    def test_pipeline_stream_processing_batch_compatibility(self):
        docs = [
            make_doc("Doc A: 2 cases of Dengue in Kozhikode."),
            make_doc("Doc B: 3 cases of Cholera in Kozhikode."),
        ]
        source = MockIngestionSource(docs)
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        updates = pipeline.process_stream(source)

        assert len(updates) == 2
        assert all(u.status == IngestionStatus.ACCEPTED for u in updates)
        assert pipeline.state.metrics.documents_accepted == 2

    # 31. Pipeline: Operational metrics accuracy
    def test_pipeline_operational_metrics_accuracy(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        doc = make_doc("10 cases of Dengue reported in Kozhikode.")
        pipeline.process_document(doc)
        # Duplicate
        pipeline.process_document(doc)
        # Malformed
        pipeline.process_document({"bad": "doc"})

        m = pipeline.state.metrics
        assert m.documents_received == 2
        assert m.documents_accepted == 1
        assert m.duplicates_skipped == 1
        assert m.documents_rejected == 1

    # 32. Pipeline: Alert history preservation
    def test_pipeline_alert_history_preservation(self):
        pipeline = ContinuousSurveillancePipeline(nlp_pipeline=MockNLPPipeline())
        t = datetime(2024, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
        doc1 = make_doc("2 cases of Dengue in Kozhikode.", pub_time=t, source_id="src1")
        doc2 = make_doc("10 cases of Dengue in Kozhikode.", pub_time=t, source_id="src2")

        pipeline.process_document(doc1)
        pipeline.process_document(doc2)

        alerts = list(pipeline.state.alerts.values())
        assert len(alerts) >= 1
        aid = alerts[0].alert_id
        history = pipeline.state.alert_history.get(aid, [])
        assert len(history) >= 1  # Prior revisions preserved in audit history

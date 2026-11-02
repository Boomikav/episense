"""
Unit Tests for EpiSense Data Integrity Refactor.
Verifies temporal integrity, non-clinical quantity rejection, event relevance gating,
zero-baseline signal suppression, and connector telemetry fields.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest

from episense.events.builder import EventCandidateBuilder
from episense.events.relevance import EventRelevanceCategory, EventRelevanceClassifier
from episense.nlp.quantities import QuantityExtractor
from episense.nlp.temporal.extractor import RuleBasedTemporalExtractor
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.signal import BaselineReliability, SignalLevel
from episense.schemas.source import SourceConnectorConfig, SourceConnectorStatus
from episense.anomaly.detector import SignalDetector
from episense.streaming.ingestion import StreamingDocumentValidator


class TestDataIntegrityRefactor:
    """Verifies that data provenance, temporal sanity, and statistical honesty are preserved."""

    def test_unreasonable_future_date_quarantined(self):
        """Documents with publication date > 48h in future must be quarantined."""
        validator = StreamingDocumentValidator()
        future_pub = datetime.now(timezone.utc) + timedelta(days=5)
        text = "Ten cases of Dengue were confirmed."

        doc = Document(
            document_id=uuid4(),
            source_id="who_don",
            source_type=SourceType.OFFICIAL_BULLETIN,
            origin=OriginClassification.LIVE_EXTERNAL,
            title="Future Outbreak Report",
            text=text,
            publication_timestamp=future_pub,
            content_hash_sha256=validator.calculate_sha256(text),
        )

        is_valid, dlq, validated_doc = validator.validate(doc)
        assert is_valid is False
        assert dlq is not None
        assert dlq.error_type == "UnreasonableFutureDateError"
        assert "unreasonably in the future" in dlq.error_message

    def test_missing_publication_date_preserved(self):
        """Missing publication dates must remain None, not substituted with current time."""
        validator = StreamingDocumentValidator()
        text = "Cholera outbreak reported in district."
        doc = Document(
            document_id=uuid4(),
            source_id="undated_bulletin",
            source_type=SourceType.OFFICIAL_BULLETIN,
            title="Undated Outbreak Notice",
            text=text,
            publication_timestamp=None,
            content_hash_sha256=validator.calculate_sha256(text),
        )

        is_valid, dlq, validated_doc = validator.validate(doc)
        assert is_valid is True
        assert validated_doc.publication_timestamp is None
        assert validated_doc.ingestion_timestamp is not None

    def test_future_policy_target_year_rejected_as_occurrence(self):
        """Mentions of future policy targets (e.g. 'towards the 2030 target') must not become event dates."""
        extractor = RuleBasedTemporalExtractor()
        text = "Health authorities reviewed national malaria milestones towards the 2030 target."
        doc_time = datetime(2024, 5, 10, tzinfo=timezone.utc)

        expressions = extractor.extract(text, reference_date=doc_time)
        extracted_text = [e.original_expression for e in expressions]

        # 2030 in 'towards the 2030 target' must not be extracted
        for raw in extracted_text:
            assert "2030" not in raw

    def test_non_clinical_quantity_rejected(self):
        """Numbers followed by non-clinical units (districts, states, years, percent) are rejected."""
        extractor = QuantityExtractor()
        text = "Review of transmission shows 140 districts and 12 states eligible, with 95 percent verification."
        quantities = extractor.extract(text)

        # Non-clinical units like districts, states, percent must be rejected
        for q in quantities:
            assert q.unit not in ("districts", "states", "percent", "years", "months", "pages")

    def test_event_relevance_classification_policy(self):
        """Diplomatic agreements and institutional news must be classified as non-outbreak."""
        classifier = EventRelevanceClassifier()
        title = "WHO and Kingdom of Saudi Arabia sign contribution agreement"
        text = "WHO Director-General met with representatives to cement bilateral cooperation and health strategy."

        decision = classifier.classify(title, text)
        assert decision.is_epidemiological_event is False
        assert decision.category == EventRelevanceCategory.POLICY_ADMINISTRATIVE_NEWS

    def test_event_relevance_classification_elimination(self):
        """Elimination program reviews must be classified as non-outbreak."""
        classifier = EventRelevanceClassifier()
        title = "Malaria elimination milestones review"
        text = "Country maintained zero indigenous transmission and awards verification of malaria-free status."

        decision = classifier.classify(title, text)
        assert decision.is_epidemiological_event is False
        assert decision.category == EventRelevanceCategory.ELIMINATION_PROGRAM_REVIEW

    def test_event_relevance_classification_outbreak(self):
        """Authentic disease reports with cases must be classified as acute outbreak reports."""
        classifier = EventRelevanceClassifier()
        title = "Surge in Dengue fever cases in West Bengal"
        text = "State hospitals admitted 450 confirmed Dengue cases over the past fortnight."

        decision = classifier.classify(title, text)
        assert decision.is_epidemiological_event is True
        assert decision.category == EventRelevanceCategory.ACUTE_OUTBREAK_REPORT

    def test_sparse_baseline_signal_suppressed(self):
        """When baseline is 0 or history is insufficient, statistical signals are honestly suppressed."""
        detector = SignalDetector()
        from episense.schemas.signal import BaselineEstimate, EpidemiologicalTimeBin

        baseline = BaselineEstimate(
            baseline_id=uuid4(),
            disease_key="nipah",
            geo_key="kozhikode",
            target_period_start=datetime(2024, 7, 21, tzinfo=timezone.utc),
            target_period_end=datetime(2024, 7, 27, tzinfo=timezone.utc),
            baseline_window_weeks=7,
            baseline_count=0.0,
            baseline_mean=0.0,
            baseline_median=0.0,
            baseline_std=0.0,
            baseline_variance=0.0,
            dispersion_metric=0.0,
            number_of_historical_bins=1,
            number_of_nonzero_bins=1,
            reliability_status=BaselineReliability.INSUFFICIENT_HISTORY,
            rationale="Insufficient historical bins (1 < 7).",
            method="ears_c1",
        )

        target_bin = EpidemiologicalTimeBin(
            disease_key="nipah",
            geo_key="kozhikode",
            period_start=datetime(2024, 7, 21, tzinfo=timezone.utc),
            period_end=datetime(2024, 7, 27, tzinfo=timezone.utc),
            iso_year=2024,
            iso_week=30,
            observed_case_count=2,
            fused_event_count=1,
            independent_source_count=1,
        )

        signal = detector.detect_signal(
            target_bin=target_bin,
            baseline=baseline,
            historical_bins=[],
            value_type="cases",
        )

        assert signal.signal_level == SignalLevel.NO_SIGNAL
        assert "Insufficient historical baseline data" in signal.downgrade_reason

    def test_source_connector_telemetry_schema(self):
        """Connector schema must include verified network and scheduling telemetry fields."""
        cfg = SourceConnectorConfig(
            source_id="test_feed",
            name="Test Public Health Feed",
            category=SourceType.OFFICIAL_BULLETIN,
            official_source_url="https://health.example.gov",
            endpoint_url="https://health.example.gov/feed.xml",
            is_configured=True,
            http_network_result=200,
            items_discovered=15,
            new_documents_ingested=3,
            items_skipped_duplicates=12,
            parsing_errors=[],
        )

        assert cfg.is_configured is True
        assert cfg.http_network_result == 200
        assert cfg.items_discovered == 15
        assert cfg.items_skipped_duplicates == 12

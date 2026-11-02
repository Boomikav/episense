"""
Unit Tests for EpiSense Grounded LLM Adapter.
Validates:
1. Verbatim evidence-span verification and hallucination detection.
2. Proper mapping of grounded LLM extractions to EpiSense NLPOutput schema.
3. Clean fallback to deterministic rule/spaCy pipeline when unconfigured or rejected.
"""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from episense.nlp.llm_adapter import (
    GroundedLLMAdapter,
    LLMExtractedEntity,
    LLMExtractedLocation,
    LLMExtractedQuantity,
    LLMStructuredExtraction,
)
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.assertion import AssertionStatus
from episense.nlp.pipeline import NLPPipeline


class TestGroundedLLMAdapter:

    def test_verbatim_grounding_verification_success(self):
        adapter = GroundedLLMAdapter(enable_llm=True, api_key="dummy-key")
        text = "Kozhikode health authorities reported 5 confirmed cases of Nipah virus on June 1st."

        extraction = LLMStructuredExtraction(
            primary_disease=LLMExtractedEntity(
                raw_span="Nipah virus",
                canonical_name="Nipah virus disease",
                start_char=59,
                end_char=70,
            ),
            location=LLMExtractedLocation(
                raw_span="Kozhikode",
                normalized_name="Kozhikode",
                start_char=0,
                end_char=9,
            ),
            quantities=[
                LLMExtractedQuantity(
                    raw_span="5 confirmed cases",
                    numeric_value=5.0,
                    start_char=38,
                    end_char=55,
                )
            ],
            assertion_status="confirmed",
            evidence_sentences=["Kozhikode health authorities reported 5 confirmed cases of Nipah virus on June 1st."],
        )

        res = adapter.verify_grounding(text, extraction)
        assert res.is_grounded is True
        assert res.hallucination_detected is False
        assert len(res.unmatched_spans) == 0
        assert len(res.verified_spans) >= 4

    def test_hallucination_detection_rejects_unmatched_span(self):
        adapter = GroundedLLMAdapter(enable_llm=True, api_key="dummy-key")
        text = "Kozhikode health authorities reported fever cases."

        # Extraction invents 'Ebola' and '100 cases'
        hallucinated_extraction = LLMStructuredExtraction(
            primary_disease=LLMExtractedEntity(
                raw_span="Ebola virus",
                canonical_name="Ebola virus disease",
                start_char=10,
                end_char=21,
            ),
            quantities=[
                LLMExtractedQuantity(
                    raw_span="100 cases",
                    numeric_value=100.0,
                    start_char=30,
                    end_char=39,
                )
            ],
            evidence_sentences=["100 patients died of Ebola in Kozhikode."],
        )

        res = adapter.verify_grounding(text, hallucinated_extraction)
        assert res.is_grounded is False
        assert res.hallucination_detected is True
        assert len(res.unmatched_spans) >= 2
        assert any("Ebola" in s for s in res.unmatched_spans)

    def test_conversion_to_nlp_output(self):
        adapter = GroundedLLMAdapter(enable_llm=True, api_key="dummy-key")
        doc_id = uuid4()
        text = "A cluster of Dengue was detected in Malappuram with 12 cases."

        extraction = LLMStructuredExtraction(
            primary_disease=LLMExtractedEntity(
                raw_span="Dengue",
                canonical_name="Dengue",
                start_char=13,
                end_char=19,
            ),
            location=LLMExtractedLocation(
                raw_span="Malappuram",
                normalized_name="Malappuram",
                start_char=36,
                end_char=46,
            ),
            quantities=[
                LLMExtractedQuantity(
                    raw_span="12 cases",
                    numeric_value=12.0,
                    start_char=52,
                    end_char=60,
                )
            ],
            assertion_status="suspected",
        )

        nlp_output = adapter.to_nlp_output(doc_id, text, extraction)

        assert nlp_output.document_id == doc_id
        assert len(nlp_output.entities) == 1
        assert nlp_output.entities[0].text_span == "Dengue"
        assert nlp_output.entities[0].normalized_value == "Dengue"

        assert len(nlp_output.locations) == 1
        assert nlp_output.locations[0].resolved_location.normalized_name == "Malappuram"

        assert len(nlp_output.quantities) == 1
        assert nlp_output.quantities[0].numeric_value == 12.0

        assert len(nlp_output.context_associations) == 1
        assert nlp_output.context_associations[0].assertion.assertion_status == AssertionStatus.SUSPECTED

    def test_clean_fallback_when_llm_disabled(self):
        import hashlib
        adapter = GroundedLLMAdapter(enable_llm=False)
        nlp_fallback = NLPPipeline(enable_cache=False)

        text = "Health department confirms 15 cases of Dengue in Kozhikode district."
        doc = Document(
            document_id=uuid4(),
            source_id="test_feed",
            source_type=SourceType.NEWS_MEDIA,
            origin=OriginClassification.LIVE_EXTERNAL,
            title="Dengue outbreak",
            text=text,
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            publication_timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )

        # Process via adapter with fallback
        output = adapter.process_document(doc, fallback_pipeline=nlp_fallback)

        assert output.document_id == doc.document_id
        assert len(output.entities) > 0
        assert any(e.text_span == "Dengue" for e in output.entities)

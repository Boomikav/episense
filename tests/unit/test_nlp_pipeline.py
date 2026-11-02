"""
Comprehensive Unit Tests for EpiSense Context-Aware NLP Extraction Engine (Phase 6).
Verifies offset invariants, entity extraction, assertions, temporal, geographic,
quantity, context association, provenance, serialization, and gold evaluation.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4
import pytest

from episense.schemas.document import Document, SourceType
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import AssertionStatus, CertaintyLevel
from episense.schemas.temporal import TemporalType
from episense.schemas.nlp import ResolutionState, NLPOutput
from episense.nlp.loader import DocumentTextLoader
from episense.nlp.segmentation import SentenceSegmenter
from episense.nlp.models import ModelManager
from episense.nlp.entities.extractor import HybridHealthEntityExtractor
from episense.nlp.entities.normalizer import EntityNormalizer
from episense.nlp.assertion.analyzer import ContextualAssertionAnalyzer
from episense.nlp.temporal.extractor import RuleBasedTemporalExtractor
from episense.nlp.geospatial.resolver import CautiousLocationResolver
from episense.nlp.quantities import QuantityExtractor
from episense.nlp.context import ContextAssociator
from episense.nlp.provenance import ProvenanceValidator
from episense.nlp.pipeline import NLPPipeline
from episense.nlp.batch import BatchRunner
from episense.nlp.evaluation import GoldEvaluator
from episense.exceptions import NLPExtractionError, MalformedInputError


class TestNLPPipeline:

    @pytest.fixture(scope="class")
    def web_nlp(self):
        return ModelManager.get_web_model()

    @pytest.fixture(scope="class")
    def sci_nlp(self):
        return ModelManager.get_sci_model()

    @pytest.fixture(scope="class")
    def pipeline(self):
        # Disable cache for clean unit tests
        return NLPPipeline(enable_cache=False)

    # 1. Text Loader and Empty Input Safety
    def test_loader_text_and_empty_safety(self, tmp_path):
        loader = DocumentTextLoader(raw_data_dir=tmp_path)
        doc_id = uuid4()
        file_path = tmp_path / f"{doc_id}.txt"
        file_path.write_text("Dengue cases reported in Vellore.", encoding="utf-8")

        loaded_id, text, _ = loader.load_text(doc_id)
        assert loaded_id == doc_id
        assert text == "Dengue cases reported in Vellore."

        # Empty document raises MalformedInputError
        empty_id = uuid4()
        (tmp_path / f"{empty_id}.txt").write_text("   \n  ", encoding="utf-8")
        with pytest.raises(MalformedInputError):
            loader.load_text(empty_id)

    # 2. Sentence Segmentation and Offset Invariant
    def test_sentence_segmentation_offsets(self, web_nlp):
        segmenter = SentenceSegmenter()
        text = "First sentence about Nipah. Second sentence regarding Kozhikode."
        doc = web_nlp(text)
        sentences = segmenter.segment(text, doc)

        assert len(sentences) == 2
        for s in sentences:
            # Exact character slice check
            assert text[s.start_char:s.end_char] == s.text

    # 3. Health Entity Extraction and Exact Offsets
    def test_entity_extraction_and_provenance(self, sci_nlp, web_nlp):
        extractor = HybridHealthEntityExtractor(sci_nlp=sci_nlp, web_nlp=web_nlp)
        text = "Patients presented with acute respiratory distress and fever due to Nipah virus disease."
        doc_id = uuid4()
        entities = extractor.extract(text, doc_id)

        assert len(entities) >= 3
        # Check every entity satisfies offset invariant
        for e in entities:
            assert text[e.start_char:e.end_char] == e.text_span

        types = {e.entity_type for e in entities}
        assert EntityType.DISEASE in types
        assert EntityType.SYMPTOM in types

    # 4. Entity Normalization (ICD-10 Mapping)
    def test_entity_normalization(self):
        norm = EntityNormalizer()
        canon, icd = norm.normalize_disease("Nipah virus disease")
        assert canon == "Nipah virus disease"
        # In ICD-10, Nipah has no assigned code (B27.8 is infectious mononucleosis); returns None
        assert icd is None

        canon_d, icd_d = norm.normalize_disease("dengue fever")
        assert canon_d == "Dengue"
        assert icd_d == "ICD10:A90"

        # Unknown/unresolved returns None without inventing
        canon_u, icd_u = norm.normalize_disease("mysterious space pathogen")
        assert canon_u is None
        assert icd_u is None

    # 5. Assertion and Negation Scoping
    def test_assertion_and_negation_scoping(self, web_nlp):
        analyzer = ContextualAssertionAnalyzer(nlp=web_nlp)
        text = "No cholera cases were detected, but two laboratory-confirmed Nipah cases occurred."
        doc_id = uuid4()

        e_cholera = Entity(
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span="cholera",
            start_char=3,
            end_char=10,
        )
        e_nipah = Entity(
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span="Nipah",
            start_char=61,
            end_char=66,
        )

        assertions = analyzer.analyze(text, [e_cholera, e_nipah])
        assert len(assertions) == 2

        # Cholera is negated
        assert assertions[0].assertion_status == AssertionStatus.NEGATED
        assert assertions[0].is_negated is True

        # Nipah is confirmed
        assert assertions[1].assertion_status == AssertionStatus.CONFIRMED
        assert assertions[1].is_negated is False

    # 6. Temporal Extraction and Publication vs Event Time
    def test_temporal_extraction_and_separation(self, web_nlp):
        extractor = RuleBasedTemporalExtractor(web_nlp=web_nlp)
        pub_date = datetime(2026, 6, 18, 12, 0, 0, tzinfo=timezone.utc)
        text = "The outbreak occurred between 12 and 18 January 2026, but the report was issued on 22 May 2026."

        temporals = extractor.extract(text, reference_date=pub_date)
        assert len(temporals) >= 2

        # Check offsets
        for t in temporals:
            assert text[t.start_char:t.end_char] == t.original_expression

        # First expression is an interval
        interval_expr = [t for t in temporals if t.temporal_type == TemporalType.INTERVAL]
        assert len(interval_expr) >= 1
        assert interval_expr[0].normalized_start.year == 2026
        assert interval_expr[0].normalized_start.month == 1
        assert interval_expr[0].normalized_start.day == 12

    # 7. Geographic Resolution and Explicit States
    def test_geographic_resolution_states(self, web_nlp):
        resolver = CautiousLocationResolver(nlp=web_nlp)
        text = "Cases were reported in Kozhikode district, Kerala, and also in ImaginaryLand."

        mentions = resolver.resolve_mentions(text)
        assert len(mentions) >= 2

        # Check offsets
        for m in mentions:
            assert text[m.start_char:m.end_char] == m.raw_text

        by_text = {m.raw_text: m for m in mentions}
        if "Kozhikode district" in by_text:
            assert by_text["Kozhikode district"].resolution_state == ResolutionState.RESOLVED
            assert by_text["Kozhikode district"].resolved_location.parent_location == "Kerala"

        if "Kerala" in by_text:
            assert by_text["Kerala"].resolution_state == ResolutionState.RESOLVED
            assert by_text["Kerala"].resolved_location.parent_location == "India"

        if "ImaginaryLand" in by_text:
            assert by_text["ImaginaryLand"].resolution_state == ResolutionState.UNRESOLVED

    # 8. Quantity Extraction
    def test_quantity_extraction(self, web_nlp):
        extractor = QuantityExtractor(nlp=web_nlp)
        text = "A total of 14 confirmed cases and 5 deaths were recorded among 178 contacts."

        quantities = extractor.extract(text)
        assert len(quantities) >= 3

        for q in quantities:
            assert text[q.start_char:q.end_char] == q.raw_text

        vals = [q.numeric_value for q in quantities]
        assert 14.0 in vals
        assert 5.0 in vals
        assert 178.0 in vals

    # 9. Sentence-Level Context Association
    def test_context_association(self, pipeline):
        text = "Two confirmed Nipah cases were reported in Kozhikode on 18 June 2026."
        doc_id = uuid4()
        doc = Document(
            document_id=doc_id,
            source_id="test_source",
            source_type=SourceType.BENCHMARK_CORPUS,
            title="Nipah Alert",
            text=text,
            publication_timestamp=datetime(2026, 6, 18, tzinfo=timezone.utc),
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

        output: NLPOutput = pipeline.process_document(doc)
        assert len(output.context_associations) >= 1

        assoc = output.context_associations[0]
        assert assoc.primary_disease is not None
        assert "Nipah" in assoc.primary_disease.text_span
        assert assoc.assertion is not None
        assert assoc.assertion.assertion_status == AssertionStatus.CONFIRMED
        assert assoc.location is not None
        assert "Kozhikode" in assoc.location.raw_text

    # 10. Complete Provenance Invariant Check
    def test_provenance_invariant(self, pipeline):
        text = "Health authorities verified 12 dengue cases in Vellore yesterday."
        doc_id = uuid4()
        doc = Document(
            document_id=doc_id,
            source_id="test_source",
            source_type=SourceType.BENCHMARK_CORPUS,
            title="Dengue Report",
            text=text,
            publication_timestamp=datetime(2026, 6, 18, tzinfo=timezone.utc),
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

        output: NLPOutput = pipeline.process_document(doc)
        assert len(output.provenance_records) > 0

        for rec in output.provenance_records:
            slice_text = text[rec.start_char:rec.end_char]
            assert len(slice_text) > 0
            assert rec.document_id == doc_id

    # 11. Serialization and Deserialization
    def test_nlp_output_serialization(self, pipeline):
        text = "Measles outbreak in Katpadi with fever and rash."
        doc_id = uuid4()
        doc = Document(
            document_id=doc_id,
            source_id="test_source",
            source_type=SourceType.BENCHMARK_CORPUS,
            title="Measles Report",
            text=text,
            publication_timestamp=datetime(2026, 6, 18, tzinfo=timezone.utc),
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

        output: NLPOutput = pipeline.process_document(doc)
        json_str = output.model_dump_json()
        deserialized = NLPOutput.model_validate_json(json_str)

        assert deserialized.document_id == doc_id
        assert len(deserialized.sentences) == len(output.sentences)
        assert len(deserialized.entities) == len(output.entities)

    # 12. Batch Runner Execution
    def test_batch_runner_execution(self, tmp_path, pipeline):
        runner = BatchRunner(pipeline=pipeline, output_base_dir=str(tmp_path))
        doc_id = uuid4()
        raw_file = Path("data/raw") / f"{doc_id}.txt"
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text("Cholera confirmed in Puri.", encoding="utf-8")

        try:
            report, outputs = runner.process_documents([{"document_id": str(doc_id)}], run_name="test_run")
            assert report.total_documents == 1
            assert report.processed_count == 1
            assert report.failed_count == 0
            assert len(outputs) == 1
            assert outputs[0].document_id == doc_id
        finally:
            if raw_file.exists():
                raw_file.unlink()

    # 13. Gold Evaluator Real Execution
    def test_gold_evaluation_execution(self, pipeline):
        evaluator = GoldEvaluator(pipeline=pipeline)
        results = evaluator.evaluate()

        assert results["gold_document_count"] == 18
        assert results["gold_span_count"] == 96
        assert "span_exact_match" in results
        assert "entity_classification_micro" in results
        assert results["temporal_evaluation"]["event_time_vs_pub_time"] == "NOT EVALUABLE WITH CURRENT GOLD DATA"
        assert results["geographic_grounding_evaluation"]["status"] == "NOT EVALUABLE WITH CURRENT GOLD DATA"

    # 14. Real Gold Document Regression
    def test_gold_document_regression(self, pipeline):
        # Use first gold document: Nipah outbreak in Kozhikode (8a919512-1b53-5800-b6d2-d05c2957fb5a)
        doc_id = UUID("8a919512-1b53-5800-b6d2-d05c2957fb5a")
        output: NLPOutput = pipeline.process_document(doc_id)

        raw_text = Path("data/raw/8a919512-1b53-5800-b6d2-d05c2957fb5a.txt").read_text(encoding="utf-8")

        # Verify all extracted offsets match raw_text perfectly
        for e in output.entities:
            assert raw_text[e.start_char:e.end_char] == e.text_span
        for t in output.temporal_expressions:
            assert raw_text[t.start_char:t.end_char] == t.original_expression
        for loc in output.locations:
            assert raw_text[loc.start_char:loc.end_char] == loc.raw_text
        for q in output.quantities:
            assert raw_text[q.start_char:q.end_char] == q.raw_text

        # Verify key entities extracted
        disease_names = [e.text_span for e in output.entities if e.entity_type == EntityType.DISEASE]
        assert any("Nipah" in d for d in disease_names)

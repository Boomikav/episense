"""
Unit tests for benchmark dataset and annotation schemas.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from episense.schemas.document import Document, SourceType
from episense.schemas.dataset import (
    AnnotationLayer,
    AnnotationSpan,
    BenchmarkDocument,
    BenchmarkManifest,
    DatasetSplit,
)


def create_sample_doc(text="Sample text") -> Document:
    import hashlib
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        document_id=uuid4(),
        source_id="who_don",
        source_type=SourceType.BENCHMARK_CORPUS,
        title="Outbreak Notice",
        text=text,
        publication_timestamp=datetime.now(timezone.utc),
        content_hash_sha256=h,
    )


def test_annotation_span_valid():
    """Verify valid annotation span instantiation."""
    span = AnnotationSpan(
        layer=AnnotationLayer.ENTITY,
        label="DISEASE",
        start_char=10,
        end_char=16,
        span_text="dengue",
        normalized_value="ICD10:A90",
    )
    assert span.span_text == "dengue"
    assert span.layer == AnnotationLayer.ENTITY


def test_annotation_span_invalid_offsets():
    """Verify annotation span rejects end_char <= start_char."""
    with pytest.raises(ValidationError):
        AnnotationSpan(
            layer=AnnotationLayer.ENTITY,
            label="DISEASE",
            start_char=20,
            end_char=15,  # Invalid
            span_text="dengue",
        )

    with pytest.raises(ValidationError):
        AnnotationSpan(
            layer=AnnotationLayer.ENTITY,
            label="DISEASE",
            start_char=10,
            end_char=10,  # Equal is invalid
            span_text="dengue",
        )


def test_benchmark_document_composition():
    """Verify BenchmarkDocument binds raw Document with annotations and split."""
    doc = create_sample_doc("Dengue reported in Katpadi.")
    span = AnnotationSpan(
        layer=AnnotationLayer.GEOGRAPHIC,
        label="DISTRICT",
        start_char=19,
        end_char=26,
        span_text="Katpadi",
    )
    bdoc = BenchmarkDocument(
        document=doc,
        split=DatasetSplit.BENCHMARK,
        annotations=[span],
        license_or_usage_note="Public health release under open terms",
    )
    assert bdoc.document.title == "Outbreak Notice"
    assert len(bdoc.annotations) == 1
    assert bdoc.annotations[0].span_text == "Katpadi"


def test_benchmark_manifest_validation():
    """Verify BenchmarkManifest validates counts and detects duplicates."""
    doc1 = create_sample_doc("Text of article 1")
    doc2 = create_sample_doc("Text of article 2")

    bdoc1 = BenchmarkDocument(
        document=doc1,
        split=DatasetSplit.BENCHMARK,
        license_or_usage_note="Open Access",
    )
    bdoc2 = BenchmarkDocument(
        document=doc2,
        split=DatasetSplit.BENCHMARK,
        license_or_usage_note="Open Access",
    )

    # Valid manifest
    manifest = BenchmarkManifest(
        dataset_name="episense_benchmark_india",
        version="0.1.0",
        description="Curated benchmark for early epidemic intelligence",
        geographic_scope="India",
        document_count=2,
        documents=[bdoc1, bdoc2],
        sources_included=["who_don"],
    )
    assert manifest.document_count == 2

    # Invalid manifest: document_count mismatch
    with pytest.raises(ValidationError):
        BenchmarkManifest(
            dataset_name="invalid_manifest",
            version="0.1.0",
            description="Test",
            geographic_scope="India",
            document_count=5,  # Mismatch (len is 2)
            documents=[bdoc1, bdoc2],
        )

    # Invalid manifest: duplicate document IDs
    with pytest.raises(ValidationError):
        BenchmarkManifest(
            dataset_name="duplicate_manifest",
            version="0.1.0",
            description="Test",
            geographic_scope="India",
            document_count=2,
            documents=[bdoc1, bdoc1],  # Duplicate document
        )

"""
Unit tests for human annotation schemas and gold annotation release verification.
"""

import json
from pathlib import Path
import pytest
from uuid import uuid4
from pydantic import ValidationError

from episense.schemas.annotation import (
    AnnotationStatus,
    DetailedAnnotationSpan,
    DocumentAnnotation,
    EntityCategory,
    AssertionLabel,
    EventStatus,
    GoldAnnotationRelease,
)


def test_annotation_span_validation():
    """Verify offset rules and category enforcement on DetailedAnnotationSpan."""
    span = DetailedAnnotationSpan(
        start_char=5,
        end_char=12,
        span_text="cholera",
        entity_label=EntityCategory.DISEASE,
        assertion_label=AssertionLabel.CONFIRMED,
        normalized_value="ICD10:A00",
    )
    assert span.span_text == "cholera"
    assert span.entity_label == EntityCategory.DISEASE

    # Inverted offsets must raise ValidationError
    with pytest.raises(ValidationError):
        DetailedAnnotationSpan(
            start_char=20,
            end_char=10,
            span_text="cholera",
            entity_label=EntityCategory.DISEASE,
        )


def test_gold_annotation_release_loads_and_verifies_spans():
    """
    Loads gold_annotations_v1.json and verifies that every annotated span
    matches the exact substring in the raw source file on disk.
    """
    gold_path = Path("data/benchmarks/annotations/gold_annotations_v1.json")
    assert gold_path.exists(), "Gold annotation file missing!"

    with open(gold_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    release = GoldAnnotationRelease(**data)
    assert release.document_count == 18
    assert len(release.documents) == 18

    raw_dir = Path("data/raw")
    total_spans_verified = 0

    for doc_ann in release.documents:
        doc_id = str(doc_ann.document_id)
        raw_file = raw_dir / f"{doc_id}.txt"
        assert raw_file.exists(), f"Raw file for {doc_id} missing!"

        with open(raw_file, "r", encoding="utf-8") as rf:
            raw_text = rf.read()

        for span in doc_ann.spans:
            extracted_text = raw_text[span.start_char:span.end_char]
            assert extracted_text == span.span_text, (
                f"Span mismatch in doc {doc_id}! "
                f"Expected '{span.span_text}', got '{extracted_text}' "
                f"at offsets ({span.start_char}:{span.end_char})"
            )
            total_spans_verified += 1

    assert total_spans_verified >= 80, f"Expected >= 80 spans, got {total_spans_verified}"

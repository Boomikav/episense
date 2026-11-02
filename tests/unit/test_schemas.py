"""
Tests verifying domain schema instantiation, constraints, and rejection of invalid data.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from episense.schemas.document import Document
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import Assertion, AssertionStatus
from episense.schemas.temporal import TemporalExpression, TemporalType
from episense.schemas.location import Location, GeographicLevel
from episense.schemas.event import HealthEvent
from episense.schemas.provenance import ProvenanceRecord


def test_document_valid():
    doc = Document(
        source_id="who_don",
        title="Outbreak News",
        text="A report of cholera.",
        publication_timestamp=datetime.now(timezone.utc),
        content_hash_sha256="0" * 64,
    )
    assert doc.title == "Outbreak News"


def test_document_invalid_hash_rejected():
    with pytest.raises(ValidationError):
        Document(
            source_id="who_don",
            title="Outbreak News",
            text="A report.",
            publication_timestamp=datetime.now(timezone.utc),
            content_hash_sha256="short_hash",  # Invalid length (must be 64)
        )


def test_entity_valid_offsets():
    doc_id = uuid4()
    ent = Entity(
        document_id=doc_id,
        entity_type=EntityType.DISEASE,
        text_span="dengue",
        start_char=10,
        end_char=16,
    )
    assert ent.text_span == "dengue"


def test_entity_invalid_offsets_rejected():
    doc_id = uuid4()
    # end_char <= start_char must fail
    with pytest.raises(ValidationError):
        Entity(
            document_id=doc_id,
            entity_type=EntityType.DISEASE,
            text_span="dengue",
            start_char=20,
            end_char=10,
        )


def test_health_event_composition(sample_document, sample_provenance):
    disease = Entity(
        document_id=sample_document.document_id,
        entity_type=EntityType.DISEASE,
        text_span="dengue",
        start_char=41,
        end_char=47,
    )
    assertion = Assertion(
        assertion_status=AssertionStatus.SUSPECTED,
        is_negated=False,
    )
    location = Location(
        original_text="Katpadi",
        normalized_name="Katpadi",
        geographic_level=GeographicLevel.DISTRICT,
    )
    event = HealthEvent(
        document_id=sample_document.document_id,
        primary_disease=disease,
        assertion=assertion,
        location=location,
        provenance=sample_provenance,
    )
    assert event.primary_disease.text_span == "dengue"
    assert event.assertion.assertion_status == AssertionStatus.SUSPECTED
    assert event.is_actionable is True

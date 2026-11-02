"""
Shared pytest fixtures for EpiSense tests.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from episense.schemas.document import Document, SourceType
from episense.schemas.entity import Entity, EntityType
from episense.schemas.assertion import Assertion, AssertionStatus
from episense.schemas.provenance import ProvenanceRecord


@pytest.fixture
def sample_document() -> Document:
    return Document(
        document_id=uuid4(),
        source_id="promed_archive",
        source_type=SourceType.BENCHMARK_CORPUS,
        title="Dengue fever cases reported in Vellore district",
        text="Health officials reported 14 suspected cases of dengue in Katpadi on Thursday.",
        publication_timestamp=datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc),
        content_hash_sha256="a" * 64,
    )


@pytest.fixture
def sample_provenance(sample_document) -> ProvenanceRecord:
    return ProvenanceRecord(
        document_id=sample_document.document_id,
        source_id=sample_document.source_id,
        start_char=41,
        end_char=47,
        extraction_method="mock_ner_v1",
        confidence=0.95,
    )

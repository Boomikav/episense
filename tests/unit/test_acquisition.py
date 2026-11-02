"""
Unit tests for data acquisition, source registry, validation, and deduplication.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from episense.acquisition.source_registry import (
    AccessMethod,
    SourceMetadata,
    SourceRegistry,
    SourceStatus,
)
from episense.acquisition.validation import DocumentValidator
from episense.acquisition.deduplication import ExactDeduplicator
from episense.exceptions import ConfigurationError, MalformedInputError


# ------------------------------------------------------------------------------
# Source Registry Tests
# ------------------------------------------------------------------------------

def test_source_registry_default_population():
    """Verify default registry contains verified institutional sources."""
    registry = SourceRegistry.create_default_registry()
    sources = registry.list_sources()
    assert len(sources) >= 5

    # Verify key verified sources exist
    ids = {s.source_id for s in sources}
    assert "ncdc_idsp_india" in ids
    assert "who_don" in ids
    assert "pib_mohfw_india" in ids
    assert "promed_mail" in ids
    assert "medrxiv_preprints" in ids


def test_source_registry_query_and_filtering():
    """Verify filtering by geographic scope and access method."""
    registry = SourceRegistry.create_default_registry()

    india_sources = registry.list_sources(geographic_scope="India")
    assert len(india_sources) >= 2
    for s in india_sources:
        assert "india" in s.geographic_scope.lower()

    rss_sources = registry.list_sources(access_method=AccessMethod.RSS_FEED)
    assert len(rss_sources) >= 1
    assert rss_sources[0].source_id == "pib_mohfw_india"


def test_source_registry_duplicate_registration_rejected():
    """Verify that registering the same source_id twice raises ConfigurationError."""
    registry = SourceRegistry()
    src = SourceMetadata(
        source_id="test_source",
        organization="Test Org",
        source_name="Test Source",
        source_type="official_bulletin",
        official_url="https://example.org",
        geographic_scope="Global",
        document_format="html",
        licensing_or_terms="Open Access",
    )
    registry.register(src)
    with pytest.raises(ConfigurationError):
        registry.register(src)


# ------------------------------------------------------------------------------
# Document Validation Tests
# ------------------------------------------------------------------------------

def test_document_validation_success():
    """Verify validation passes on complete, well-formed document dictionary."""
    text = "Confirmed cholera outbreak in district hospital."
    content_hash = DocumentValidator.calculate_sha256(text)
    doc_dict = {
        "document_id": str(uuid4()),
        "source_id": "who_don",
        "title": "Cholera in District",
        "text": text,
        "publication_timestamp": datetime.now(timezone.utc),
        "content_hash_sha256": content_hash,
    }
    is_valid, errors = DocumentValidator.validate_document_dict(doc_dict)
    assert is_valid is True
    assert len(errors) == 0


def test_document_validation_missing_fields():
    """Verify validation fails when required fields are missing."""
    doc_dict = {
        "document_id": str(uuid4()),
        # missing source_id, title, text, publication_timestamp, content_hash_sha256
    }
    is_valid, errors = DocumentValidator.validate_document_dict(doc_dict)
    assert is_valid is False
    assert len(errors) >= 5


def test_document_validation_hash_mismatch():
    """Verify validation rejects content hash that does not match text."""
    doc_dict = {
        "document_id": str(uuid4()),
        "source_id": "who_don",
        "title": "Cholera in District",
        "text": "Actual document text",
        "publication_timestamp": datetime.now(timezone.utc),
        "content_hash_sha256": "0" * 64,  # Invalid hash
    }
    is_valid, errors = DocumentValidator.validate_document_dict(doc_dict)
    assert is_valid is False
    assert any("mismatch" in e for e in errors)


def test_document_validation_empty_text():
    """Verify validation rejects documents with empty or whitespace-only text."""
    doc_dict = {
        "document_id": str(uuid4()),
        "source_id": "who_don",
        "title": "Empty Doc",
        "text": "   ",
        "publication_timestamp": datetime.now(timezone.utc),
        "content_hash_sha256": DocumentValidator.calculate_sha256("   "),
    }
    is_valid, errors = DocumentValidator.validate_document_dict(doc_dict)
    assert is_valid is False
    assert any("non-empty" in e for e in errors)


def test_document_validator_assert_valid_raises():
    """Verify assert_valid raises MalformedInputError on invalid document."""
    with pytest.raises(MalformedInputError):
        DocumentValidator.assert_valid({"invalid": "data"})


# ------------------------------------------------------------------------------
# Exact Deduplication Tests
# ------------------------------------------------------------------------------

def test_exact_deduplication_lifecycle():
    """Verify deduplicator registers unique items and detects duplicates."""
    dedup = ExactDeduplicator()
    doc_id1 = uuid4()
    doc_id2 = uuid4()
    hash1 = DocumentValidator.calculate_sha256("Article 1 content")
    hash2 = DocumentValidator.calculate_sha256("Article 2 content")

    # First document should be unique
    assert dedup.is_duplicate(hash1) is False
    assert dedup.register(hash1, doc_id1) is True
    assert dedup.is_duplicate(hash1) is True
    assert dedup.get_canonical_doc_id(hash1) == doc_id1
    assert dedup.total_unique_documents == 1
    assert dedup.total_duplicates_detected == 0

    # Second unique document
    assert dedup.register(hash2, doc_id2) is True
    assert dedup.total_unique_documents == 2

    # Attempt to register duplicate of hash1
    doc_id3 = uuid4()
    assert dedup.register(hash1, doc_id3) is False
    assert dedup.total_unique_documents == 2
    assert dedup.total_duplicates_detected == 1
    # Canonical ID should still point to original doc_id1
    assert dedup.get_canonical_doc_id(hash1) == doc_id1


def test_hash_reproducibility():
    """Verify SHA-256 calculation is deterministic across multiple calls."""
    text = "Epidemiological bulletin for Tamil Nadu."
    h1 = DocumentValidator.calculate_sha256(text)
    h2 = DocumentValidator.calculate_sha256(text)
    assert h1 == h2
    assert len(h1) == 64

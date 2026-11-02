"""
Exact Duplicate Detection Foundation for EpiSense.
Enforces content hash deduplication to prevent redundant document ingestion
while maintaining an extension point for future near-duplicate MinHash clustering.
"""

from typing import Dict, List, Optional, Set
from uuid import UUID

from episense.exceptions import SchemaValidationError


class ExactDeduplicator:
    """
    In-memory and stateful registry for exact document duplicate detection.
    Guarantees that identical raw content is never re-ingested as a novel document ID.
    """

    def __init__(self) -> None:
        # Maps content_hash_sha256 -> document_id
        self._hash_to_doc_id: Dict[str, UUID] = {}
        self._duplicate_count: int = 0

    def is_duplicate(self, content_hash: str) -> bool:
        """Returns True if the content hash has already been registered."""
        return content_hash.lower() in self._hash_to_doc_id

    def get_canonical_doc_id(self, content_hash: str) -> Optional[UUID]:
        """Returns the document ID of the canonical first-seen document with this hash."""
        return self._hash_to_doc_id.get(content_hash.lower())

    def register(self, content_hash: str, document_id: UUID) -> bool:
        """
        Registers a document content hash.
        Returns:
            True if the document is unique and was successfully registered.
            False if the document is an exact duplicate (increments duplicate counter).
        """
        hash_norm = content_hash.lower()
        if len(hash_norm) != 64:
            raise SchemaValidationError(f"Invalid SHA-256 hash length: {len(hash_norm)}")

        if hash_norm in self._hash_to_doc_id:
            self._duplicate_count += 1
            return False

        self._hash_to_doc_id[hash_norm] = document_id
        return True

    @property
    def total_unique_documents(self) -> int:
        """Number of distinct unique documents registered."""
        return len(self._hash_to_doc_id)

    @property
    def total_duplicates_detected(self) -> int:
        """Total number of duplicate ingestion attempts blocked."""
        return self._duplicate_count

    def clear(self) -> None:
        """Resets the deduplication registry."""
        self._hash_to_doc_id.clear()
        self._duplicate_count = 0

    # --------------------------------------------------------------------------
    # EXTENSION POINT: MinHash / LSH Near-Duplicate Clustering
    # --------------------------------------------------------------------------
    # NOTE: Near-duplicate detection (e.g. MinHash LSH with 0.80 Jaccard threshold)
    # is scheduled for Phase 7 (Multi-Source Fusion). Exact SHA-256 deduplication
    # runs first at ingestion to suppress identical syndicated text.

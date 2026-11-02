"""
Deterministic Text Loader for EpiSense NLP Pipeline.
Preserves exact character offsets and verifies cryptographic content hashes.
"""

import hashlib
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

from episense.schemas.document import Document
from episense.exceptions import MalformedInputError, DataUnavailableError


class DocumentTextLoader:
    """
    Loads raw text deterministically for NLP processing without modifying
    or mutating source characters.
    """

    def __init__(self, raw_data_dir: Union[str, Path] = "data/raw"):
        self.raw_data_dir = Path(raw_data_dir)

    def load_text(self, document_or_id: Union[Document, UUID, str]) -> tuple[UUID, str, Optional[str]]:
        """
        Loads document_id, raw_text, and expected_hash.
        Raises IngestionError if text is missing, empty, or hash mismatches.
        """
        if isinstance(document_or_id, Document):
            doc_id = document_or_id.document_id
            text = document_or_id.text
            expected_hash = document_or_id.content_hash_sha256
        elif isinstance(document_or_id, (UUID, str)):
            doc_id = UUID(str(document_or_id))
            file_path = self.raw_data_dir / f"{doc_id}.txt"
            if not file_path.exists():
                raise DataUnavailableError(f"Raw document file not found: {file_path}")
            text = file_path.read_text(encoding="utf-8")
            expected_hash = None
        else:
            raise ValueError(f"Unsupported document identifier type: {type(document_or_id)}")

        if not text or not text.strip():
            raise MalformedInputError(f"Document {doc_id} text is empty or whitespace-only.")

        if expected_hash is not None:
            actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if actual_hash != expected_hash:
                raise MalformedInputError(
                    f"Content hash mismatch for document {doc_id}: expected {expected_hash}, got {actual_hash}"
                )

        return doc_id, text, expected_hash

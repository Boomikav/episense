"""
Data Validation Utilities for EpiSense Document Ingestion.
Enforces structural, cryptographic, temporal, and textual integrity
without silently discarding invalid records.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from uuid import UUID

from episense.exceptions import MalformedInputError, SchemaValidationError


class DocumentValidator:
    """Validates raw and benchmark document dictionaries prior to ingestion or persistence."""

    REQUIRED_FIELDS = {
        "document_id",
        "source_id",
        "title",
        "text",
        "publication_timestamp",
        "content_hash_sha256",
    }

    @staticmethod
    def calculate_sha256(text: str) -> str:
        """Calculates deterministic SHA-256 hash over utf-8 encoded text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @classmethod
    def validate_document_dict(cls, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates document dictionary against ingestion criteria.
        Returns (is_valid, list_of_error_messages).
        """
        errors: List[str] = []

        # 1. Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: '{field}'")

        if errors:
            return False, errors

        # 2. Validate Document ID
        doc_id = data.get("document_id")
        if isinstance(doc_id, str):
            try:
                UUID(doc_id)
            except ValueError:
                errors.append(f"document_id '{doc_id}' is not a valid UUID string")
        elif not isinstance(doc_id, UUID):
            errors.append(f"document_id must be a UUID object or valid UUID string, got {type(doc_id)}")

        # 3. Validate Text non-emptiness
        text = data.get("text", "")
        if not isinstance(text, str) or len(text.strip()) == 0:
            errors.append("Document 'text' must be a non-empty string")

        # 4. Validate Title non-emptiness
        title = data.get("title", "")
        if not isinstance(title, str) or len(title.strip()) == 0:
            errors.append("Document 'title' must be a non-empty string")

        # 5. Validate Timestamps
        pub_time = data.get("publication_timestamp")
        if not isinstance(pub_time, datetime):
            errors.append(f"publication_timestamp must be a datetime object, got {type(pub_time)}")
        else:
            if pub_time.tzinfo is None:
                errors.append("publication_timestamp must be timezone-aware (UTC)")

        ing_time = data.get("ingestion_timestamp")
        if ing_time is not None:
            if not isinstance(ing_time, datetime):
                errors.append(f"ingestion_timestamp must be a datetime object, got {type(ing_time)}")
            elif isinstance(pub_time, datetime) and ing_time < pub_time:
                errors.append(f"ingestion_timestamp ({ing_time}) cannot be earlier than publication_timestamp ({pub_time})")

        # 6. Validate Content Hash
        content_hash = data.get("content_hash_sha256", "")
        if not isinstance(content_hash, str) or len(content_hash) != 64:
            errors.append("content_hash_sha256 must be a 64-character hexadecimal SHA-256 string")
        elif isinstance(text, str) and len(text.strip()) > 0:
            expected_hash = cls.calculate_sha256(text)
            if content_hash.lower() != expected_hash.lower():
                errors.append(
                    f"content_hash_sha256 mismatch: declared '{content_hash}', computed '{expected_hash}'"
                )

        return len(errors) == 0, errors

    @classmethod
    def assert_valid(cls, data: Dict[str, Any]) -> None:
        """Raises MalformedInputError if document validation fails."""
        is_valid, errors = cls.validate_document_dict(data)
        if not is_valid:
            raise MalformedInputError(
                message=f"Document validation failed with {len(errors)} error(s)",
                details={"errors": errors, "document_id": str(data.get("document_id"))},
            )

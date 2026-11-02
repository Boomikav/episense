"""
Source-Agnostic Streaming Ingestion Abstraction for EpiSense (Phase 11).
Supports streaming single documents, batches, file manifests, and test fixtures
with strict validation, provenance preservation, and error isolation.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.streaming import DeadLetterRecord, IngestionStatus
from episense.acquisition.validation import DocumentValidator
from episense.exceptions import MalformedInputError, SchemaValidationError
from episense.logging import get_logger

logger = get_logger("streaming.ingestion")


class IngestionSource(ABC):
    """
    Abstract base class for all streaming surveillance document sources.
    Decouples ingestion from specific transport mechanisms (files, mock feeds, queues).
    """

    @abstractmethod
    def __iter__(self) -> Iterator[Document]:
        """Yields documents sequentially as they arrive."""
        pass

    @abstractmethod
    def has_next(self) -> bool:
        """Returns True if further documents are available in the stream."""
        pass

    @abstractmethod
    def get_next(self) -> Optional[Document]:
        """Fetches the next document from the stream, or None if exhausted."""
        pass


class MockIngestionSource(IngestionSource):
    """
    In-memory deterministic document stream for unit testing and benchmarking.
    """

    def __init__(self, documents: List[Document]):
        self._documents = list(documents)
        self._cursor = 0

    def __iter__(self) -> Iterator[Document]:
        while self.has_next():
            doc = self.get_next()
            if doc:
                yield doc

    def has_next(self) -> bool:
        return self._cursor < len(self._documents)

    def get_next(self) -> Optional[Document]:
        if not self.has_next():
            return None
        doc = self._documents[self._cursor]
        self._cursor += 1
        return doc

    def reset(self):
        """Resets the stream cursor to the beginning."""
        self._cursor = 0


class SingleDocumentIngestionSource(IngestionSource):
    """
    Ingestion source delivering a single discrete document.
    """

    def __init__(self, document: Document):
        self._document: Optional[Document] = document
        self._delivered = False

    def __iter__(self) -> Iterator[Document]:
        doc = self.get_next()
        if doc:
            yield doc

    def has_next(self) -> bool:
        return not self._delivered and self._document is not None

    def get_next(self) -> Optional[Document]:
        if not self.has_next():
            return None
        self._delivered = True
        return self._document


class FileStreamIngestionSource(IngestionSource):
    """
    File-backed ingestion source that reads document manifests or JSON files deterministically.
    """

    def __init__(self, paths: List[Union[str, Path]]):
        self._paths = [Path(p) for p in paths]
        self._documents: List[Document] = []
        self._cursor = 0
        self._load_documents()

    def _load_documents(self):
        validator = StreamingDocumentValidator()
        for p in self._paths:
            if not p.exists():
                logger.warning(f"Manifest file not found: {p}")
                continue

            try:
                content = p.read_text(encoding="utf-8")
                data = json.loads(content)
            except Exception as e:
                logger.error(f"Failed to read manifest JSON from {p}: {e}")
                continue

            raw_docs = data.get("documents", []) if isinstance(data, dict) else data
            if not isinstance(raw_docs, list):
                raw_docs = [data]

            for item in raw_docs:
                doc_payload = item.get("document", item) if isinstance(item, dict) else item
                is_valid, _, doc = validator.validate(doc_payload)
                if is_valid and doc:
                    self._documents.append(doc)

    def __iter__(self) -> Iterator[Document]:
        while self.has_next():
            doc = self.get_next()
            if doc:
                yield doc

    def has_next(self) -> bool:
        return self._cursor < len(self._documents)

    def get_next(self) -> Optional[Document]:
        if not self.has_next():
            return None
        doc = self._documents[self._cursor]
        self._cursor += 1
        return doc


class DocumentBatchIngestionSource(IngestionSource):
    """
    Ingests an arbitrary batch of document objects or dictionaries.
    """

    def __init__(self, items: List[Union[Document, Dict[str, Any]]]):
        self._items = list(items)
        self._cursor = 0
        self._validator = StreamingDocumentValidator()

    def __iter__(self) -> Iterator[Document]:
        while self.has_next():
            doc = self.get_next()
            if doc:
                yield doc

    def has_next(self) -> bool:
        return self._cursor < len(self._items)

    def get_next(self) -> Optional[Document]:
        while self._cursor < len(self._items):
            item = self._items[self._cursor]
            self._cursor += 1
            is_valid, _, doc = self._validator.validate(item)
            if is_valid and doc:
                return doc
        return None


class StreamingDocumentValidator:
    """
    Validates streaming document records, ensuring cryptographic integrity,
    structural completeness, and non-empty clinical text.
    Isolates invalid payloads into DeadLetterRecords rather than raising unhandled exceptions.
    """

    @staticmethod
    def calculate_sha256(text: str) -> str:
        """Calculates deterministic SHA-256 over utf-8 text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def validate(
        self, payload: Union[Document, Dict[str, Any]]
    ) -> Tuple[bool, Optional[DeadLetterRecord], Optional[Document]]:
        """
        Validates an incoming payload.
        Returns:
            (is_valid: bool, dead_letter_record: Optional[DeadLetterRecord], document: Optional[Document])
        """
        if isinstance(payload, Document):
            # Check unreasonable future date (> 48 hours from current UTC)
            if payload.publication_timestamp is not None:
                max_permitted_future = datetime.now(timezone.utc) + timedelta(days=2)
                pub_time = payload.publication_timestamp
                if pub_time.tzinfo is None:
                    pub_time = pub_time.replace(tzinfo=timezone.utc)
                if pub_time > max_permitted_future:
                    if payload.origin not in (OriginClassification.BENCHMARK, OriginClassification.HISTORICAL_CORPUS, OriginClassification.SYNTHETIC_TEST):
                        dl = DeadLetterRecord(
                            document_id=payload.document_id,
                            source_id=payload.source_id,
                            stage="ingestion_validation",
                            error_type="UnreasonableFutureDateError",
                            error_message=f"Publication timestamp {pub_time.isoformat()} is unreasonably in the future (> {max_permitted_future.isoformat()})",
                            raw_payload_preview=payload.text[:200],
                        )
                        return False, dl, None

            # Verify cryptographic integrity of existing Document model
            computed_hash = self.calculate_sha256(payload.text)
            if payload.content_hash_sha256.lower() != computed_hash.lower():
                dl = DeadLetterRecord(
                    document_id=payload.document_id,
                    source_id=payload.source_id,
                    stage="ingestion_validation",
                    error_type="ContentHashMismatchError",
                    error_message=f"Declared hash {payload.content_hash_sha256} != computed {computed_hash}",
                    raw_payload_preview=payload.text[:200],
                )
                return False, dl, None
            return True, None, payload

        if not isinstance(payload, dict):
            dl = DeadLetterRecord(
                stage="ingestion_validation",
                error_type="InvalidPayloadTypeError",
                error_message=f"Expected Document or dict, got {type(payload).__name__}",
                raw_payload_preview=str(payload)[:200],
            )
            return False, dl, None

        # Check required fields (title and text are strictly required)
        required = ["title", "text"]
        for field in required:
            if field not in payload or payload[field] is None:
                dl = DeadLetterRecord(
                    stage="ingestion_validation",
                    error_type="MissingRequiredFieldError",
                    error_message=f"Missing required field: '{field}'",
                    raw_payload_preview=str(payload)[:200],
                )
                return False, dl, None

        # Check non-empty strings
        text = str(payload.get("text", "")).strip()
        title = str(payload.get("title", "")).strip()
        if not text:
            dl = DeadLetterRecord(
                stage="ingestion_validation",
                error_type="EmptyTextError",
                error_message="Document text must be non-empty",
                raw_payload_preview=str(payload)[:200],
            )
            return False, dl, None

        if not title:
            dl = DeadLetterRecord(
                stage="ingestion_validation",
                error_type="EmptyTitleError",
                error_message="Document title must be non-empty",
                raw_payload_preview=str(payload)[:200],
            )
            return False, dl, None

        # Validate publication timestamp (optional, but if present must be valid and not in unreasonable future)
        pub_raw = payload.get("publication_timestamp")
        pub_time: Optional[datetime] = None
        if pub_raw is not None and str(pub_raw).strip() != "":
            if isinstance(pub_raw, datetime):
                pub_time = pub_raw if pub_raw.tzinfo else pub_raw.replace(tzinfo=timezone.utc)
            elif isinstance(pub_raw, str):
                try:
                    pub_time = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                    if pub_time.tzinfo is None:
                        pub_time = pub_time.replace(tzinfo=timezone.utc)
                except Exception as e:
                    dl = DeadLetterRecord(
                        stage="ingestion_validation",
                        error_type="InvalidTimestampError",
                        error_message=f"Malformed publication_timestamp: {e}",
                        raw_payload_preview=str(payload)[:200],
                    )
                    return False, dl, None
            else:
                dl = DeadLetterRecord(
                    stage="ingestion_validation",
                    error_type="InvalidTimestampError",
                    error_message=f"Unsupported publication_timestamp type: {type(pub_raw).__name__}",
                    raw_payload_preview=str(payload)[:200],
                )
                return False, dl, None

            # Quarantine unreasonable future dates (> 48 hours from current UTC)
            max_permitted_future = datetime.now(timezone.utc) + timedelta(days=2)
            if pub_time > max_permitted_future:
                origin_val = str(payload.get("origin", "")).upper()
                if origin_val not in ("BENCHMARK", "HISTORICAL_CORPUS", "SYNTHETIC_TEST"):
                    dl = DeadLetterRecord(
                        stage="ingestion_validation",
                        error_type="UnreasonableFutureDateError",
                        error_message=f"Publication timestamp {pub_time.isoformat()} is unreasonably in the future (> {max_permitted_future.isoformat()})",
                        raw_payload_preview=str(payload)[:200],
                    )
                    return False, dl, None

        # Validate or calculate SHA-256 hash
        computed_hash = self.calculate_sha256(text)
        declared_hash = payload.get("content_hash_sha256")
        if declared_hash:
            if str(declared_hash).lower() != computed_hash.lower():
                dl = DeadLetterRecord(
                    stage="ingestion_validation",
                    error_type="ContentHashMismatchError",
                    error_message=f"Declared hash {declared_hash} != computed {computed_hash}",
                    raw_payload_preview=text[:200],
                )
                return False, dl, None
        else:
            declared_hash = computed_hash

        # Parse document_id
        doc_id_raw = payload.get("document_id")
        doc_id: UUID
        if isinstance(doc_id_raw, UUID):
            doc_id = doc_id_raw
        elif isinstance(doc_id_raw, str) and doc_id_raw:
            try:
                doc_id = UUID(doc_id_raw)
            except ValueError as e:
                dl = DeadLetterRecord(
                    stage="ingestion_validation",
                    error_type="InvalidUUIDError",
                    error_message=f"Malformed document_id UUID string: {e}",
                    raw_payload_preview=str(payload)[:200],
                )
                return False, dl, None
        else:
            doc_id = uuid4()

        # Parse SourceType
        source_type_raw = payload.get("source_type", SourceType.BENCHMARK_CORPUS)
        source_type = SourceType(source_type_raw) if source_type_raw in SourceType._value2member_map_ else SourceType.BENCHMARK_CORPUS

        # Parse OriginClassification
        origin_raw = payload.get("origin")
        origin = OriginClassification.HISTORICAL_CORPUS
        if origin_raw:
            if isinstance(origin_raw, OriginClassification):
                origin = origin_raw
            elif str(origin_raw) in OriginClassification._value2member_map_:
                origin = OriginClassification(str(origin_raw))
            elif str(origin_raw).upper() in OriginClassification.__members__:
                origin = OriginClassification[str(origin_raw).upper()]

        try:
            doc = Document(
                document_id=doc_id,
                source_id=str(payload.get("source_id", "streaming_source")),
                source_type=source_type,
                origin=origin,
                title=title,
                text=text,
                publication_timestamp=pub_time,
                content_hash_sha256=declared_hash,
                source_url=payload.get("source_url"),
                language=str(payload.get("language", "en")),
                provenance_metadata=payload.get("provenance_metadata", {}),
            )
            return True, None, doc
        except Exception as e:
            dl = DeadLetterRecord(
                stage="ingestion_validation",
                error_type="SchemaInstantiationError",
                error_message=str(e),
                raw_payload_preview=text[:200],
            )
            return False, dl, None

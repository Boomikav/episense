"""
Benchmark dataset and annotation schemas for EpiSense.
Preserves character-level ground-truth offsets compatible with Phase 2 domain models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import Field, model_validator

from episense.schemas.base import EpiSenseBaseModel, utc_now
from episense.schemas.document import Document, SourceType


class DatasetSplit(str, Enum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"
    BENCHMARK = "benchmark"


class AnnotationLayer(str, Enum):
    ENTITY = "entity"
    ASSERTION = "assertion"
    TEMPORAL = "temporal"
    GEOGRAPHIC = "geographic"
    EVENT = "event"


class AnnotationSpan(EpiSenseBaseModel):
    """
    Ground-truth character-level annotation span in a benchmark document.
    """
    annotation_id: UUID = Field(default_factory=uuid4)
    layer: AnnotationLayer
    label: str = Field(min_length=1, description="e.g. DISEASE, CONFIRMED, GPE, DATE")
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    span_text: str = Field(min_length=1)
    normalized_value: Optional[str] = Field(default=None, description="ICD-10, GeoNames ID, ISO date")
    attributes: Dict[str, str] = Field(default_factory=dict)
    annotator_id: str = Field(default="human_expert")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_offsets(self) -> "AnnotationSpan":
        if self.end_char <= self.start_char:
            raise ValueError(
                f"end_char ({self.end_char}) must be strictly greater than start_char ({self.start_char})"
            )
        return self


class BenchmarkDocument(EpiSenseBaseModel):
    """
    A curated real-world public health document within the benchmark corpus.
    """
    document: Document
    split: DatasetSplit = DatasetSplit.BENCHMARK
    annotations: List[AnnotationSpan] = Field(default_factory=list)
    license_or_usage_note: str = Field(min_length=1)
    curation_notes: Optional[str] = None
    curator_id: str = Field(default="episense_curator")
    verified: bool = Field(default=True)


class BenchmarkManifest(EpiSenseBaseModel):
    """
    Reproducible manifest cataloging all documents in a benchmark release.
    """
    manifest_id: UUID = Field(default_factory=uuid4)
    dataset_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    description: str
    geographic_scope: str
    temporal_range_start: Optional[datetime] = None
    temporal_range_end: Optional[datetime] = None
    document_count: int = Field(ge=0)
    split_counts: Dict[str, int] = Field(default_factory=dict)
    sources_included: List[str] = Field(default_factory=list)
    documents: List[BenchmarkDocument] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts_and_uniqueness(self) -> "BenchmarkManifest":
        if self.document_count != len(self.documents):
            raise ValueError(
                f"document_count ({self.document_count}) does not match len(documents) ({len(self.documents)})"
            )

        # Ensure no duplicate document IDs or content hashes
        seen_ids = set()
        seen_hashes = set()
        for bdoc in self.documents:
            doc_id = bdoc.document.document_id
            doc_hash = bdoc.document.content_hash_sha256
            if doc_id in seen_ids:
                raise ValueError(f"Duplicate document_id in manifest: {doc_id}")
            if doc_hash in seen_hashes:
                raise ValueError(f"Duplicate content_hash_sha256 in manifest: {doc_hash}")
            seen_ids.add(doc_id)
            seen_hashes.add(doc_hash)

        return self

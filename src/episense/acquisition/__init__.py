"""EpiSense Data Acquisition Package."""
from episense.acquisition.source_registry import AccessMethod, SourceMetadata, SourceRegistry, SourceStatus
from episense.acquisition.validation import DocumentValidator
from episense.acquisition.deduplication import ExactDeduplicator

from episense.acquisition.normalization import TextNormalizer
from episense.acquisition.incident_grouping import Incident, IncidentGrouper

__all__ = [
    "AccessMethod",
    "SourceMetadata",
    "SourceRegistry",
    "SourceStatus",
    "DocumentValidator",
    "ExactDeduplicator",
    "TextNormalizer",
    "Incident",
    "IncidentGrouper",
]

"""
EpiSense Fusion Component.
Deterministic cross-source event clustering, corroboration, and canonical FusedEvent synthesis.
"""

from episense.fusion.disease_linker import DiseaseLinker
from episense.fusion.geo_linker import GeographicLinker
from episense.fusion.temporal_linker import TemporalLinker
from episense.fusion.source_independence import SourceIndependenceTracker
from episense.fusion.quantities import QuantityAggregator
from episense.fusion.matcher import EventMatcher
from episense.fusion.engine import EventFusionEngine

__all__ = [
    "DiseaseLinker",
    "GeographicLinker",
    "TemporalLinker",
    "SourceIndependenceTracker",
    "QuantityAggregator",
    "EventMatcher",
    "EventFusionEngine",
]

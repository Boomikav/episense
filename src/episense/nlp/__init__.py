"""
EpiSense Context-Aware NLP Extraction Engine.
Provides deterministic, explainable extraction of health entities, assertions,
temporals, locations, case counts, and sentence context associations with strict provenance.
"""

from episense.nlp.pipeline import NLPPipeline
from episense.nlp.batch import BatchRunner
from episense.nlp.loader import DocumentTextLoader
from episense.nlp.segmentation import SentenceSegmenter
from episense.nlp.models import ModelManager
from episense.nlp.entities.extractor import HybridHealthEntityExtractor
from episense.nlp.assertion.analyzer import ContextualAssertionAnalyzer
from episense.nlp.temporal.extractor import RuleBasedTemporalExtractor
from episense.nlp.geospatial.resolver import CautiousLocationResolver
from episense.nlp.quantities import QuantityExtractor
from episense.nlp.context import ContextAssociator
from episense.nlp.provenance import ProvenanceValidator
from episense.nlp.evaluation import GoldEvaluator

__all__ = [
    "NLPPipeline",
    "BatchRunner",
    "DocumentTextLoader",
    "SentenceSegmenter",
    "ModelManager",
    "HybridHealthEntityExtractor",
    "ContextualAssertionAnalyzer",
    "RuleBasedTemporalExtractor",
    "CautiousLocationResolver",
    "QuantityExtractor",
    "ContextAssociator",
    "ProvenanceValidator",
    "GoldEvaluator",
]

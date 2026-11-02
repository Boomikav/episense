"""
Pipeline Coordinator for EpiSense Context-Aware NLP Extraction Engine.
Coordinates text loading, segmentation, NER, assertion, temporal, geospatial,
quantity, context association, and provenance validation.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Union
from uuid import UUID

from episense.schemas.document import Document
from episense.schemas.nlp import NLPOutput
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


class NLPPipeline:
    """
    Orchestrates the deterministic, explainable NLP extraction pipeline for EpiSense.
    """

    PIPELINE_VERSION = "2.4.0"

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = "data/interim/nlp_cache",
        enable_cache: bool = True,
    ):
        self.loader = DocumentTextLoader()
        self.segmenter = SentenceSegmenter()
        self.web_nlp = ModelManager.get_web_model()
        self.sci_nlp = ModelManager.get_sci_model()

        self.entity_extractor = HybridHealthEntityExtractor(sci_nlp=self.sci_nlp, web_nlp=self.web_nlp)
        self.assertion_analyzer = ContextualAssertionAnalyzer(nlp=self.web_nlp)
        self.temporal_extractor = RuleBasedTemporalExtractor(web_nlp=self.web_nlp)
        self.location_resolver = CautiousLocationResolver(nlp=self.web_nlp)
        self.quantity_extractor = QuantityExtractor(nlp=self.web_nlp)
        self.context_associator = ContextAssociator()

        self.enable_cache = enable_cache
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.enable_cache and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def process_document(self, document_or_id: Union[Document, UUID, str]) -> NLPOutput:
        """
        Executes the full NLP extraction pipeline on an ingested document.
        """
        # 1. Load raw text
        doc_id, raw_text, content_hash = self.loader.load_text(document_or_id)

        # 2. Check deterministic cache
        cache_key = None
        if self.enable_cache and self.cache_dir:
            cache_key = hashlib.sha256(
                f"{raw_text}:{self.PIPELINE_VERSION}".encode("utf-8")
            ).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    return NLPOutput.model_validate_json(cache_file.read_text(encoding="utf-8"))
                except Exception:
                    pass  # Fall back to re-processing if corrupted cache

        source_id = "unknown"
        pub_time = None
        if isinstance(document_or_id, Document):
            source_id = document_or_id.source_id
            pub_time = document_or_id.publication_timestamp

        # Reference time for temporal extraction: fallback to doc publication timestamp or UTC now
        ref_time = pub_time or Document.model_fields["ingestion_timestamp"].default_factory()

        # 3. Sentence segmentation and tokenization
        web_doc = self.web_nlp(raw_text)
        sentences = self.segmenter.segment(raw_text, web_doc)

        # 4. Health entity extraction
        entities = self.entity_extractor.extract(raw_text, doc_id)

        # 5. Assertion and negation analysis
        assertions = self.assertion_analyzer.analyze(raw_text, entities)

        # 6. Temporal extraction (preserving pub vs event time)
        temporals = self.temporal_extractor.extract(raw_text, ref_time)

        # 7. Geographic mention resolution
        locations = self.location_resolver.resolve_mentions(raw_text)

        # 8. Quantity extraction
        quantities = self.quantity_extractor.extract(raw_text)

        # 9. Context association
        associations = self.context_associator.associate(
            sentences=sentences,
            entities=entities,
            assertions=assertions,
            temporals=temporals,
            locations=locations,
            quantities=quantities,
        )

        # 10. Provenance validation
        provenance_records = ProvenanceValidator.generate_records(
            document_id=doc_id,
            source_id=source_id,
            raw_text=raw_text,
            entities=entities,
            temporals=temporals,
            locations=locations,
            quantities=quantities,
        )

        pipeline_metadata = {
            "pipeline_version": self.PIPELINE_VERSION,
            "web_model": "en_core_web_sm-3.8.0",
            "sci_model": "en_core_sci_sm-0.5.4",
            "raw_text_length": len(raw_text),
            "sentence_count": len(sentences),
            "entity_count": len(entities),
            "temporal_count": len(temporals),
            "location_count": len(locations),
            "quantity_count": len(quantities),
        }

        output = NLPOutput(
            document_id=doc_id,
            sentences=sentences,
            entities=entities,
            assertions=assertions,
            temporal_expressions=temporals,
            locations=locations,
            quantities=quantities,
            context_associations=associations,
            provenance_records=provenance_records,
            pipeline_metadata=pipeline_metadata,
        )

        # Write to cache
        if self.enable_cache and self.cache_dir and cache_key:
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_file.write_text(output.model_dump_json(indent=2), encoding="utf-8")

        return output

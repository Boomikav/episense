import sys
sys.path.insert(0, "src")
import sqlite3
import json
from uuid import UUID
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import Document

db = SurveillanceDatabase("data/surveillance_store.sqlite")
doc_id = UUID("da07f5a7-333e-5c57-9efb-b1cc8d450240")
doc = db.get_document(doc_id)
print("=== TRACE FOR LIVE DOCUMENT ===")
print(f"1. External Retrieval: Source: {doc.source_id}, URL: {doc.source_url}")
print(f"2. Time Semantics: Published at {doc.publication_timestamp}, Ingested at {doc.ingestion_timestamp}")
print(f"3. Provenance: Origin = {doc.origin.value}")
print(f"4. Persistent Storage: Doc ID = {doc.document_id}, Content Hash = {doc.content_hash_sha256}")

# Run NLP processing explicitly to inspect exact spans and stages
pipeline = ContinuousSurveillancePipeline()
update = pipeline.process_document(doc)
print(f"\n5. NLP Pipeline Processing Status: {update.status.value}")
trace = pipeline.state.traces.get(doc.document_id)
print(f"   Trace exists: {trace is not None}")
if trace:
    print(f"   Trace ID: {trace.trace_id}, Document: {trace.document_id}")
    for stage in trace.stages:
        print(f"     Stage {stage.stage_number:02d} ({stage.stage_name}): {stage.status.value} ({stage.duration_ms:.1f}ms) -> {stage.output_summary}")
    if trace.nlp_output:
        nlp = trace.nlp_output
        print(f"\n   Extracted Entities ({len(nlp.entities)}):")
        for ent in nlp.entities[:8]:
            print(f"     - '{ent.text_span}' [{ent.start_char}:{ent.end_char}] type={ent.entity_type} norm={ent.normalized_value} conf={ent.extraction_confidence:.2f}")

print(f"\n6. Canonical Event Creation / Clustering:")
print(f"   Fused events affected: {update.fused_events_affected}")
print(f"   Alerts generated: {update.alerts_generated}")
for fe_id in update.fused_events_affected:
    fe = pipeline.state.fused_events.get(fe_id)
    if fe:
        print(f"   Fused Event ID: {fe.fused_event_id}")
        print(f"     Canonical Disease: {fe.canonical_disease}")
        print(f"     Assertion / Certainty: {fe.assertion_status.value} / {fe.certainty.value}")
        print(f"     Quantities: {fe.aggregated_quantities}")
        print(f"     Independent Sources: {[s.source_id for s in fe.independent_sources]}")
        print(f"     Quantities: {fe.aggregated_quantities}")
        print(f"     Independent Sources: {[s.source_id for s in fe.independent_sources]}")


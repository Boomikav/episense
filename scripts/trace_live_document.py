import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get the most recently ingested document
cur.execute("SELECT * FROM documents WHERE origin='LIVE_EXTERNAL' ORDER BY ingestion_timestamp DESC LIMIT 5")
docs = cur.fetchall()
print(f"Total live external docs recently ingested: {len(docs)}")
for i, d in enumerate(docs):
    print(f"\n--- Document #{i+1} ---")
    print(f"  ID: {d['document_id']}")
    print(f"  Title: {d['title']}")
    print(f"  Source ID: {d['source_id']}")
    print(f"  Origin: {d['origin']}")
    print(f"  Published at: {d['publication_timestamp']}")
    print(f"  Ingested at: {d['ingestion_timestamp']}")
    print(f"  Content Hash SHA-256: {d['content_hash_sha256']}")
    print(f"  URL: {d['source_url']}")
    print(f"  Text preview (first 200 chars): {d['text'][:200]}...")

# Pick the first one and inspect its NLP traces, entities, fused events
doc_0 = docs[0]
doc_id = doc_0['document_id']

# Check NLP forensic traces in database if stored
cur.execute("SELECT * FROM document_nlp_extractions WHERE document_id = ?", (doc_id,))
nlp_rows = cur.fetchall()
print(f"\nNLP Extractions found for {doc_id}: {len(nlp_rows)}")
for r in nlp_rows:
    print(f"  Extraction: {dict(r)}")

# Check canonical fused events contributing this document
cur.execute("SELECT * FROM fused_events WHERE contributing_doc_ids LIKE ? OR contributing_doc_ids LIKE ?", (f"%{doc_id}%", f"%{str(doc_id)}%"))
fe_rows = cur.fetchall()
print(f"\nCanonical Fused Events linked to {doc_id}: {len(fe_rows)}")
for r in fe_rows:
    print(f"  Fused Event ID: {r['fused_event_id']}")
    print(f"  Canonical Disease: {r['canonical_disease']}")
    print(f"  Location: {r['canonical_location']}")
    print(f"  Window: {r['event_window_start']} -> {r['event_window_end']}")
    print(f"  Independent Sources Count: {r['independent_source_count']}")

conn.close()

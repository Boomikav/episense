import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get the most recently ingested document
cur.execute("SELECT * FROM documents WHERE origin='LIVE_EXTERNAL' ORDER BY created_at DESC LIMIT 5")
docs = cur.fetchall()
print(f"Total live external docs recently ingested: {len(docs)}")
for i, d in enumerate(docs):
    print(f"\n--- Document #{i+1} ---")
    print(f"  Document ID: {d['document_id']}")
    print(f"  Title: {d['title']}")
    print(f"  Source ID: {d['source_id']}")
    print(f"  Origin: {d['origin']}")
    print(f"  Published at: {d['publication_timestamp']}")
    print(f"  Retrieved at: {d['retrieval_timestamp']}")
    print(f"  Created at (DB): {d['created_at']}")
    print(f"  Content Hash SHA-256: {d['content_hash_sha256']}")
    print(f"  URL: {d['source_url']}")
    print(f"  Text preview: {d['text'][:180]}...")

# Inspect pipeline traces for the most recent document
doc_0 = docs[0]
doc_id = doc_0['document_id']

cur.execute("SELECT * FROM pipeline_traces WHERE document_id = ?", (doc_id,))
traces = cur.fetchall()
print(f"\n=== PIPELINE TRACES FOR DOCUMENT {doc_id} ===")
print(f"Total trace rows: {len(traces)}")
for t in traces:
    print(f"  Trace ID: {t['trace_id']}")
    data = json.loads(t['trace_data']) if 'trace_data' in t.keys() else {}
    print(f"  Stages recorded: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    if isinstance(data, dict):
        stages = data.get("stages", [])
        for s in stages:
            print(f"    - Stage {s.get('stage_number')}: {s.get('stage_name')} | output count: {len(s.get('output', [])) if isinstance(s.get('output'), list) else 'non-list'}")

# Check fused events
cur.execute("SELECT * FROM fused_events ORDER BY created_at DESC LIMIT 5")
events = cur.fetchall()
print(f"\n=== MOST RECENT FUSED EVENTS ===")
for e in events:
    print(f"  Fused Event ID: {e['fused_event_id']}")
    data = json.loads(e['json_data']) if 'json_data' in e.keys() else {}
    print(f"  Disease: {data.get('canonical_disease')} | Location: {data.get('canonical_location')} | Window: {data.get('event_window_start')} -> {data.get('event_window_end')}")
    print(f"  Contributing Obs: {data.get('contributing_observation_ids')} | Sources: {data.get('independent_sources')}")

conn.close()

import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
print("--- Origin breakdown in pipeline_traces ---")
for r in con.execute("SELECT origin, COUNT(*) FROM pipeline_traces GROUP BY origin").fetchall():
    print(r)

print("\n--- Origin breakdown in alerts ---")
for r in con.execute("SELECT origin, COUNT(*) FROM alerts GROUP BY origin").fetchall():
    print(r)

print("\n--- Documents with SYNTHETIC_TEST ---")
for r in con.execute("SELECT document_id, title, source_id FROM documents WHERE origin='SYNTHETIC_TEST'").fetchall():
    print(r)

print("\n--- Any fused events linked to SYNTHETIC_TEST documents? ---")
synth_ids = set(r[0] for r in con.execute("SELECT document_id FROM documents WHERE origin='SYNTHETIC_TEST'").fetchall())
count_synth_fused = 0
for r in con.execute("SELECT fused_event_id, json_data FROM fused_events").fetchall():
    data = json.loads(r[1])
    obs = data.get("contributing_observation_ids", [])
    ev_refs = [e.get("document_id") for e in data.get("evidence_references", [])]
    if any(i in synth_ids for i in obs) or any(i in synth_ids for i in ev_refs):
        count_synth_fused += 1
print(f"Fused events linked to synth docs: {count_synth_fused}")

import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
cur.execute("SELECT fused_event_id, canonical_disease, disease_key, primary_origin, earliest_time, latest_time, total_cases, supporting_observation_count, json_data FROM fused_events WHERE primary_origin='LIVE_EXTERNAL' LIMIT 10")
rows = cur.fetchall()
print(f"Total live external fused events found: {len(rows)}")
for r in rows:
    data = json.loads(r[8])
    print(f"ID: {r[0]} | Disease: {r[1]} ({r[2]}) | Window: {r[4]} -> {r[5]} | Cases: {r[6]} | Contributing Obs: {data.get('contributing_observation_ids')} | Contributing Docs: {data.get('contributing_document_ids', data.get('source_document_ids'))}")

conn.close()

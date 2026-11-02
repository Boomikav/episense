import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
c = conn.cursor()

print("=== DOCUMENTS BY SOURCE / ORIGIN ===")
for r in c.execute("SELECT source_id, origin, count(*) FROM documents GROUP BY source_id, origin"):
    print(f"source_id: {r[0]} | origin: {r[1]} | count: {r[2]}")

print("\n=== FUSED EVENTS BY ORIGIN / STATUS ===")
for r in c.execute("SELECT primary_origin, status, count(*) FROM fused_events GROUP BY primary_origin, status"):
    print(f"origin: {r[0]} | status: {r[1]} | count: {r[2]}")

# Let's inspect live external fused events
rows = c.execute("SELECT fused_event_id, canonical_disease, supporting_observation_count, linkage_classification, json_data FROM fused_events WHERE primary_origin = 'LIVE_EXTERNAL'").fetchall()
print(f"\nTotal LIVE_EXTERNAL fused events: {len(rows)}")

counts_by_linkage = {}
counts_by_obs_cnt = {}
for r in rows:
    lk = r[3]
    obs_cnt = r[2]
    counts_by_linkage[lk] = counts_by_linkage.get(lk, 0) + 1
    counts_by_obs_cnt[obs_cnt] = counts_by_obs_cnt.get(obs_cnt, 0) + 1

print(f"By linkage_classification: {counts_by_linkage}")
print(f"By supporting_observation_count: {counts_by_obs_cnt}")

conn.close()

import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
sig_ids = [
    "324d9238-c2cd-54d0-9059-83a35e273e76",
    "00234528-9eff-5999-84c6-09761e0f538e",
    "45e04b36-685f-549a-aa21-833eee2f0b78",
    "7a68b4d9-4a0b-51b4-9b38-20301f2cb4c8",
    "0b6171dc-6a8e-5efc-986f-0f9a8a996137",
    "ced3fef2-6b07-550c-b484-6e1aad6df445"
]
placeholders = ','.join(['?'] * len(sig_ids))
cur.execute("SELECT alert_id, disease_key, geo_key, alert_tier, json_data FROM alerts")
rows = cur.fetchall()
gated_count = 0
ungated_count = 0
for r in rows:
    data = json.loads(r[4])
    is_g = data.get("is_gated", False)
    reason = data.get("gating_reason")
    if is_g:
        gated_count += 1
    else:
        ungated_count += 1

print(f"Total alerts: {len(rows)}")
print(f"  Gated alerts: {gated_count}")
print(f"  Ungated alerts: {ungated_count}")

conn.close()

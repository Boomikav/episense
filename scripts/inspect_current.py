import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cursor = conn.cursor()

cursor.execute("SELECT fused_event_id, canonical_disease, total_cases, json_data FROM fused_events WHERE json_data LIKE '%CURRENT_EVENT%'")
rows = cursor.fetchall()
print("Number of rows containing CURRENT_EVENT:", len(rows))
for r in rows:
    data = json.loads(r[3])
    if data.get("currentness_status") == "CURRENT_EVENT":
        print(f"ID: {r[0]} | Disease: {r[1]} | Cases: {r[2]}")
        print(f"  Window: {data.get('event_window_start')} to {data.get('event_window_end')}")
        print(f"  Assertion: {data.get('assertion_status')} | Certainty: {data.get('certainty')}")
        print(f"  Location: {data.get('canonical_location')}")

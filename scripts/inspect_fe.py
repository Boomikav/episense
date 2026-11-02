import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
r = con.execute("SELECT * FROM fused_events WHERE fused_event_id = '1e404a20-bbf2-503e-b2a3-16e044736014'").fetchone()
data = json.loads(r["json_data"])
print("event_window_start:", data.get("event_window_start"))
print("event_window_end:", data.get("event_window_end"))
print("publication_timestamp:", data.get("publication_timestamp"))
print("is_event_time_estimated:", data.get("is_event_time_estimated"))
print("assertion_status:", data.get("assertion_status"))
print("evidence_references:", data.get("evidence_references"))
print("contributing_observation_ids:", data.get("contributing_observation_ids"))

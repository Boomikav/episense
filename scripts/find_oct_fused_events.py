import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT fused_event_id, canonical_disease, primary_origin, earliest_time, latest_time, total_cases, json_data 
    FROM fused_events 
    WHERE primary_origin = 'LIVE_EXTERNAL'
""").fetchall()

oct_fes = []
for r in rows:
    data = json.loads(r["json_data"])
    ev_start = data.get("event_window_start")
    ev_end = data.get("event_window_end")
    if ev_start and "2026-10" in ev_start:
        oct_fes.append((r, data))

print(f"Total LIVE_EXTERNAL fused events with event_window_start in 2026-10: {len(oct_fes)}")
for r, d in oct_fes:
    print(r["fused_event_id"], r["canonical_disease"], d.get("event_window_start"), d.get("decision_category"), d.get("currentness_status"))

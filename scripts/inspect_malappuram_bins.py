import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
rows = con.execute("SELECT bin_id, series_key, iso_year, iso_week, json_data FROM time_bins WHERE series_key LIKE '%malappuram%'").fetchall()
print(f"Time bins for malappuram: {len(rows)}")
for r in rows:
    data = json.loads(r[4])
    print("Bin:", r[0], r[1], r[2], r[3], "fused_events:", data.get("fused_event_ids"), "p_start:", data.get("period_start"), "p_end:", data.get("period_end"))

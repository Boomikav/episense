import sqlite3

con = sqlite3.connect("data/surveillance_store.sqlite")
rows = con.execute("SELECT alert_id, disease_key, geo_key, origin, status, period_start, json_data FROM alerts WHERE period_start >= '2026-10-26'").fetchall()
print(f"Total alerts created for week 26 Oct: {len(rows)}")
for r in rows:
    print(r)

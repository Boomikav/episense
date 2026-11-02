import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
cur.execute("SELECT bin_id, iso_year, iso_week, json_data FROM time_bins WHERE series_key='dengue:india_national' ORDER BY iso_year, iso_week, bin_id")
rows = cur.fetchall()
print(f"Total rows for dengue:india_national: {len(rows)}")
for r in rows:
    data = json.loads(r[3])
    print(f"ID: {r[0]} | Year: {r[1]}, Week: {r[2]} | Start: {data.get('period_start')} | End: {data.get('period_end')} | Cases: {data.get('observed_case_count')} | Confirmed: {data.get('confirmed_cases')}")

conn.close()

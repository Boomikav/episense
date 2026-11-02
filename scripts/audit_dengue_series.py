import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check all series_keys in time_bins
cur.execute("SELECT DISTINCT series_key, COUNT(*) as cnt FROM time_bins GROUP BY series_key ORDER BY cnt DESC")
rows = cur.fetchall()
print("=== DISTINCT SERIES KEYS IN time_bins ===")
for r in rows:
    print(f"  {r['series_key']}: {r['cnt']} rows")

print("\n=== DENGUE BINS DETAIL ===")
cur.execute("SELECT bin_id, series_key, iso_year, iso_week, is_generic_historical, json_data FROM time_bins WHERE series_key LIKE '%dengue%' ORDER BY series_key, iso_year, iso_week")
dengue_bins = cur.fetchall()
print(f"Total dengue bins found: {len(dengue_bins)}")

series_map = {}
for b in dengue_bins:
    sk = b["series_key"]
    if sk not in series_map:
        series_map[sk] = []
    data = json.loads(b["json_data"])
    series_map[sk].append((b["bin_id"], b["iso_year"], b["iso_week"], data))

for sk, blist in series_map.items():
    print(f"\n=======================================================")
    print(f"Series: {sk} (total bins: {len(blist)})")
    for bid, y, w, d in blist:
        print(f"  Bin ID: {bid} | Year-Week: {y}-W{w:02d} | Start: {d.get('period_start')} -> End: {d.get('period_end')} | Cases: {d.get('observed_case_count')} | Deaths: {d.get('observed_death_count')} | Confirmed: {d.get('confirmed_cases')}")

# Check what raw data exists for dengue in data/raw or data/
print("\n=== RAW DATA FILES FOR DENGUE ===")
import glob
for f in glob.glob("data/**/*.csv", recursive=True):
    print(f"  CSV: {f}")
for f in glob.glob("data/**/*.json", recursive=True):
    if "dengue" in f.lower() or "opendengue" in f.lower():
        print(f"  JSON: {f}")

conn.close()

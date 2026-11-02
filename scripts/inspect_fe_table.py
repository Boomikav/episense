import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

total_fe = cur.execute("SELECT count(*) FROM fused_events").fetchone()[0]
print(f"Total rows in fused_events table: {total_fe}")

# Check breakdown by status and origin
for r in cur.execute("SELECT primary_origin, status, count(*) FROM fused_events GROUP BY primary_origin, status"):
    print("  Origin:", r[0], "| Status:", r[1], "| Count:", r[2])

conn.close()

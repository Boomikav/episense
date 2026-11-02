import sqlite3
import json
import re
import sys
from collections import defaultdict

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

# 1. Mpox observations
rows_mpox = cur.execute("""
    SELECT document_id, title, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
    AND (lower(metadata_json) LIKE '%mpox%' OR lower(text) LIKE '%mpox%')
""").fetchall()

print(f"Total Mpox documents found: {len(rows_mpox)}")
for r in rows_mpox:
    meta = json.loads(r[2]) if r[2] else {}
    raw_text = r[3] or ""
    print("-" * 60)
    print("Doc ID:", r[0])
    print("UID:", meta.get("unique_id"))
    print("Week:", meta.get("week") or meta.get("reporting_week"))
    print("Disease:", meta.get("disease"))
    print("District:", meta.get("district"), "| State:", meta.get("state"))
    print("Locality / Subdistrict:", meta.get("sub_district"))
    print("Cases:", meta.get("cases"), "| Deaths:", meta.get("deaths"))
    print("Status:", meta.get("status"))
    print("Start Date:", meta.get("event_start"))
    print("Text snippet:", raw_text[:300].replace("\n", " "))

# 2. Total observations check
total_obs = cur.execute("SELECT count(*) FROM documents WHERE source_id = 'idsp_bulletin_feed'").fetchone()[0]
print("\n" + "=" * 60)
print(f"Total IDSP bulletin observations in SQLite: {total_obs}")

conn.close()

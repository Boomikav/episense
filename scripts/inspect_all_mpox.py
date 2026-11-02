import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, title, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
    AND (lower(metadata_json) LIKE '%mpox%' OR lower(text) LIKE '%mpox%')
""").fetchall()

for r in rows:
    meta = json.loads(r[2]) if r[2] else {}
    uid = meta.get("unique_id", "")
    print("=" * 80)
    print(f"UID: {uid} | Doc ID: {r[0]}")
    print(f"Disease: {meta.get('disease')} | District: {meta.get('district')} | State: {meta.get('state')}")
    print(f"Subdistrict: {meta.get('sub_district')} | Cases: {meta.get('cases')} | Deaths: {meta.get('deaths')}")
    print(f"Start date: {meta.get('event_start')}")
    print(f"Full Text:\n{r[3]}")

conn.close()

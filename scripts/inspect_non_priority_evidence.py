import sqlite3
import json

conn = sqlite3.connect('data/surveillance_store.sqlite')
cur = conn.cursor()

print("=== RAICHUR RECORDS ===")
rows = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
    AND lower(metadata_json) LIKE '%raichur%'
""").fetchall()

for doc_id, m_str, txt in rows:
    meta = json.loads(m_str) if m_str else {}
    print("Doc ID:", doc_id)
    print("UID:", meta.get("unique_id"))
    print("Disease (raw):", meta.get("disease"))
    print("Canonical Disease:", meta.get("canonical_disease"))
    print("Week:", meta.get("week") or meta.get("reporting_week"))
    print("State / District:", meta.get("state"), "|", meta.get("district"))
    print("Subdistrict:", meta.get("sub_district"))
    print("Cases / Deaths:", meta.get("cases"), "|", meta.get("deaths"))
    print("Event Start:", meta.get("event_start"))
    print("Status:", meta.get("status"))
    print("Text:")
    print(txt)
    print("=" * 70)

print("\n=== KOTTAYAM MUMPS RECORDS ===")
rows_mumps = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
    AND lower(metadata_json) LIKE '%kottayam%'
    AND (lower(metadata_json) LIKE '%mumps%' OR lower(text) LIKE '%mumps%')
""").fetchall()

for doc_id, m_str, txt in rows_mumps:
    meta = json.loads(m_str) if m_str else {}
    print("Doc ID:", doc_id)
    print("UID:", meta.get("unique_id"))
    print("Disease (raw):", meta.get("disease"))
    print("Canonical Disease:", meta.get("canonical_disease"))
    print("Week:", meta.get("week") or meta.get("reporting_week"))
    print("State / District:", meta.get("state"), "|", meta.get("district"))
    print("Subdistrict:", meta.get("sub_district"))
    print("Cases / Deaths:", meta.get("cases"), "|", meta.get("deaths"))
    print("Event Start:", meta.get("event_start"))
    print("Status:", meta.get("status"))
    print("Text:")
    print(txt)
    print("=" * 70)

conn.close()

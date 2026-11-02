import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()

rows = cur.execute("""
    SELECT document_id, metadata_json, text
    FROM documents
    WHERE source_id = 'idsp_bulletin_feed'
    AND lower(text) LIKE '%shirishbani%'
""").fetchall()

print(f"Total Shirishbani documents: {len(rows)}")
for doc_id, m_str, text in rows:
    meta = json.loads(m_str) if m_str else {}
    print("Doc ID:", doc_id)
    print("UID:", meta.get("unique_id"))
    print("Disease:", meta.get("disease"))
    print("Cases:", meta.get("cases"))
    print("Text:", text)
    print("=" * 60)

conn.close()

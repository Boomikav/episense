import sqlite3

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT document_id, title, source_id, origin, publication_timestamp FROM documents WHERE publication_timestamp >= '2026-10-01'").fetchall()
print(f"Total documents with pub >= 2026-10-01: {len(rows)}")
for r in rows:
    print(r["document_id"], "|", r["title"][:50], "|", r["source_id"], "|", r["origin"], "|", r["publication_timestamp"])

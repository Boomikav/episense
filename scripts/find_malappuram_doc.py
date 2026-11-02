import sqlite3

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT document_id, title, origin, publication_timestamp FROM documents WHERE text LIKE '%Malappuram%' OR title LIKE '%Malappuram%' LIMIT 5").fetchall()
for r in rows:
    print(r["document_id"], r["title"], r["origin"], r["publication_timestamp"])

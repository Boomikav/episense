import sqlite3, json

con = sqlite3.connect("data/surveillance_store.sqlite")
con.row_factory = sqlite3.Row
r = con.execute("SELECT * FROM documents WHERE document_id = '26913e3b-96fd-54a9-b76e-8eae19b02dd8'").fetchone()
for k in r.keys():
    print(k, ":", str(r[k])[:100])

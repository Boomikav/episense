import sqlite3

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
cur.execute("PRAGMA table_info(documents)")
print("Columns in documents:", [r[1] for r in cur.fetchall()])
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("All tables:", [r[0] for r in cur.fetchall()])
conn.close()

import sqlite3
import json

conn = sqlite3.connect("data/surveillance_store.sqlite")
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
counts = {}
for t in tables:
    counts[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

print(json.dumps(counts, indent=2))

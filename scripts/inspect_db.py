import sqlite3

con = sqlite3.connect("data/surveillance_store.sqlite")
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

for t in tables:
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})").fetchall()]
    count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"Table {t} ({count} rows): {cols}")

print("\n--- Origin breakdown in documents ---")
for r in con.execute("SELECT origin, COUNT(*) FROM documents GROUP BY origin").fetchall():
    print(r)

print("\n--- Origin breakdown in fused_events ---")
for r in con.execute("SELECT primary_origin, COUNT(*) FROM fused_events GROUP BY primary_origin").fetchall():
    print(r)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()

with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables in SQLite database:", tables)

    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  {t}: {cnt} rows")

    print("\n--- Fused Events Table Analysis ---")
    # check if fused_events exists
    if "fused_events" in tables:
        cur.execute("SELECT primary_origin, status, count(*) FROM fused_events GROUP BY primary_origin, status")
        for r in cur.fetchall():
            print(f"  fused_events primary_origin={r[0]} status={r[1]} count={r[2]}")

    print("\n--- Documents Table Analysis ---")
    cur.execute("SELECT origin, count(*) FROM documents GROUP BY origin")
    for r in cur.fetchall():
        print(f"  documents origin={r[0]} count={r[1]}")

    print("\n--- Signals Table Analysis ---")
    cur.execute("SELECT origin, count(*) FROM signals GROUP BY origin")
    for r in cur.fetchall():
        print(f"  signals origin={r[0]} count={r[1]}")

    print("\n--- Alerts Table Analysis ---")
    cur.execute("SELECT origin, status, count(*) FROM alerts GROUP BY origin, status")
    for r in cur.fetchall():
        print(f"  alerts origin={r[0]} status={r[1]} count={r[2]}")

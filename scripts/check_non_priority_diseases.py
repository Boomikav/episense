import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.taxonomy.priority import is_priority_disease, resolve_priority_disease
from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()

with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT canonical_disease, primary_origin, count(*) FROM fused_events WHERE status='active' GROUP BY canonical_disease, primary_origin")
    rows = cur.fetchall()
    print("Diseases in active fused_events:")
    priority_counts = {"LIVE_EXTERNAL": 0, "HISTORICAL_CORPUS": 0}
    exploratory_counts = {"LIVE_EXTERNAL": 0, "HISTORICAL_CORPUS": 0}
    for r in rows:
        meta = resolve_priority_disease(r[0])
        prio = meta is not None
        orig = r[1]
        cnt = r[2]
        if prio:
            priority_counts[orig] = priority_counts.get(orig, 0) + cnt
        else:
            exploratory_counts[orig] = exploratory_counts.get(orig, 0) + cnt
        print(f"  {r[0]:<35} | origin={orig:<16} | count={cnt:<3} | priority={prio}")

    print("\nSummary:")
    print("  Priority diseases active fused events:", priority_counts)
    print("  Exploratory/other active fused events:", exploratory_counts)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.taxonomy.priority import PRIORITY_DISEASES
from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()

with db._get_connection() as conn:
    cur = conn.cursor()
    print(f"{'Disease':<28} | {'Events (All)':<12} | {'Events (Live)':<13} | {'Events (Hist)':<13} | {'Time Bins':<10}")
    print("-" * 85)
    for d in PRIORITY_DISEASES:
        d_name = d.canonical_name
        d_id = d.canonical_id.value
        aliases = [a.lower() for a in d.aliases]
        
        # Build query for fused events
        where_clauses = ["lower(canonical_disease) LIKE ?"] + ["lower(canonical_disease) LIKE ?" for _ in aliases[:3]]
        params = [f"%{d_name.lower()}%"] + [f"%{a}%" for a in aliases[:3]]
        
        sql = f"SELECT primary_origin, count(*) FROM fused_events WHERE status='active' AND ({' OR '.join(where_clauses)}) GROUP BY primary_origin"
        cur.execute(sql, params)
        orig_counts = {r[0]: r[1] for r in cur.fetchall()}
        total_ev = sum(orig_counts.values())
        live_ev = orig_counts.get("LIVE_EXTERNAL", 0)
        hist_ev = orig_counts.get("HISTORICAL_CORPUS", 0)
        
        # Query time bins
        cur.execute(f"SELECT count(*) FROM time_bins WHERE {' OR '.join(['lower(series_key) LIKE ?' for _ in params])}", params)
        bins_cnt = cur.fetchone()[0]
        
        print(f"{d_name:<28} | {total_ev:<12} | {live_ev:<13} | {hist_ev:<13} | {bins_cnt:<10}")

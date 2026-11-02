import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()

with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT fused_event_id, canonical_disease, primary_origin, earliest_time, latest_time FROM fused_events WHERE primary_origin = 'LIVE_EXTERNAL'")
    rows = cur.fetchall()
    print("Live external fused events count:", len(rows))
    years = {}
    for r in rows:
        y = str(r[3])[:4] if r[3] else "None"
        years[y] = years.get(y, 0) + 1
    print("Event window start years for LIVE_EXTERNAL fused events:", years)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()

with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT origin, source_id, count(*), min(publication_timestamp), max(publication_timestamp) FROM documents GROUP BY origin, source_id")
    for r in cur.fetchall():
        print(f"origin={r[0]:<18} | source={r[1]:<20} | count={r[2]:<3} | min_pub={str(r[3])[:10]} | max_pub={str(r[4])[:10]}")

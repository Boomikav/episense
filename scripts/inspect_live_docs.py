import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()
with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT document_id, title, publication_timestamp, retrieval_timestamp, origin, source_id FROM documents WHERE origin = 'LIVE_EXTERNAL'")
    rows = cur.fetchall()
    print(f"Total LIVE_EXTERNAL documents: {len(rows)}")
    
    pub_years = {}
    for r in rows:
        pub = str(r[2])[:4] if r[2] else "None"
        pub_years[pub] = pub_years.get(pub, 0) + 1
    print("Publication years for LIVE_EXTERNAL docs:", pub_years)

    print("\nSample 15 LIVE_EXTERNAL docs:")
    for r in rows[:15]:
        print(f"  {r[0][:8]} | pub={r[2]} | ret={r[3]} | src={r[5]} | {r[1][:55]}")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from episense.persistence.database import SurveillanceDatabase
db = SurveillanceDatabase()
with db._get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT series_key, iso_year, iso_week, count(*) FROM time_bins WHERE series_key LIKE '%dengue%' GROUP BY series_key, iso_year, iso_week")
    rows = cur.fetchall()
    print("Dengue time bins count:", len(rows))
    for r in rows:
        print(" ", r[0], r[1], r[2], r[3])

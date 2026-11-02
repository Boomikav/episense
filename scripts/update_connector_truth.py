import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.source import SourceConnectorStatus

db = SurveillanceDatabase()
with db._get_connection() as conn:
    cur = conn.cursor()
    # Check cdc_outbreak_feed: HTTP 200, but 0 items
    cur.execute("SELECT source_id, status, error_message, config_json FROM source_connectors WHERE source_id = 'cdc_outbreak_feed'")
    row = cur.fetchone()
    if row:
        print("CDC Outbreak Feed current status:", row[1])
        # Update status to reflect true state: content unavailable (empty feed)
        cur.execute("""
            UPDATE source_connectors 
            SET status = 'DEGRADED', 
                error_message = 'HTTP 200 reachable, but feed returned 0 usable records (empty feed)'
            WHERE source_id = 'cdc_outbreak_feed'
        """)
        conn.commit()
        print("Updated CDC Outbreak Feed to DEGRADED (Empty feed)")

    # Print all current statuses
    cur.execute("SELECT source_id, name, status, error_message FROM source_connectors")
    for r in cur.fetchall():
        print(f"  {r[0]:<20} | status={r[2]:<24} | {r[3]}")

import sys
sys.path.insert(0, "src")
from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.persistence.database import SurveillanceDatabase
from episense.connectors.service import SourcePollingService

db = SurveillanceDatabase("data/surveillance_store.sqlite")
state = SurveillanceStateStore(db=db)
pipeline = ContinuousSurveillancePipeline(state=state)
service = SourcePollingService(pipeline=pipeline, db=db)

print("Second poll: testing anti-inflation and duplicate rejection...")
res = service.poll_source("who_news_feed")
print(f"Second poll result:")
print(f"  Status: {res.status}")
print(f"  Docs found: {res.documents_found}")
print(f"  Docs ingested: {res.documents_ingested}")
print(f"  Duplicates skipped: {res.duplicates_skipped}")
print(f"  Items deferred: {res.items_deferred}")

import sys
sys.path.insert(0, "src")
import traceback
from episense.api.server import create_surveillance_server
from episense.streaming.state import SurveillanceStateStore
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.persistence.database import SurveillanceDatabase
from episense.connectors.service import SourcePollingService

db = SurveillanceDatabase("data/surveillance_store.sqlite")
state = SurveillanceStateStore(db=db)
pipeline = ContinuousSurveillancePipeline(state=state)
service = SourcePollingService(pipeline=pipeline, db=db)

try:
    print("Calling service.poll_source('who_news_feed')...")
    res = service.poll_source("who_news_feed")
    print(f"Success! Status: {res.status}, docs found: {res.documents_found}, ingested: {res.documents_ingested}")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()

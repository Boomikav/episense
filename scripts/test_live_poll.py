import sys
sys.path.insert(0, "src")
import urllib.request
import feedparser
from episense.connectors.adapters import WHOOutbreakNewsConnector, IDSPBulletinConnector, CDCOutbreakConnector

print("Testing external connectivity to WHO News Feed...")
who = WHOOutbreakNewsConnector()
try:
    who_docs = who.fetch()
    print(f"WHO fetch succeeded: {len(who_docs)} items returned.")
    if who_docs:
        print(f"  First item title: {who_docs[0].title}")
        print(f"  First item pub: {who_docs[0].publication_timestamp}")
        print(f"  First item URL: {who_docs[0].url}")
except Exception as e:
    print(f"WHO fetch failed: {e}")

print("\nTesting external connectivity to IDSP Bulletin Feed...")
idsp = IDSPBulletinConnector()
try:
    idsp_docs = idsp.fetch()
    print(f"IDSP fetch succeeded: {len(idsp_docs)} items returned.")
except Exception as e:
    print(f"IDSP fetch failed: {e}")

print("\nTesting external connectivity to CDC Outbreak Feed...")
cdc = CDCOutbreakConnector()
try:
    cdc_docs = cdc.fetch()
    print(f"CDC fetch succeeded: {len(cdc_docs)} items returned.")
except Exception as e:
    print(f"CDC fetch failed: {e}")

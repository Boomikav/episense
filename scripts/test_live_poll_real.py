import sys
sys.path.insert(0, "src")

from episense.connectors.sources import WHONewsConnector, CDCOutbreakConnector
from episense.schemas.source import SourceConnectorConfig, SourceType

cfg_who = SourceConnectorConfig(
    source_id="who_news_feed",
    name="WHO News",
    endpoint_url="https://www.who.int/rss-feeds/news-english.xml",
    source_type=SourceType.NEWS_MEDIA,
    enabled=True,
)

print("Polling WHO News feed live...")
who = WHONewsConnector(cfg_who)
docs, record = who.fetch_documents()
print(f"WHO Status: {record.status}, HTTP: {record.http_status}, Docs found: {len(docs)}, Ingested: {record.documents_ingested}")
if docs:
    print(f"  First doc title: {docs[0].title}")
    print(f"  First doc pub: {docs[0].publication_timestamp}")
    print(f"  First doc URL: {docs[0].url}")
    print(f"  Raw payload sample (first 150 chars): {docs[0].raw_text[:150]}")

print("\nPolling CDC Outbreak feed live...")
cfg_cdc = SourceConnectorConfig(
    source_id="cdc_outbreak_feed",
    name="CDC Outbreak Feed",
    endpoint_url="https://tools.cdc.gov/api/v2/resources/media/403372.rss",
    source_type=SourceType.OFFICIAL_BULLETIN,
    enabled=True,
)
cdc = CDCOutbreakConnector(cfg_cdc)
cdc_docs, cdc_record = cdc.fetch_documents()
print(f"CDC Status: {cdc_record.status}, HTTP: {cdc_record.http_status}, Docs found: {len(cdc_docs)}")

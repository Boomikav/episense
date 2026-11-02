import sqlite3
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import httpx
from episense.taxonomy.priority import PRIORITY_CANONICAL_NAMES

def inspect_live_and_search_feeds():
    print("=" * 80)
    print("AUDITING LIVE RETRIEVAL VS RECENT DISEASE DISCOVERY")
    print("=" * 80)

    # 1. Audit current live documents in SQLite
    conn = sqlite3.connect("data/surveillance_store.sqlite")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = c.execute("""
        SELECT document_id, source_id, origin, title, publication_timestamp, retrieval_timestamp, metadata_json
        FROM documents
        WHERE origin = 'LIVE_EXTERNAL'
        ORDER BY publication_timestamp DESC
    """).fetchall()

    print(f"Total LIVE_EXTERNAL documents in DB: {len(rows)}")
    pub_years = {}
    for r in rows:
        pts = r["publication_timestamp"]
        year = pts[:4] if pts else "None"
        pub_years[year] = pub_years.get(year, 0) + 1
    print("Breakdown by publication year:", pub_years)

    # Check which ones are genuinely >= 2025
    recent_live = [r for r in rows if (r["publication_timestamp"] or "") >= "2025"]
    print(f"Genuinely recent (published >= 2025) LIVE_EXTERNAL docs in DB: {len(recent_live)}")
    for r in recent_live[:5]:
        print(f"  [{r['source_id']}] {r['publication_timestamp'][:10]}: {r['title']}")

    # 2. Query live RSS feeds directly to see what upstream contains right now
    print("\n" + "=" * 80)
    print("QUERYING CURRENT LIVE EXTERNAL FEEDS FOR RECENT PRIORITY-DISEASE REPORTS")
    print("=" * 80)

    feeds = [
        ("who_news_feed", "https://www.who.int/rss-feeds/news-english.xml"),
        ("pib_mohfw_feed", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1"),
    ]

    priority_keywords = [p.lower() for p in PRIORITY_CANONICAL_NAMES]
    # Also include sub-terms
    priority_keywords.extend(["dengue", "malaria", "chikungunya", "cholera", "leptospirosis", "encephalitis", "typhus", "diarrhoea", "diarrheal"])

    found_priority_items = []
    for s_id, url in feeds:
        try:
            print(f"\nPolling {s_id} ({url})...")
            resp = httpx.get(url, timeout=10.0, headers={"User-Agent": "EpiSenseAudit/2.0"})
            print(f"  HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                print(f"  Total items in upstream XML: {len(items)}")
                for it in items:
                    title = (it.find("title").text or "").strip() if it.find("title") is not None else ""
                    desc = (it.find("description").text or "").strip() if it.find("description") is not None else ""
                    pub = (it.find("pubDate").text or "").strip() if it.find("pubDate") is not None else ""
                    link = (it.find("link").text or "").strip() if it.find("link") is not None else ""
                    
                    full_text = f"{title} {desc}".lower()
                    matched = [k for k in priority_keywords if k in full_text]
                    if matched:
                        found_priority_items.append({
                            "source_id": s_id,
                            "title": title,
                            "pubDate": pub,
                            "link": link,
                            "matched": matched,
                        })
        except Exception as e:
            print(f"  Error polling {s_id}: {e}")

    print(f"\nPriority disease matches discovered in live feeds: {len(found_priority_items)}")
    for item in found_priority_items:
        print(f"  [{item['source_id']}] Pub: {item['pubDate']}")
        print(f"    Title: {item['title']}")
        print(f"    Matched terms: {item['matched']}")
        print(f"    Link: {item['link']}")

if __name__ == "__main__":
    inspect_live_and_search_feeds()

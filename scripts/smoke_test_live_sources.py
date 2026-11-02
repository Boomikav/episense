"""
Real-world external source network probe and smoke test for EpiSense.
Tests all 6 configured public health feeds for accessibility, rate limits,
headers, response formats, and parsing viability.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx
from episense.connectors.base import DEFAULT_USER_AGENT, clean_html_text

FEEDS = [
    {
        "source_id": "who_news_feed",
        "name": "World Health Organization News",
        "url": "https://www.who.int/rss-feeds/news-english.xml",
        "category": "RSS 2.0 XML",
    },
    {
        "source_id": "pib_mohfw_feed",
        "name": "MoHFW India (Press Information Bureau)",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1",
        "category": "RSS 2.0 XML",
    },
    {
        "source_id": "cdc_outbreak_feed",
        "name": "CDC Outbreak Notices",
        "url": "https://tools.cdc.gov/api/v2/resources/media/403372.rss",
        "category": "RSS 2.0 XML",
    },
    {
        "source_id": "promed_mail_rss",
        "name": "ProMED-mail Global Surveillance",
        "url": "https://promedmail.org/feed/",
        "category": "RSS 2.0 XML",
    },
    {
        "source_id": "idsp_bulletin_feed",
        "name": "IDSP Weekly Outbreak Bulletins (NCDC)",
        "url": "https://ncdc.mohfw.gov.in/includes/WeeklyOutbreaks.php",
        "category": "HTML / PDF Directory",
    },
    {
        "source_id": "idsp_portal",
        "name": "IDSP Portal (NCDC)",
        "url": "https://idsp.mohfw.gov.in/",
        "category": "Government Web Portal",
    },
]

def probe_feed(feed):
    url = feed["url"]
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, application/json, text/html;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }
    t0 = time.perf_counter()
    res = {
        "source_id": feed["source_id"],
        "name": feed["name"],
        "url": url,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status_code": None,
        "latency_ms": None,
        "content_type": None,
        "etag": None,
        "last_modified": None,
        "bytes_received": 0,
        "item_count": 0,
        "usable_documents": False,
        "classification": "UNKNOWN",
        "diagnostic_notes": "",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            latency = (time.perf_counter() - t0) * 1000.0
            res["status_code"] = resp.status_code
            res["latency_ms"] = round(latency, 1)
            res["content_type"] = resp.headers.get("content-type", "")
            res["etag"] = resp.headers.get("etag")
            res["last_modified"] = resp.headers.get("last-modified")
            res["bytes_received"] = len(resp.content)

            if resp.status_code == 200:
                ct = res["content_type"].lower()
                if "xml" in ct or resp.content.strip().startswith(b"<?xml") or b"<rss" in resp.content or b"<feed" in resp.content:
                    try:
                        root = ET.fromstring(resp.content)
                        channel = root.find("channel") or root
                        items = channel.findall("item") or channel.findall("{http://www.w3.org/2005/Atom}entry")
                        res["item_count"] = len(items)
                        if len(items) > 0:
                            res["usable_documents"] = True
                            res["classification"] = "OPERATIONAL"
                            # Inspect first item
                            first = items[0]
                            title = first.find("title")
                            title_text = title.text if title is not None else "N/A"
                            res["diagnostic_notes"] = f"Parsed {len(items)} items. Sample: {title_text[:60]}"
                        else:
                            res["usable_documents"] = False
                            res["classification"] = "DEGRADED"
                            res["diagnostic_notes"] = "HTTP 200 returned but 0 items found in feed."
                    except Exception as e:
                        res["classification"] = "PARSING_ERROR"
                        res["diagnostic_notes"] = f"XML parse error: {e}"
                elif "html" in ct:
                    res["classification"] = "OPERATIONAL_HTML"
                    res["diagnostic_notes"] = f"HTML page received ({len(resp.content)} bytes)."
                else:
                    res["classification"] = "UNEXPECTED_CONTENT_TYPE"
                    res["diagnostic_notes"] = f"Unexpected content-type: {ct}"
            elif resp.status_code in (401, 403):
                res["classification"] = "AUTHENTICATION_REQUIRED"
                res["diagnostic_notes"] = f"HTTP {resp.status_code} Access Denied / Auth Required."
            elif resp.status_code == 404:
                res["classification"] = "PERMANENT_UNAVAILABLE"
                res["diagnostic_notes"] = "HTTP 404 Not Found (Endpoint retired/moved)."
            else:
                res["classification"] = f"HTTP_{resp.status_code}"
                res["diagnostic_notes"] = f"Unexpected status: {resp.status_code}"

    except httpx.ConnectTimeout:
        res["classification"] = "TIMEOUT"
        res["diagnostic_notes"] = "Connection timed out after 15s."
    except httpx.ConnectError as ce:
        res["classification"] = "CONNECT_ERROR"
        res["diagnostic_notes"] = f"Connection failed: {ce}"
    except Exception as e:
        res["classification"] = "ERROR"
        res["diagnostic_notes"] = f"Exception: {type(e).__name__}: {e}"

    return res

if __name__ == "__main__":
    print(f"Executing real external network smoke tests at {datetime.now(timezone.utc).isoformat()}...")
    print("=" * 80)
    for f in FEEDS:
        r = probe_feed(f)
        print(f"Source: {r['source_id']:<20} | Status: {r['status_code']!s:<4} | Latency: {r['latency_ms']!s:<6}ms | Class: {r['classification']}")
        print(f"  Notes: {r['diagnostic_notes']}")
        if r['etag'] or r['last_modified']:
            print(f"  Caching: ETag={r['etag']} | Last-Modified={r['last_modified']}")
        print("-" * 80)

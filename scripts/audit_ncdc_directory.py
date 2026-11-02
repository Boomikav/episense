import re
import json
import hashlib
from pathlib import Path
from urllib.parse import urljoin
import httpx
from datetime import datetime, timezone

DIRECTORY_URL = "https://ncdc.mohfw.gov.in/uploads/weekly_outbreaks/2026/"
STORAGE_DIR = Path("data/raw/ncdc_2026")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def audit_directory():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers, verify=False) as client:
        print(f"Connecting to {DIRECTORY_URL}...")
        resp = client.get(DIRECTORY_URL)
        print(f"HTTP Status: {resp.status_code}")
        
        # Parse links
        html = resp.text
        pdf_matches = re.findall(r'href=[\"\']([^\"\']+\.pdf)[\"\']', html, re.IGNORECASE)
        print(f"Found {len(pdf_matches)} raw PDF hrefs in directory HTML.")
        
        # Load existing manifest if present
        manifest_path = STORAGE_DIR / "manifest.json"
        existing_items = {}
        if manifest_path.exists():
            for item in json.loads(manifest_path.read_text(encoding="utf-8")):
                existing_items[item.get("reporting_week")] = item

        discovered = []
        seen_weeks = set()
        
        for href in pdf_matches:
            fname = Path(href).name
            week_num = None
            m1 = re.search(r'(\d{1,2})(?:st|nd|rd|th)', fname, re.IGNORECASE)
            if m1:
                week_num = int(m1.group(1))
            else:
                m2 = re.search(r'(?:week|wk)[_\s]*0*(\d{1,2})', fname, re.IGNORECASE)
                if m2:
                    week_num = int(m2.group(1))
            
            if week_num is None or week_num < 1 or week_num > 53:
                continue
            if week_num in seen_weeks:
                continue
            seen_weeks.add(week_num)
            
            full_url = urljoin(DIRECTORY_URL, href)
            discovered.append({
                "reporting_week": week_num,
                "week": week_num,
                "filename": fname,
                "url": full_url,
                "discovered_at": datetime.now(timezone.utc).isoformat()
            })
            
        discovered.sort(key=lambda x: x["reporting_week"])
        print(f"Discovered {len(discovered)} unique weekly PDFs (Weeks {min(seen_weeks)} to {max(seen_weeks)}).")
        
        return client, discovered, existing_items

if __name__ == "__main__":
    audit_directory()

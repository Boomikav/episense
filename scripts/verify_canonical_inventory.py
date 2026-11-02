import hashlib
import json
from pathlib import Path
import pandas as pd

def verify_datasets():
    print("=" * 80)
    print("CANONICAL EIGHT-DISEASE DATASETS AUDIT")
    print("=" * 80)
    manifest_path = Path("data/benchmarks/canonical_eight_disease_inventory.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    data_dir = Path("data/raw/official_historical_series")
    files = sorted(data_dir.glob("*.csv"))

    print(f"Manifest version: {manifest.get('manifest_version')}")
    print(f"Total CSV files found: {len(files)}\n")

    for fpath in files:
        with open(fpath, "rb") as f:
            computed_hash = hashlib.sha256(f.read()).hexdigest()
        df = pd.read_csv(fpath)
        
        m_entry = manifest["diseases"].get(fpath.name, {})
        manifest_hash = m_entry.get("sha256")
        hash_match = (computed_hash == manifest_hash)

        year_col = "year" if "year" in df.columns else "Year"
        years = sorted(df[year_col].unique())
        span_min, span_max = min(years), max(years)
        expected_years = list(range(span_min, span_max + 1))
        missing_years = [y for y in expected_years if y not in years]

        print(f"File: {fpath.name}")
        print(f"  Rows: {len(df)} | Unique Years: {len(years)} ({span_min} - {span_max})")
        print(f"  Missing calendar years in span: {missing_years if missing_years else 'None (Complete)'}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Source: {df['source'].iloc[0] if 'source' in df.columns else m_entry.get('source')}")
        print(f"  Geo Level: {df['geographic_level'].iloc[0] if 'geographic_level' in df.columns else 'National'}")
        print(f"  Frequency: {df['frequency'].iloc[0] if 'frequency' in df.columns else 'Annual'}")
        print(f"  SHA-256 Match: {hash_match} ({computed_hash[:16]}...)")
        print()

if __name__ == "__main__":
    verify_datasets()

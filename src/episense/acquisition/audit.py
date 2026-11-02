"""
Audit utilities for independent verification of EpiSense benchmarks and raw corpora.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from episense.schemas.dataset import BenchmarkManifest


class BenchmarkAuditor:
    """
    Performs independent verification of manifest metadata against stored disk artifacts.
    """

    @staticmethod
    def audit_manifest(manifest_path: str | Path, base_dir: str | Path) -> Dict[str, Any]:
        """
        Audits a benchmark manifest JSON file and cross-verifies all references.
        """
        m_path = Path(manifest_path)
        b_dir = Path(base_dir)

        if not m_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {m_path}")

        import json
        with open(m_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = BenchmarkManifest(**data)
        docs = manifest.documents

        unique_ids = set()
        unique_hashes = set()
        sources_count = {}
        years_count = {}
        splits_count = {}
        missing_raw = 0
        missing_proc = 0
        hash_mismatches = 0
        incidents_by_split: Dict[str, set] = {"train": set(), "dev": set(), "test": set(), "benchmark": set()}

        for bdoc in docs:
            d = bdoc.document
            doc_id = str(d.document_id)
            unique_ids.add(doc_id)
            h = d.content_hash_sha256
            unique_hashes.add(h)

            src = d.source_id
            sources_count[src] = sources_count.get(src, 0) + 1

            yr = str(d.publication_timestamp.year)
            years_count[yr] = years_count.get(yr, 0) + 1

            split_val = bdoc.split.value
            splits_count[split_val] = splits_count.get(split_val, 0) + 1

            inc_id = d.provenance_metadata.get("incident_id", "unassigned")
            if split_val in incidents_by_split:
                incidents_by_split[split_val].add(inc_id)

            # Raw file check
            raw_file = b_dir / "data" / "raw" / f"{doc_id}.txt"
            if not raw_file.exists():
                missing_raw += 1
            else:
                with open(raw_file, "r", encoding="utf-8") as rf:
                    content = rf.read()
                computed_h = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if computed_h.lower() != h.lower():
                    hash_mismatches += 1

            # Processed file check
            proc_file = b_dir / "data" / "processed" / f"{doc_id}.txt"
            if not proc_file.exists():
                missing_proc += 1

        # Check incident leakage between splits
        train_inc = incidents_by_split.get("train", set())
        dev_inc = incidents_by_split.get("dev", set())
        test_inc = incidents_by_split.get("test", set())

        leakage_train_dev = train_inc.intersection(dev_inc)
        leakage_train_test = train_inc.intersection(test_inc)
        leakage_dev_test = dev_inc.intersection(test_inc)

        is_clean = (
            len(unique_ids) == len(docs)
            and len(unique_hashes) == len(docs)
            and missing_raw == 0
            and missing_proc == 0
            and hash_mismatches == 0
            and len(leakage_train_dev) == 0
            and len(leakage_train_test) == 0
            and len(leakage_dev_test) == 0
        )

        return {
            "is_clean": is_clean,
            "total_documents": len(docs),
            "unique_document_ids": len(unique_ids),
            "unique_content_hashes": len(unique_hashes),
            "sources_count": sources_count,
            "years_count": years_count,
            "splits_count": splits_count,
            "missing_raw_files": missing_raw,
            "missing_processed_files": missing_proc,
            "content_hash_mismatches": hash_mismatches,
            "incident_leakage": {
                "train_dev_overlap": list(leakage_train_dev),
                "train_test_overlap": list(leakage_train_test),
                "dev_test_overlap": list(leakage_dev_test),
            },
        }

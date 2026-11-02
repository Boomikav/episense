"""
Unit tests for the BenchmarkAuditor utility.
"""

from pathlib import Path
from episense.acquisition.audit import BenchmarkAuditor


def test_auditor_on_benchmark_v1():
    """Verify that BenchmarkAuditor passes cleanly on episense_benchmark_v1.json."""
    manifest_path = Path("data/benchmarks/episense_benchmark_v1.json")
    result = BenchmarkAuditor.audit_manifest(manifest_path, base_dir=".")

    assert result["is_clean"] is True
    assert result["total_documents"] == 52
    assert result["unique_document_ids"] == 52
    assert result["unique_content_hashes"] == 52
    assert result["missing_raw_files"] == 0
    assert result["missing_processed_files"] == 0
    assert result["content_hash_mismatches"] == 0

    # Leakage check
    leak = result["incident_leakage"]
    assert len(leak["train_dev_overlap"]) == 0
    assert len(leak["train_test_overlap"]) == 0
    assert len(leak["dev_test_overlap"]) == 0


def test_auditor_on_background_v1():
    """Verify that BenchmarkAuditor passes cleanly on episense_background_v1.json."""
    manifest_path = Path("data/benchmarks/episense_background_v1.json")
    result = BenchmarkAuditor.audit_manifest(manifest_path, base_dir=".")

    assert result["is_clean"] is True
    assert result["total_documents"] == 58
    assert result["missing_raw_files"] == 0
    assert result["content_hash_mismatches"] == 0

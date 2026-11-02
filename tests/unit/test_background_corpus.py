"""
Unit tests for background surveillance corpus manifest and files.
"""

import json
from pathlib import Path
import pytest

from episense.schemas.dataset import BenchmarkManifest
from episense.acquisition.validation import DocumentValidator


def test_background_manifest_loads_and_validates():
    """Verify episense_background_v1.json loads against BenchmarkManifest schema."""
    bg_path = Path("data/benchmarks/episense_background_v1.json")
    assert bg_path.exists(), "Background manifest missing!"

    with open(bg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    manifest = BenchmarkManifest(**data)
    assert manifest.dataset_name == "episense_background_v1"
    assert manifest.document_count == 58
    assert len(manifest.documents) == 58


def test_background_corpus_files_exist_and_match_hash():
    """Verify that all 58 background documents exist in raw and processed dirs with valid hashes."""
    bg_path = Path("data/benchmarks/episense_background_v1.json")
    with open(bg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = BenchmarkManifest(**data)

    raw_dir = Path("data/raw")
    proc_dir = Path("data/processed")

    for bdoc in manifest.documents:
        doc_id = str(bdoc.document.document_id)
        raw_file = raw_dir / f"{doc_id}.txt"
        proc_file = proc_dir / f"{doc_id}.txt"

        assert raw_file.exists(), f"Missing raw file for {doc_id}"
        assert proc_file.exists(), f"Missing proc file for {doc_id}"

        with open(raw_file, "r", encoding="utf-8") as rf:
            raw_text = rf.read()

        computed_hash = DocumentValidator.calculate_sha256(raw_text)
        assert computed_hash == bdoc.document.content_hash_sha256


def test_background_corpus_fills_2025_temporal_gap():
    """Verify that the background corpus contains 2025 documents."""
    bg_path = Path("data/benchmarks/episense_background_v1.json")
    with open(bg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = BenchmarkManifest(**data)

    years_2025 = [
        bdoc for bdoc in manifest.documents
        if bdoc.document.publication_timestamp.year == 2025
    ]
    assert len(years_2025) >= 20, f"Expected >= 20 documents from 2025, found {len(years_2025)}"


def test_benchmark_and_background_datasets_are_disjoint():
    """Verify that benchmark v1 and background v1 have completely disjoint document IDs."""
    with open("data/benchmarks/episense_benchmark_v1.json", "r", encoding="utf-8") as f:
        bench_data = json.load(f)
    with open("data/benchmarks/episense_background_v1.json", "r", encoding="utf-8") as f:
        bg_data = json.load(f)

    bench_ids = {bdoc["document"]["document_id"] for bdoc in bench_data["documents"]}
    bg_ids = {bdoc["document"]["document_id"] for bdoc in bg_data["documents"]}

    assert bench_ids.isdisjoint(bg_ids), "Overlap detected between benchmark and background IDs!"

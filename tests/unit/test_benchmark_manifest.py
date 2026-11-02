"""
Unit tests validating the real EpiSense Benchmark v1 manifest and stored files.
"""

import json
import os
import pytest
from pathlib import Path

from episense.schemas.dataset import BenchmarkManifest
from episense.acquisition.validation import DocumentValidator


def test_manifest_loads_and_validates():
    """Verify that data/benchmarks/episense_benchmark_v1.json loads against Pydantic schema."""
    manifest_path = Path("data/benchmarks/episense_benchmark_v1.json")
    assert manifest_path.exists(), "Benchmark manifest file does not exist!"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    manifest = BenchmarkManifest(**data)
    assert manifest.dataset_name == "episense_benchmark_v1"
    assert manifest.document_count == 52
    assert len(manifest.documents) == 52


def test_raw_and_processed_files_exist():
    """Verify that every document in the manifest has corresponding raw and processed files."""
    manifest_path = Path("data/benchmarks/episense_benchmark_v1.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = BenchmarkManifest(**data)

    raw_dir = Path("data/raw")
    proc_dir = Path("data/processed")

    for bdoc in manifest.documents:
        doc_id = str(bdoc.document.document_id)
        raw_file = raw_dir / f"{doc_id}.txt"
        proc_file = proc_dir / f"{doc_id}.txt"

        assert raw_file.exists(), f"Missing raw file for doc {doc_id}"
        assert proc_file.exists(), f"Missing processed file for doc {doc_id}"

        # Verify raw content hash matches file contents
        with open(raw_file, "r", encoding="utf-8") as f:
            raw_content = f.read()
        computed_hash = DocumentValidator.calculate_sha256(raw_content)
        assert computed_hash == bdoc.document.content_hash_sha256


def test_manifest_source_distribution_and_epistemic_diversity():
    """Verify source diversity and epistemic balance across the benchmark."""
    manifest_path = Path("data/benchmarks/episense_benchmark_v1.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = BenchmarkManifest(**data)

    sources = {bdoc.document.source_id for bdoc in manifest.documents}
    assert "who_don" in sources
    assert "ncdc_idsp_india" in sources
    assert "pib_mohfw_india" in sources
    assert "promed_mail" in sources
    assert "medrxiv_preprints" in sources

    categories = {
        bdoc.document.provenance_metadata.get("event_category")
        for bdoc in manifest.documents
    }
    assert "confirmed_outbreak" in categories
    assert "routine_surveillance" in categories
    assert "precautionary_advisory" in categories
    assert "negation_statement" in categories


def test_splits_are_disjoint():
    """Verify that train, dev, and test splits have zero overlap."""
    manifest_path = Path("data/benchmarks/episense_benchmark_v1.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = BenchmarkManifest(**data)

    train_ids = {str(d.document.document_id) for d in manifest.documents if d.split.value == "train"}
    dev_ids = {str(d.document.document_id) for d in manifest.documents if d.split.value == "dev"}
    test_ids = {str(d.document.document_id) for d in manifest.documents if d.split.value == "test"}

    assert len(train_ids) + len(dev_ids) + len(test_ids) == 52
    assert train_ids.isdisjoint(dev_ids)
    assert train_ids.isdisjoint(test_ids)
    assert dev_ids.isdisjoint(test_ids)

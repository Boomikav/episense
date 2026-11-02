"""
Unit Tests for Mandatory Priority Disease Registry Enforcement.
Verifies:
1. Canonical priority registry contains exactly the 8 authorized research diseases:
   - Dengue, Malaria, Chikungunya, Leptospirosis, Cholera, Acute Diarrhoeal Disease,
     Japanese Encephalitis, Scrub Typhus.
2. Explicitly fails if any out-of-scope disease (e.g. Zika, Kyasanur Forest Disease/KFD, Nipah, CCHF)
   replaces a priority disease or appears in the primary registry.
3. Dataset inventory (canonical_eight_disease_inventory.json) and official historical series
   contain exactly the 8 authorized priority datasets with verified cryptographic SHA-256 integrity.
4. Data sufficiency profiler and models sufficiency endpoints evaluate strictly the 8 canonical diseases.
"""

import hashlib
import json
from pathlib import Path
import pytest

from episense.taxonomy.priority import (
    PRIORITY_CANONICAL_NAMES,
    PRIORITY_CANONICAL_IDS,
    PRIORITY_DISEASES,
    PriorityDiseaseId,
)
from episense.surveillance.data_sufficiency import (
    DataSufficiencyProfiler,
    DEFAULT_PRIORITY_DISEASES,
)

EXPECTED_PRIORITY_DISEASES = [
    "Dengue",
    "Malaria",
    "Chikungunya",
    "Leptospirosis",
    "Cholera",
    "Acute Diarrhoeal Disease",
    "Japanese Encephalitis",
    "Scrub Typhus",
]

DISALLOWED_OUT_OF_SCOPE_DISEASES = [
    "Zika",
    "Zika virus disease",
    "Kyasanur Forest Disease",
    "KFD",
    "Monkey Fever",
    "Nipah",
    "Crimean-Congo Hemorrhagic Fever",
    "CCHF",
    "COVID-19",
    "Yellow Fever",
    "Ebola",
    "Marburg",
]


class TestPriorityRegistryEnforcement:
    def test_canonical_registry_contains_exactly_eight_diseases(self):
        """Registry must contain exactly 8 diseases, matching the authoritative list."""
        assert len(PRIORITY_DISEASES) == 8, f"Expected 8 priority diseases, got {len(PRIORITY_DISEASES)}"
        assert len(PRIORITY_CANONICAL_NAMES) == 8
        assert len(DEFAULT_PRIORITY_DISEASES) == 8

        names_set = set(PRIORITY_CANONICAL_NAMES)
        for expected in EXPECTED_PRIORITY_DISEASES:
            assert expected in names_set, f"Mandatory priority disease '{expected}' missing from registry"

    def test_disallowed_diseases_are_strictly_excluded_from_priority_registry(self):
        """Explicitly fails if any out-of-scope disease replaces or enters the priority registry."""
        names_lower = {n.lower() for n in PRIORITY_CANONICAL_NAMES}
        ids_lower = {i.lower() for i in PRIORITY_CANONICAL_IDS}

        for disallowed in DISALLOWED_OUT_OF_SCOPE_DISEASES:
            d_low = disallowed.lower()
            assert d_low not in names_lower, f"Out-of-scope disease '{disallowed}' found in PRIORITY_CANONICAL_NAMES"
            assert d_low not in ids_lower, f"Out-of-scope disease '{disallowed}' found in PRIORITY_CANONICAL_IDS"

            for entry in PRIORITY_DISEASES:
                assert entry.canonical_name.lower() != d_low, f"Out-of-scope disease '{disallowed}' found in PRIORITY_DISEASES"
                assert entry.canonical_id.value.lower() != d_low

    def test_canonical_manifest_inventory_contains_exactly_eight_priority_datasets(self):
        """Verifies canonical_eight_disease_inventory.json contains strictly the 8 datasets and no out-of-scope entries."""
        manifest_path = Path("data/benchmarks/canonical_eight_disease_inventory.json")
        assert manifest_path.exists(), "canonical_eight_disease_inventory.json manifest not found"

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        diseases = manifest.get("diseases", {})
        assert len(diseases) == 8, f"Manifest should contain exactly 8 datasets, found {len(diseases)}"

        # Verify no disallowed disease name in manifest keys or file paths
        for file_key in diseases.keys():
            for disallowed in ["zika", "kfd", "kyasanur", "nipah", "cchf"]:
                assert disallowed not in file_key.lower(), f"Manifest contains out-of-scope dataset '{file_key}'"

        # Verify ADD and Scrub Typhus are explicitly present
        assert any("add_" in k.lower() for k in diseases.keys()), "Acute Diarrhoeal Disease dataset missing from manifest"
        assert any("scrub_typhus_" in k.lower() for k in diseases.keys()), "Scrub Typhus dataset missing from manifest"

    def test_actual_csv_files_exist_and_match_manifest_hashes(self):
        """Verifies physical presence, non-emptiness, and SHA-256 hashes of all 8 priority datasets."""
        manifest_path = Path("data/benchmarks/canonical_eight_disease_inventory.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        data_dir = Path("data/raw/official_historical_series")
        assert data_dir.exists(), "Official historical series directory missing"

        for file_name, meta in manifest["diseases"].items():
            fpath = data_dir / file_name
            assert fpath.exists(), f"Physical dataset file {file_name} missing on disk"

            with open(fpath, "rb") as fl:
                actual_hash = hashlib.sha256(fl.read()).hexdigest()

            assert actual_hash == meta["sha256"], f"SHA-256 hash mismatch for {file_name}: {actual_hash} != {meta['sha256']}"

            # Verify non-empty data rows
            with open(fpath, "r", encoding="utf-8") as fl:
                lines = [line.strip() for line in fl if line.strip()]
            assert len(lines) >= meta["row_count"] + 1, f"File {file_name} has fewer rows than declared in manifest"

    def test_sufficiency_profiler_audits_exactly_eight_priority_diseases(self):
        """Verifies DataSufficiencyProfiler audits strictly the 8 canonical priority diseases."""
        profiler = DataSufficiencyProfiler()
        audit_results = profiler.audit_database()

        assert len(audit_results) == 8, f"Profiler returned {len(audit_results)} diseases, expected 8"
        for expected in EXPECTED_PRIORITY_DISEASES:
            assert expected in audit_results, f"Expected priority disease '{expected}' not profiled"

        for disallowed in DISALLOWED_OUT_OF_SCOPE_DISEASES:
            assert disallowed not in audit_results, f"Disallowed disease '{disallowed}' profiled in default priority audit"

"""
Unit Tests for DataSufficiencyProfiler (Phase 1 & Phase 8).
Verifies:
  - Profiling from database and in-memory events/bins
  - Data structure classification (Longitudinal, Discontinuous, Cross-sectional, Sparse)
  - Consecutive week computation
  - Go/No-Go decisions for anomaly detection and forecasting
  - Capability A vs Capability B partitioning
"""

import json
from pathlib import Path
import pytest

from episense.surveillance.data_sufficiency import (
    DataSufficiencyProfiler,
    DataStructureClassification,
    DEFAULT_RAINY_SEASON_DISEASES,
)


class TestDataSufficiencyProfiler:
    def test_default_rainy_season_diseases_count(self):
        assert len(DEFAULT_RAINY_SEASON_DISEASES) == 8
        assert "Dengue" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Malaria" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Chikungunya" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Leptospirosis" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Cholera" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Acute Diarrhoeal Disease" in DEFAULT_RAINY_SEASON_DISEASES or "Acute Diarrheal Disease" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Japanese Encephalitis" in DEFAULT_RAINY_SEASON_DISEASES
        assert "Scrub Typhus" in DEFAULT_RAINY_SEASON_DISEASES

    def test_profile_empty_disease(self):
        profiler = DataSufficiencyProfiler()
        profile = profiler.profile_disease("Zika", all_events=[], all_bins=[])
        assert profile.total_fused_events == 0
        assert profile.total_time_bins == 0
        assert profile.max_consecutive_weeks == 0
        assert profile.data_structure_classification == DataStructureClassification.SPARSE_EVENT_REPORTS
        assert "NO-GO" in profile.forecasting_decision

    def test_profile_cross_sectional_snapshots(self):
        profiler = DataSufficiencyProfiler()
        events = [
            {
                "canonical_disease": "Dengue",
                "canonical_location": {"normalized_name": "Delhi"},
                "event_window_start": "2026-01-05T00:00:00Z",
                "aggregated_quantities": {"case_count": 50, "death_count": 0},
            }
        ]
        bins = [
            {
                "disease_key": "dengue",
                "geo_key": "delhi",
                "iso_year": 2026,
                "iso_week": 1,
                "observed_case_count": 50,
            },
            {
                "disease_key": "dengue",
                "geo_key": "delhi",
                "iso_year": 2026,
                "iso_week": 2,
                "observed_case_count": 60,
            },
        ]
        profile = profiler.profile_disease("Dengue", events, bins)
        assert profile.total_fused_events == 1
        assert profile.total_time_bins == 2
        assert profile.max_consecutive_weeks == 2
        assert profile.data_structure_classification == DataStructureClassification.CROSS_SECTIONAL_SNAPSHOTS
        assert "NO-GO" in profile.forecasting_decision
        assert "GO" in profile.capability_a_event_surveillance

    def test_profile_longitudinal_series(self):
        profiler = DataSufficiencyProfiler()
        events = []
        bins = []
        # 54 consecutive weeks ending in October 2026 (fresh active surveillance)
        for i in range(54):
            # i=0 -> 2025-W42; i=53 -> 2026-W43 (Oct 2026)
            total_week = 42 + i
            yr = 2025 if total_week <= 52 else 2026
            wk = total_week if total_week <= 52 else total_week - 52
            bins.append(
                {
                    "disease_key": "dengue",
                    "geo_key": "delhi",
                    "iso_year": yr,
                    "iso_week": wk,
                    "observed_case_count": 100 + i,
                }
            )
        profile = profiler.profile_disease("Dengue", events, bins)
        assert profile.max_consecutive_weeks >= 52
        assert profile.data_structure_classification == DataStructureClassification.LONGITUDINAL_TIME_SERIES
        assert "GO" in profile.forecasting_decision
        assert "GO" in profile.capability_b_quantitative_forecasting

    def test_audit_active_database(self):
        profiler = DataSufficiencyProfiler("data/surveillance_store.sqlite")
        results = profiler.audit_database()
        assert len(results) == 8
        for d in DEFAULT_RAINY_SEASON_DISEASES:
            assert d in results
            assert results[d].capability_a_event_surveillance.startswith("GO")

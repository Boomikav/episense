"""
Unit Tests for EpiSense Forecasting API Endpoints (Phase 7 & Phase 5).
Verifies:
  - GET /api/v1/forecasting/sufficiency
  - GET /api/v1/forecasting/series
  - POST /api/v1/forecasting/predict (with gating and abstention)
  - GET /api/v1/forecasting/history
  - GET /api/v1/forecasting/{id}
"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import numpy as np
import pytest
from fastapi.testclient import TestClient

from episense.api.app import create_app
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.streaming.state import SurveillanceStateStore


@pytest.fixture
def client_with_data(tmp_path):
    db_file = tmp_path / "api_test.sqlite"
    db = SurveillanceDatabase(db_file)
    state = SurveillanceStateStore(db=db)

    # Seed 20 consecutive weeks for dengue in delhi (fresh active surveillance ending Oct 2026)
    base = datetime(2026, 6, 8, tzinfo=timezone.utc)
    conn = db._get_connection()
    with conn:
        for w in range(1, 21):
            dt = base + timedelta(weeks=w - 1)
            b = EpidemiologicalTimeBin(
                disease_key="dengue",
                geo_key="delhi",
                period_start=dt,
                period_end=dt + timedelta(days=6, hours=23, minutes=59),
                iso_year=2026,
                iso_week=23 + w,
                observed_case_count=float(25 + w),
                fused_event_count=1,
                independent_source_count=1,
                supporting_observation_count=1,
            )
            state.bins_by_id[b.bin_id] = b
            state.bins_by_series[("dengue", "delhi")].append(b.bin_id)
            conn.execute(
                "INSERT INTO time_bins (bin_id, series_key, iso_year, iso_week, is_generic_historical, json_data) VALUES (?, ?, ?, ?, ?, ?)",
                (str(b.bin_id), "dengue:delhi", b.iso_year, b.iso_week, 0, b.model_dump_json()),
            )

        # Seed 2 weeks for cholera in puri (insufficient)
        for w in range(1, 3):
            dt = base + timedelta(weeks=w - 1)
            b = EpidemiologicalTimeBin(
                disease_key="cholera",
                geo_key="puri",
                period_start=dt,
                period_end=dt + timedelta(days=6, hours=23, minutes=59),
                iso_year=2026,
                iso_week=w,
                observed_case_count=5.0,
                fused_event_count=1,
                independent_source_count=1,
                supporting_observation_count=1,
            )
            state.bins_by_id[b.bin_id] = b
            state.bins_by_series[("cholera", "puri")].append(b.bin_id)
            conn.execute(
                "INSERT INTO time_bins (bin_id, series_key, iso_year, iso_week, is_generic_historical, json_data) VALUES (?, ?, ?, ?, ?, ?)",
                (str(b.bin_id), "cholera:puri", b.iso_year, b.iso_week, 0, b.model_dump_json()),
            )

    app = create_app(db=db, state=state)
    return TestClient(app)


def test_get_sufficiency_audit(client_with_data):
    resp = client_with_data.get("/api/v1/forecasting/sufficiency")
    assert resp.status_code == 200
    data = resp.json()
    assert "Dengue" in data
    assert "Malaria" in data
    assert "Cholera" in data
    assert "capability_a_event_surveillance" in data["Dengue"]


def test_list_series(client_with_data):
    resp = client_with_data.get("/api/v1/forecasting/series")
    assert resp.status_code == 200
    series = resp.json()
    assert len(series) >= 2

    # Verify dengue series has 20 weeks and is eligible
    dengue_series = next((s for s in series if s["series_key"] == "dengue:delhi"), None)
    assert dengue_series is not None
    assert dengue_series["max_consecutive_weeks"] == 20
    assert dengue_series["forecasting_eligible"] is True

    # Verify cholera series has 2 weeks and is not eligible
    cholera_series = next((s for s in series if s["series_key"] == "cholera:puri"), None)
    assert cholera_series is not None
    assert cholera_series["max_consecutive_weeks"] == 2
    assert cholera_series["forecasting_eligible"] is False


def test_predict_insufficient_baseline_abstention(client_with_data):
    # Call prediction on cholera:puri (only 2 weeks)
    payload = {
        "series_key": "cholera:puri",
        "model_type": "negative_binomial",
        "horizon_weeks": 4,
    }
    resp = client_with_data.post("/api/v1/forecasting/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sufficiency_status"] == "suppressed_insufficient_baseline"
    assert len(data["predictions"]) == 0
    assert "Forecasting gated" in data["abstention_rationale"]


def test_predict_sufficient_baseline(client_with_data):
    # Call prediction on dengue:delhi (20 weeks)
    payload = {
        "series_key": "dengue:delhi",
        "model_type": "negative_binomial",
        "horizon_weeks": 4,
        "persist": True,
    }
    resp = client_with_data.post("/api/v1/forecasting/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sufficiency_status"] == "sufficient"
    assert len(data["predictions"]) == 4
    for p in data["predictions"]:
        assert p["point_estimate"] > 0
        assert p["interval_95_lower"] <= p["point_estimate"] <= p["interval_95_upper"]

    # Check forecast history
    hist_resp = client_with_data.get("/api/v1/forecasting/history?disease=dengue")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) >= 1
    forecast_id = hist[0]["forecast_id"]

    # Check forecast detail
    detail_resp = client_with_data.get(f"/api/v1/forecasting/{forecast_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["forecast_id"] == forecast_id


def test_predict_invalid_series(client_with_data):
    payload = {"model_type": "negative_binomial"}
    resp = client_with_data.post("/api/v1/forecasting/predict", json=payload)
    assert resp.status_code == 400


def test_get_nonexistent_forecast(client_with_data):
    resp = client_with_data.get(f"/api/v1/forecasting/{uuid4()}")
    assert resp.status_code == 404

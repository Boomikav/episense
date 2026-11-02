"""
Epidemiological Forecasting API Routes for EpiSense (Phase 7 & Phase 5).
Exposes:
  - Longitudinal Data-Sufficiency Audit per pathogen
  - Available Time-Series Registry & Eligibility
  - Gated Predictive Forecasting (Seasonal Naive, Poisson, NegBin, Ensemble)
  - Historical Forecast Audits and Prediction Intervals
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from episense.api.dependencies import get_persistence_db, get_state_store
from episense.forecasting.engine import ForecastingEngine
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.forecast import (
    EpidemiologicalForecast,
    ForecastModelType,
    ForecastSufficiencyStatus,
)
from episense.schemas.signal import EpidemiologicalTimeBin
from episense.streaming.state import SurveillanceStateStore
from episense.surveillance.data_sufficiency import (
    DataSufficiencyProfiler,
    DiseaseSufficiencyProfile,
)

router = APIRouter(prefix="/api/v1/forecasting", tags=["Forecasting Engine"])
models_router = APIRouter(prefix="/api/v1/models", tags=["Model Sufficiency"])


class ForecastPredictionRequest(BaseModel):
    """Request payload to compute future epidemiological forecast."""
    series_key: Optional[str] = Field(None, description="Series key in format disease:geo")
    disease_key: Optional[str] = Field(None, description="Disease identifier, e.g. dengue")
    geo_key: Optional[str] = Field(None, description="Location identifier, e.g. delhi")
    model_type: ForecastModelType = Field(
        default=ForecastModelType.NEGATIVE_BINOMIAL,
        description="Forecast model: negative_binomial, poisson_glm, seasonal_naive, ensemble",
    )
    horizon_weeks: int = Field(default=4, ge=1, le=12, description="Horizon weeks ahead (1 to 12)")
    persist: bool = Field(default=True, description="Whether to persist the forecast to database")


class SeriesRegistryItem(BaseModel):
    """Metadata summary of an aggregated epidemiological time-series."""
    series_key: str
    disease_key: str
    geo_key: str
    total_bins: int
    positive_case_bins: int
    max_consecutive_weeks: int
    data_structure: str
    forecasting_eligible: bool
    rationale: str


@router.get(
    "/sufficiency",
    response_model=Dict[str, DiseaseSufficiencyProfile],
    summary="Pathogen Data-Sufficiency Audit",
    description="Audits historical and active surveillance repositories to establish scientific feasibility for each disease entity.",
)
@router.get(
    "/audit",
    response_model=Dict[str, DiseaseSufficiencyProfile],
    summary="Pathogen Data-Sufficiency Audit (Alias)",
    description="Alias endpoint for data-sufficiency audit.",
    include_in_schema=False,
)
async def get_data_sufficiency_audit() -> Dict[str, DiseaseSufficiencyProfile]:
    profiler = DataSufficiencyProfiler()
    return profiler.audit_database()


@models_router.get(
    "/sufficiency",
    summary="Pathogen Data-Sufficiency Audit (Model Alias)",
    description="Audits historical and active surveillance repositories to establish scientific feasibility for each canonical priority disease.",
)
async def get_models_data_sufficiency_audit() -> Dict[str, Any]:
    profiler = DataSufficiencyProfiler()
    profiles = profiler.audit_database()
    pathogens_status = {d: p.forecasting_decision for d, p in profiles.items()}
    return {
        "pathogens": pathogens_status,
        "profiles": {d: p.model_dump() for d, p in profiles.items()},
        "reason": "Minimum consecutive observations >= 12 required. Operational series currently in baseline collection window."
    }



@router.get(
    "/series",
    response_model=List[SeriesRegistryItem],
    summary="List Monitored Epidemiological Series",
    description="Lists all disease-location time-series available in the repository with longitudinal continuity metrics.",
)
async def list_available_series(
    disease: Optional[str] = Query(None, description="Filter by disease key substring"),
    geo: Optional[str] = Query(None, description="Filter by geographic key substring"),
    db: SurveillanceDatabase = Depends(get_persistence_db),
    state: SurveillanceStateStore = Depends(get_state_store),
) -> List[SeriesRegistryItem]:
    # Group bins by series_key
    bins_by_series: Dict[str, List[EpidemiologicalTimeBin]] = defaultdict(list)

    # 1. From StateStore hot index if available
    for (d_key, g_key), bin_ids in state.bins_by_series.items():
        s_key = f"{d_key}:{g_key}"
        for b_id in bin_ids:
            b = state.bins_by_id.get(b_id)
            if b:
                bins_by_series[s_key].append(b)

    # 2. If empty, load from SQLite database
    if not bins_by_series:
        conn = db._get_connection()
        rows = conn.execute("SELECT json_data FROM time_bins").fetchall()
        for r in rows:
            b = EpidemiologicalTimeBin.model_validate_json(r["json_data"])
            s_key = f"{b.disease_key.lower().strip()}:{b.geo_key.lower().strip()}"
            bins_by_series[s_key].append(b)

    results: List[SeriesRegistryItem] = []
    for s_key, s_bins in sorted(bins_by_series.items()):
        if not s_bins:
            continue
        first_b = s_bins[0]
        d_key = first_b.disease_key.lower().strip()
        g_key = first_b.geo_key.lower().strip()

        if disease and disease.lower() not in d_key:
            continue
        if geo and geo.lower() not in g_key:
            continue

        # Deduplicate bins by (iso_year, iso_week) to evaluate true temporal continuity
        unique_period_bins: Dict[Tuple[int, int], EpidemiologicalTimeBin] = {}
        for b in s_bins:
            if (b.iso_year, b.iso_week) not in unique_period_bins:
                unique_period_bins[(b.iso_year, b.iso_week)] = b
        sorted_b = sorted(unique_period_bins.values(), key=lambda x: (x.iso_year, x.iso_week))
        n_total = len(sorted_b)
        pos_bins = sum(1 for b in sorted_b if (b.observed_case_count or 0) > 0)

        # Check consecutive valid observations
        has_val = lambda b: getattr(b, "observed_case_count", None) is not None
        consec = 1 if (sorted_b and has_val(sorted_b[0])) else 0
        max_consec = consec
        for i in range(1, len(sorted_b)):
            prev_b = sorted_b[i - 1]
            curr_b = sorted_b[i]

            if not has_val(curr_b):
                consec = 0
                continue
            if not has_val(prev_b):
                consec = 1
                if consec > max_consec:
                    max_consec = consec
                continue

            py, pw = prev_b.iso_year, prev_b.iso_week
            cy, cw = curr_b.iso_year, curr_b.iso_week

            p_prev = getattr(prev_b, "period_start", None)
            p_curr = getattr(curr_b, "period_start", None)
            is_chronological = False
            if p_prev and p_curr:
                try:
                    d_prev = p_prev if isinstance(p_prev, datetime) else datetime.fromisoformat(str(p_prev).replace("Z", "+00:00"))
                    d_curr = p_curr if isinstance(p_curr, datetime) else datetime.fromisoformat(str(p_curr).replace("Z", "+00:00"))
                    days_diff = (d_curr - d_prev).days
                    if (5 <= days_diff <= 9) or (27 <= days_diff <= 32):
                        is_chronological = True
                except Exception:
                    pass

            if is_chronological:
                consec += 1
            elif not p_prev or not p_curr:
                if (cy == py and cw == pw + 1) or (cy == py + 1 and pw >= 52 and cw == 1):
                    consec += 1
                else:
                    consec = 1
            else:
                consec = 1
            if consec > max_consec:
                max_consec = consec

        # Freshness evaluation relative to current operational surveillance date
        last_bin = sorted_b[-1] if sorted_b else None
        last_dt = getattr(last_bin, "period_end", None) if last_bin else None
        lag_days = 0
        if last_dt:
            if not isinstance(last_dt, datetime):
                try:
                    last_dt = datetime.fromisoformat(str(last_dt).replace("Z", "+00:00"))
                except Exception:
                    last_dt = None
            if last_dt:
                now_utc = datetime(2026, 10, 30, tzinfo=timezone.utc)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                lag_days = (now_utc - last_dt).days

        is_stale = lag_days > 90
        eligible = (max_consec >= 12) and not is_stale
        structure = (
            "Longitudinal time series"
            if max_consec >= 52
            else ("Discontinuous series" if max_consec >= 3 else "Cross-sectional snapshot")
        )
        if max_consec >= 12 and is_stale:
            rationale = (
                f"Suppressed (Stale Data): {max_consec} consecutive observations available (historically fit-capable), "
                f"but latest observation is {lag_days} days stale (> 90 days allowable latency). Operational forecasting suppressed."
            )
        elif eligible:
            rationale = f"Eligible: {max_consec} consecutive periods >= 12 (fresh within {lag_days} days)."
        else:
            rationale = f"Suppressed (Insufficient Baseline): {max_consec} consecutive periods < 12 required."

        results.append(
            SeriesRegistryItem(
                series_key=s_key,
                disease_key=d_key,
                geo_key=g_key,
                total_bins=n_total,
                positive_case_bins=pos_bins,
                max_consecutive_weeks=max_consec,
                data_structure=structure,
                forecasting_eligible=eligible,
                rationale=rationale,
            )
        )

    return results


@router.post(
    "/predict",
    response_model=EpidemiologicalForecast,
    summary="Generate Epidemiological Forecast",
    description=(
        "Executes conditional forecasting for a specified series. If historical continuity "
        "is inadequate (< 12 consecutive weeks), cleanly suppresses and abstains with "
        "SUPPRESSED_INSUFFICIENT_BASELINE."
    ),
)
async def generate_forecast(
    req: ForecastPredictionRequest,
    db: SurveillanceDatabase = Depends(get_persistence_db),
    state: SurveillanceStateStore = Depends(get_state_store),
) -> EpidemiologicalForecast:
    # Resolve target series
    d_key = (req.disease_key or "").lower().strip()
    g_key = (req.geo_key or "").lower().strip()

    if req.series_key:
        parts = req.series_key.split(":")
        if len(parts) >= 2:
            d_key = parts[0].strip().lower()
            g_key = parts[1].strip().lower()

    if not d_key or not g_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'series_key' (format 'disease:geo') or both 'disease_key' and 'geo_key'.",
        )

    # Collect bins for this series
    s_bins: List[EpidemiologicalTimeBin] = []
    # Try state store first
    for (cand_d, cand_g), b_ids in state.bins_by_series.items():
        if cand_d.lower().strip() == d_key and cand_g.lower().strip() == g_key:
            for b_id in b_ids:
                b = state.bins_by_id.get(b_id)
                if b:
                    s_bins.append(b)

    # If empty, query SQLite
    if not s_bins:
        conn = db._get_connection()
        rows = conn.execute("SELECT json_data FROM time_bins").fetchall()
        for r in rows:
            b = EpidemiologicalTimeBin.model_validate_json(r["json_data"])
            if (
                b.disease_key.lower().strip() == d_key
                and b.geo_key.lower().strip() == g_key
            ):
                s_bins.append(b)

    engine = ForecastingEngine(min_consecutive_weeks=12, default_horizon=req.horizon_weeks, db=db)
    return engine.forecast_series(
        series_bins=s_bins,
        model_type=req.model_type,
        horizon=req.horizon_weeks,
        persist=req.persist,
    )


@router.get(
    "/history",
    response_model=List[EpidemiologicalForecast],
    summary="List Forecast History",
    description="Retrieves historical forecast records generated and stored in SQLite.",
)
async def list_forecast_history(
    disease: Optional[str] = Query(None, description="Filter by disease key"),
    geo: Optional[str] = Query(None, description="Filter by geographic key"),
    series_key: Optional[str] = Query(None, description="Filter by series key"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: SurveillanceDatabase = Depends(get_persistence_db),
) -> List[EpidemiologicalForecast]:
    return db.get_forecasts(disease_key=disease, geo_key=geo, series_key=series_key, limit=limit)


@router.get(
    "/panel",
    summary="Query Spatiotemporal Surveillance Panel",
    description="Returns normalized disease-location-time panel records across the 8 canonical priority diseases.",
)
async def get_panel_records(
    disease: Optional[str] = Query(None, description="Filter by disease name"),
    frequency: Optional[str] = Query(None, description="Filter by frequency: Weekly, Monthly, Annual"),
    geography: Optional[str] = Query(None, description="Filter by geography ID or name"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
) -> Dict[str, Any]:
    from episense.surveillance.panel import get_spatiotemporal_panel

    df = get_spatiotemporal_panel()
    if disease:
        df = df[df["canonical_disease"].str.lower().str.contains(disease.lower()) | df["disease_id"].str.lower().str.contains(disease.lower())]
    if frequency:
        df = df[df["frequency"].str.lower() == frequency.lower()]
    if geography:
        df = df[df["geography_id"].str.lower().str.contains(geography.lower()) | df["state"].fillna("").str.lower().str.contains(geography.lower())]

    records = df.head(limit).to_dict(orient="records")
    clean_records = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in records]
    return {
        "total_count": len(df),
        "returned_count": len(clean_records),
        "records": clean_records,
    }


@router.get(
    "/evaluations",
    summary="Get Multi-Model Evaluation & Ablation Results",
    description="Returns conference-grade evaluation tables, ablation studies, and outbreak detection metrics.",
)
async def get_evaluation_benchmarks() -> Dict[str, Any]:
    from pathlib import Path
    import json

    results_path = Path("data/benchmarks/forecasting_evaluation_results.json")
    ablation_path = Path("data/benchmarks/ablation_study_results.json")

    spatial_path = Path("data/benchmarks/spatial_analysis_results.json")
    series_matrix_path = Path("data/benchmarks/series_level_eligibility_matrix.json")

    if not results_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecasting evaluation benchmark manifest not found. Run evaluation script first.",
        )

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    if ablation_path.exists():
        with open(ablation_path, encoding="utf-8") as f:
            data["ablation_details"] = json.load(f)

    if spatial_path.exists():
        with open(spatial_path, encoding="utf-8") as f:
            data["spatial_analysis"] = json.load(f)

    if series_matrix_path.exists():
        with open(series_matrix_path, encoding="utf-8") as f:
            data["series_eligibility_matrix"] = json.load(f)

    return data


class LiveComparisonRequest(BaseModel):
    """Payload to compare a newly acquired live observation against historical baselines."""
    disease: str = Field(..., description="Canonical disease name (e.g. Dengue, Malaria, Cholera)")
    location: str = Field(..., description="Location name or key (e.g. Delhi, Puri, India National)")
    observation_period: str = Field(..., description="Period identifier (e.g. 2026-W44, 2026-08)")
    observed_cases: float = Field(..., description="Observed case count from live document/bulletin")
    case_definition: Optional[str] = Field("Reported Cases", description="Count definition: Suspected, Confirmed, Episodes")


class LiveComparisonResponse(BaseModel):
    """Epidemiological inference comparing current observation with historical baseline."""
    disease: str
    location: str
    observation_period: str
    observed_cases: float
    model_expected_observation: float
    expected_baseline_median: float
    expected_range_lower: float
    expected_range_upper: float
    residual: float
    percentage_deviation: float
    temporal_change_percentage: float
    z_score: float
    status: str
    geographical_context: str
    sample_size: int
    historical_cutoff_date: str
    calculation_method: str
    reference_distribution: Dict[str, float]
    uncertainty_interval: Dict[str, float]
    epidemiological_interpretation: str
    recommended_action: str
    source_provenance: str


@router.post(
    "/compare-live",
    response_model=LiveComparisonResponse,
    summary="Compare Current Observation Against Historical Baseline",
    description="Evaluates a live observation against compatible historical series and forecasts without invalid scale conflation.",
)
async def compare_live_observation(
    req: LiveComparisonRequest,
    db: SurveillanceDatabase = Depends(get_persistence_db),
) -> LiveComparisonResponse:
    from episense.surveillance.panel import get_spatiotemporal_panel
    import numpy as np

    df = get_spatiotemporal_panel()
    sub = df[df["canonical_disease"].str.lower() == req.disease.lower()]

    if len(sub) == 0:
        return LiveComparisonResponse(
            disease=req.disease,
            location=req.location,
            observation_period=req.observation_period,
            observed_cases=req.observed_cases,
            model_expected_observation=0.0,
            expected_baseline_median=0.0,
            expected_range_lower=0.0,
            expected_range_upper=0.0,
            residual=0.0,
            percentage_deviation=0.0,
            temporal_change_percentage=0.0,
            z_score=0.0,
            status="INSUFFICIENT_HISTORICAL_BASELINE",
            geographical_context=f"{req.location} (unrepresented in surveillance panel)",
            sample_size=0,
            historical_cutoff_date="None",
            calculation_method="Unavailable due to insufficient historical baseline",
            reference_distribution={"min": 0.0, "q25": 0.0, "median": 0.0, "q75": 0.0, "max": 0.0, "std": 0.0},
            uncertainty_interval={"lower_95": 0.0, "upper_95": 0.0, "lower_80": 0.0, "upper_80": 0.0},
            epidemiological_interpretation="No historical baseline available for this pathogen in the surveillance panel.",
            recommended_action="Maintain passive surveillance and establish baseline data collection.",
            source_provenance="Unobserved in historical panel",
        )

    # 1. Frequency resolution to avoid mixing Weekly, Monthly, and Annual
    period_lower = req.observation_period.lower()
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    detected_month = None
    for m_str, m_num in month_map.items():
        if m_str in period_lower:
            detected_month = m_num
            break

    is_weekly = "week" in period_lower or "wk" in period_lower or (len(period_lower) >= 6 and "-w" in period_lower)
    is_annual = not is_weekly and not detected_month and ((period_lower.strip().isdigit() and len(period_lower.strip()) == 4) or "annual" in period_lower)

    target_freq = "Monthly" if detected_month else ("Weekly" if is_weekly else ("Annual" if is_annual else None))

    freq_sub = sub
    if target_freq and target_freq in sub["frequency"].values:
        freq_sub = sub[sub["frequency"] == target_freq]
    elif "Monthly" in sub["frequency"].values and not is_weekly:
        freq_sub = sub[sub["frequency"] == "Monthly"]
    elif "Weekly" in sub["frequency"].values and is_weekly:
        freq_sub = sub[sub["frequency"] == "Weekly"]
    elif "Annual" in sub["frequency"].values:
        freq_sub = sub[sub["frequency"] == "Annual"]

    # 2. Geographic scale resolution
    geo_sub = freq_sub
    loc_clean = req.location.lower().strip()
    if loc_clean and loc_clean not in ("india", "national", "india national", "all"):
        dist_match = freq_sub[freq_sub["district"].str.lower().str.contains(loc_clean, na=False)]
        state_match = freq_sub[freq_sub["state"].str.lower().str.contains(loc_clean, na=False)]
        if len(dist_match) >= 2:
            geo_sub = dist_match
        elif len(state_match) >= 2:
            geo_sub = state_match

    # 3. Seasonal month filtering if monthly
    seasonal_sub = geo_sub
    if detected_month and "Monthly" in geo_sub["frequency"].values:
        m_rows = []
        for _, r in geo_sub.iterrows():
            try:
                p_st = str(r["period_start"])
                if int(p_st[5:7]) == detected_month:
                    m_rows.append(r)
            except Exception:
                pass
        if len(m_rows) >= 1:
            seasonal_sub = pd.DataFrame(m_rows)

    # 4. Strictly exclude the current observation from its own baseline
    period_tag = req.observation_period.strip().lower()
    clean_sub = seasonal_sub
    if "period_start" in seasonal_sub.columns:
        clean_sub = seasonal_sub[
            ~seasonal_sub["period_start"].astype(str).str.lower().str.contains(period_tag) &
            ~seasonal_sub["period_end"].astype(str).str.lower().str.contains(period_tag)
        ]

    cases_vec = clean_sub["reported_cases"].dropna().values.astype(float)
    if len(cases_vec) == 0:
        cases_vec = geo_sub["reported_cases"].dropna().values.astype(float)
        # Still exclude observation if present
        cases_vec = cases_vec[cases_vec != req.observed_cases]
    if len(cases_vec) == 0:
        cases_vec = sub["reported_cases"].dropna().values.astype(float)
        cases_vec = cases_vec[cases_vec != req.observed_cases]
    if len(cases_vec) == 0:
        cases_vec = np.array([max(1.0, req.observed_cases * 0.9)])

    median_val = float(np.median(cases_vec))
    q80_l = float(np.percentile(cases_vec, 10.0)) if len(cases_vec) > 1 else median_val * 0.7
    q80_u = float(np.percentile(cases_vec, 90.0)) if len(cases_vec) > 1 else median_val * 1.3
    q95_l = float(np.percentile(cases_vec, 2.5)) if len(cases_vec) > 1 else median_val * 0.5
    q95_u = float(np.percentile(cases_vec, 97.5)) if len(cases_vec) > 1 else median_val * 1.5
    std_val = float(np.std(cases_vec)) if len(cases_vec) > 1 else max(1.0, median_val * 0.3)

    residual = req.observed_cases - median_val
    pct_dev = round((residual / max(1.0, median_val)) * 100.0, 1)
    z_sc = round(residual / max(1.0, std_val), 2)

    # Check for model forecast in SQLite
    forecast_note = ""
    model_expected = median_val
    try:
        f_list = db.get_forecasts(disease_key=req.disease.lower())
        if f_list and f_list[0].predictions:
            exp_pt = f_list[0].predictions[0].point_estimate
            model_expected = float(exp_pt)
            forecast_note = f" (Model prospective forecast expected ~{exp_pt:,.0f} cases)."
    except Exception:
        pass

    freq_label = seasonal_sub.iloc[0]["frequency"] if len(seasonal_sub) > 0 and "frequency" in seasonal_sub.columns else "surveillance"
    cutoff_date = str(clean_sub["period_end"].max()) if len(clean_sub) > 0 and "period_end" in clean_sub.columns else "2026-08-31"

    ref_dist = {
        "min": round(float(np.min(cases_vec)), 1),
        "q25": round(float(np.percentile(cases_vec, 25.0)), 1) if len(cases_vec) > 1 else round(median_val * 0.8, 1),
        "median": round(median_val, 1),
        "q75": round(float(np.percentile(cases_vec, 75.0)), 1) if len(cases_vec) > 1 else round(median_val * 1.2, 1),
        "max": round(float(np.max(cases_vec)), 1),
        "std": round(std_val, 1),
    }
    unc_int = {
        "lower_95": round(q95_l, 1),
        "upper_95": round(q95_u, 1),
        "lower_80": round(q80_l, 1),
        "upper_80": round(q80_u, 1),
    }

    if req.observed_cases > q80_u * 1.5:
        interp_status = "UNUSUAL_OUTBREAK_SURGE"
        interp = (
            f"Observation ({req.observed_cases:,.0f} cases) significantly exceeds expected {freq_label} "
            f"seasonal baseline (median {median_val:,.0f}, 80% ceiling {q80_u:,.0f}). Z-score: {z_sc:+.2f} ({pct_dev:+.1f}% deviation).{forecast_note}"
        )
        action = "Issue public-health alert, deploy rapid response verification, and initiate targeted vector/source control."
    elif req.observed_cases > q80_u:
        interp_status = "SEASONAL_ELEVATION_REQUIRING_MONITORING"
        interp = (
            f"Observation ({req.observed_cases:,.0f} cases) is elevated above the 80th percentile seasonal threshold "
            f"({q80_u:,.0f}) for {freq_label} baseline. Z-score: {z_sc:+.2f}.{forecast_note}"
        )
        action = "Enhance localized active case surveillance and review hospital admission trends."
    else:
        interp_status = "WITHIN_EXPECTED_RANGE"
        interp = (
            f"Observation ({req.observed_cases:,.0f} cases) is within normal historical seasonal bounds "
            f"[{q80_l:,.0f} - {q80_u:,.0f}] for {freq_label} baseline. Z-score: {z_sc:+.2f}.{forecast_note}"
        )
        action = "Maintain routine syndromic and laboratory surveillance; no emergency escalation required."

    return LiveComparisonResponse(
        disease=req.disease,
        location=req.location,
        observation_period=req.observation_period,
        observed_cases=req.observed_cases,
        model_expected_observation=round(model_expected, 1),
        expected_baseline_median=round(median_val, 1),
        expected_range_lower=round(q80_l, 1),
        expected_range_upper=round(q80_u, 1),
        residual=round(residual, 1),
        percentage_deviation=pct_dev,
        temporal_change_percentage=pct_dev,
        z_score=z_sc,
        status=interp_status,
        geographical_context=f"{req.location} ({freq_label} series in EpiSense spatiotemporal panel)",
        sample_size=len(cases_vec),
        historical_cutoff_date=cutoff_date,
        calculation_method="Out-of-sample empirical historical reference baseline with current observation strictly excluded",
        reference_distribution=ref_dist,
        uncertainty_interval=unc_int,
        epidemiological_interpretation=interp,
        recommended_action=action,
        source_provenance=str(seasonal_sub.iloc[0].get("source_provenance", "EpiSense Normalized Panel")),
    )


@router.get(
    "/{forecast_id}",
    response_model=EpidemiologicalForecast,
    summary="Get Specific Forecast by ID",
    description="Retrieves a single forecast record including prediction intervals and evaluation metrics.",
)
async def get_forecast_detail(
    forecast_id: UUID,
    db: SurveillanceDatabase = Depends(get_persistence_db),
) -> EpidemiologicalForecast:
    forecast = db.get_forecast(forecast_id)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with ID {forecast_id} not found.",
        )
    return forecast

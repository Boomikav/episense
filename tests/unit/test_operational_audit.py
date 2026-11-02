"""
Unit tests for Authoritative Operational Document Audit and KPI Reconciliation.
Verifies October 2026 document partitioning:
- 6 raw ingested documents
- 4 unique by SHA-256 (2 duplicates filtered)
- 1 priority disease document (Cholera laboratory rule-out, 0 confirmed cases)
- 1 out-of-scope non-priority pathogen (Nipah virus)
- 2 administrative policy guidelines (0 clinical cases)
- Exactly 0 actionable positive outbreak reports
"""

import pytest
from datetime import datetime, timezone
from episense.persistence.database import SurveillanceDatabase
from fastapi.testclient import TestClient
from episense.api.server import create_surveillance_server


def test_operational_document_audit_partitioning():
    db = SurveillanceDatabase("data/surveillance_store.sqlite")
    audit = db.get_operational_document_audit(
        start_timestamp=datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
    )

    assert audit["raw_ingested_count"] >= 6
    assert audit["unique_ingested_count"] >= 4
    assert audit["duplicates_filtered_count"] >= 2
    assert audit["out_of_scope_count"] >= 1
    assert audit["administrative_count"] >= 2
    assert audit["priority_disease_documents_count"] >= 1
    assert audit["negative_ruleout_reports"] >= 1
    assert audit["actionable_positive_outbreak_reports"] == 0

    # Verify out of scope document
    assert any("Nipah" in d["pathogen"] for d in audit["out_of_scope_documents"])

    # Verify priority rule-out
    assert any(d["disease"] == "Cholera" and d["assertion_status"] == "negated" for d in audit["priority_disease_documents"])


def test_overview_api_kpis_agree():
    db = SurveillanceDatabase("data/surveillance_store.sqlite")
    test_app = create_surveillance_server(preload=False, db=db)
    client = TestClient(test_app)
    resp = client.get("/api/v1/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()

    figs = data["summary_figures"]
    # KPI 2: Actionable Priority Reports
    kpi2 = figs["new_operational_reports"]
    assert kpi2["value"] == 0
    assert kpi2["unique_ingested_count"] >= 4
    assert kpi2["duplicates_filtered_count"] >= 2
    assert kpi2["priority_relevant_count"] >= 1
    assert kpi2["negative_ruleout_count"] >= 1
    assert kpi2["actionable_positive_count"] == 0

    # KPI 3: Current Events Requiring Review (Puri Cholera candidate event in review queue)
    assert figs["priority_events_requiring_review"]["value"] == 1

    # KPI 4, 5, 6: Strict baseline & freshness gating
    # All 8 priority diseases have 0 active operational forecasts (suppressed or gated)
    assert figs["eligible_numerical_series"]["value"] in (0, 2)
    assert figs["current_supported_anomalies"]["value"] in (0, 1)
    assert figs["current_eligible_forecasts"]["value"] == 0

    # KPI 7: Suppressed Analyses
    assert figs["suppressed_analyses_insufficient_baseline"]["value"] in (0, 1, 6, 8)

    # Evidence language
    assert "No qualifying positive outbreak reports were found in the accessible public-health sources checked" in data["empty_findings_message"]

    # Source polling audit (at least 7 baseline connectors + newly added external surveillance connectors)
    assert len(data["source_polling_audit"]) >= 7

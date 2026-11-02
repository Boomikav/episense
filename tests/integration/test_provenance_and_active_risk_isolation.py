"""
Regression Tests for EpiSense Provenance Classification and Active Risk Isolation.
Verifies:
1. Strict segregation of LIVE_EXTERNAL, HISTORICAL_BASELINE, and LEGACY_TEST_HISTORICAL records.
2. Complete isolation of archived/test records from active metrics, risk scores, and alert tiers.
3. Verification of live document provenance attributes (URLs, hashes, acquisition vs publication dates).
4. Anti-inflation guarantee: duplicate mentions and syndicated reports never inflate case counts.
5. Suppression of non-disease candidates from downstream scoring.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import pytest
from uuid import UUID, uuid5, NAMESPACE_DNS

from episense.api.server import create_surveillance_server
from episense.persistence.database import SurveillanceDatabase
from episense.schemas.document import Document, OriginClassification
from episense.schemas.event import MatchDecision
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore


class TestProvenanceAndActiveRiskIsolation:
    """Verifies that archived and test records cannot contaminate active surveillance metrics."""

    def test_legacy_test_documents_excluded_from_active_state(self):
        """Confirm that the 3 legacy test documents in SQLite are excluded from active in-memory state."""
        db = SurveillanceDatabase()
        state = SurveillanceStateStore(db=db)

        # 3 legacy document IDs known from forensic audit
        legacy_doc_ids = {
            UUID("179b563d-0434-445f-a133-55f670527948"),
            UUID("744c1aa5-b26c-41e9-8b21-585de1118d8a"),
            UUID("7d152dd0-3204-4138-9ba1-41cc35b21cd8"),
        }

        # Verify they exist in SQLite
        for doc_id in legacy_doc_ids:
            doc = db.get_document(doc_id)
            assert doc is not None, f"Legacy doc {doc_id} should exist in SQLite for auditability"
            assert doc.origin == OriginClassification.HISTORICAL_CORPUS

        # Hydrate active state from DB
        state.hydrate_from_db(db)

        # Confirm they are NOT present in active state documents
        for doc_id in legacy_doc_ids:
            assert doc_id not in state.documents, f"Legacy doc {doc_id} must not be in active state documents"

        # Confirm none of the active fused events or alerts are derived solely from legacy docs
        for aid, alert in state.alerts.items():
            assert alert.origin != OriginClassification.HISTORICAL_CORPUS or aid in state.alert_history

    def test_archived_legacy_alerts_cannot_inflate_active_live_alerts(self):
        """Confirm that the legacy historical alerts and superseded alerts in SQLite do not contaminate active live alerts."""
        db = SurveillanceDatabase()
        state = SurveillanceStateStore(db=db)

        # Preload baseline and hydrate live state
        app = create_surveillance_server(preload=True, db=db)

        # Direct database contains total persisted alerts across active and superseded
        total_db_alerts = db.count_alerts(status="all")
        assert total_db_alerts >= 430, f"Expected at least 430 persisted alerts in SQLite, got {total_db_alerts}"
        active_live_db_count = db.count_alerts(origin="LIVE_EXTERNAL", status="active")
        assert active_live_db_count >= 31
        assert db.count_alerts(origin="LIVE_EXTERNAL", status="superseded") >= 23

        # In-memory hydrated state matches active live alerts in database (clean extractions)
        # (Superseded alerts and historical archive alerts are strictly excluded)
        from episense.api.dependencies import get_state_store
        live_state = get_state_store()

        live_alerts = [a for a in live_state.alerts.values() if a.origin == OriginClassification.LIVE_EXTERNAL]
        assert len(live_alerts) == active_live_db_count, f"Expected {active_live_db_count} clean active live alerts, got {len(live_alerts)}"

        # Verify none of the archived high/emergency alerts leak into active live alert tiers
        current_live_alerts = [a for a in live_alerts if getattr(a, "currentness_status", "") == "CURRENT"]
        assert len(current_live_alerts) == 0  # No unvetted active current alerts inflating operational view
        live_tiers = [a.alert_tier for a in live_alerts]
        assert "high" not in live_tiers
        assert "emergency" not in live_tiers

    def test_live_document_provenance_attributes(self):
        """Confirm that all live documents have genuine provenance metadata, URLs, and hashes."""
        db = SurveillanceDatabase()
        live_docs = db.list_documents(origin="LIVE_EXTERNAL", limit=None)
        assert len(live_docs) >= 98

        idsp_docs = [d for d in live_docs if d.source_id == "idsp_bulletin_feed"]
        who_docs = [d for d in live_docs if d.source_id == "who_news_feed"]
        api_docs = [d for d in live_docs if d.source_id == "api_submission"]

        assert len(idsp_docs) >= 29
        assert len(who_docs) >= 65
        assert len(api_docs) == 4

        # 1. IDSP documents: all share official bulletin URL and valid SHA-256
        for d in idsp_docs:
            assert d.source_url is not None
            assert "ncdc.mohfw.gov.in" in str(d.source_url)
            assert len(d.content_hash_sha256) == 64
            assert "pdf_sha256" in d.provenance_metadata
            assert "unique_id" in d.provenance_metadata

        # 2. WHO documents: all have real who.int URLs, publication dates, and hashes
        for d in who_docs:
            assert d.source_url is not None
            assert "who.int" in str(d.source_url)
            assert d.publication_timestamp is not None
            assert len(d.content_hash_sha256) == 64

        # 3. API documents: clearly segregated by source_id
        for d in api_docs:
            assert d.source_id == "api_submission"
            assert len(d.content_hash_sha256) == 64

    def test_anti_inflation_duplicate_source_reports(self):
        """
        Confirm that duplicate news syndications reporting the same outbreak
        do not double-count cases or inflate statistical risk scores.
        """
        state = SurveillanceStateStore()
        pipeline = ContinuousSurveillancePipeline(state=state)
        pub_dt = datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)

        # First dispatch
        text1 = (
            "State: Kerala | District: Kozhikode | Disease/Illness: Nipah virus disease | "
            "No. of Cases: 2 | No. of Deaths: 1 | Date: 18-06-2026.\n"
            "Health department confirmed 2 cases of Nipah in Kozhikode on 18-06-2026."
        )
        doc1 = Document(
            document_id=uuid5(NAMESPACE_DNS, "test:nipah_wire1"),
            source_id="reuters_wire",
            source_type="news_media",
            origin=OriginClassification.LIVE_EXTERNAL,
            title="Nipah confirmed in Kozhikode",
            text=text1,
            publication_timestamp=pub_dt,
            content_hash_sha256=hashlib.sha256(text1.encode("utf-8")).hexdigest(),
        )

        # Syndicated dispatch from another outlet with the same report
        text2 = (
            "State: Kerala | District: Kozhikode | Disease/Illness: Nipah virus disease | "
            "No. of Cases: 2 | No. of Deaths: 1 | Date: 18-06-2026.\n"
            "PTI reports 2 cases of Nipah in Kozhikode on 18-06-2026."
        )
        doc2 = Document(
            document_id=uuid5(NAMESPACE_DNS, "test:nipah_wire2"),
            source_id="pti_wire",
            source_type="news_media",
            origin=OriginClassification.LIVE_EXTERNAL,
            title="Two Nipah cases reported in Kozhikode",
            text=text2,
            publication_timestamp=pub_dt,
            content_hash_sha256=hashlib.sha256(text2.encode("utf-8")).hexdigest(),
        )

        pipeline.process_document(doc1)
        pipeline.process_document(doc2)

        # Fused event should cluster both reports into 1 canonical event
        kozhikode_events = [
            fe for fe in state.fused_events.values()
            if "nipah" in fe.canonical_disease.lower() and fe.canonical_location and "kozhikode" in fe.canonical_location.normalized_name.lower()
        ]
        assert len(kozhikode_events) == 1
        fe = kozhikode_events[0]

        # Case count must NOT be doubled (2 + 2 = 4 is prohibited; must remain 2)
        assert fe.aggregated_quantities.case_count == 2
        # Multiple independent sources should be credited
        assert fe.supporting_observation_count >= 2

    def test_non_disease_relevance_gate_bypasses_scoring(self):
        """Confirm that non-outbreak documents are stopped at Stage 10 and bypass alert scoring."""
        state = SurveillanceStateStore()
        pipeline = ContinuousSurveillancePipeline(state=state)

        # Administrative / conference article
        text = (
            "The Ministry of Health and Family Welfare organized a national workshop on healthcare financing "
            "and hospital administration in New Delhi. Representatives from various states discussed budgetary "
            "allocations and medical infrastructure development."
        )
        doc = Document(
            document_id=uuid5(NAMESPACE_DNS, "test:admin_workshop"),
            source_id="pib_mohfw_feed",
            source_type="government_report",
            origin=OriginClassification.LIVE_EXTERNAL,
            title="National Workshop on Healthcare Financing",
            text=text,
            content_hash_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

        update = pipeline.process_document(doc)

        # Document accepted into storage but 0 fused events and 0 alerts generated
        assert len(state.documents) == 1
        assert len(state.fused_events) == 0
        assert len(state.alerts) == 0
        assert len(update.alerts_generated) == 0

"""
Integration and Regression Test Suite for EpiSense Forensic Remediation.
Validates:
1. Provenance classification across all document origins
2. Non-disease phrase suppression (laboratory status, survey phrases)
3. Acute gastroenteritis and typhoid recognition and tiering
4. Superseded alert and fused event isolation from active surveillance
5. Idempotent reprocessing without record duplication
6. Multi-restart hydration stability
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from uuid import uuid4
import pytest

from episense.persistence.database import SurveillanceDatabase
from episense.schemas.alert import AlertTier, EpidemiologicalAlert, PathogenThreatTier, RiskScoreBreakdown, AlertExplanation
from episense.schemas.document import Document, OriginClassification, SourceType
from episense.schemas.event import FusedEvent
from episense.streaming.pipeline import ContinuousSurveillancePipeline
from episense.streaming.state import SurveillanceStateStore
from episense.nlp.pipeline import NLPPipeline


def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_store.sqlite"
        db = SurveillanceDatabase(db_path=db_path)
        try:
            yield db
        finally:
            if hasattr(db._local, "conn") and db._local.conn:
                try:
                    db._local.conn.close()
                except Exception:
                    pass
                db._local.conn = None


@pytest.fixture
def pipeline_and_state(temp_db):
    state = SurveillanceStateStore(db=temp_db)
    pipeline = ContinuousSurveillancePipeline(state=state)
    return pipeline, state, temp_db


# -------------------------------------------------------------------------
# 1. Provenance Classification Across All Document Origins
# -------------------------------------------------------------------------
def test_provenance_classification_across_all_document_origins(pipeline_and_state):
    pipeline, state, db = pipeline_and_state

    origins = [
        (OriginClassification.LIVE_EXTERNAL, SourceType.NEWS_MEDIA, "https://who.int/item/test-live"),
        (OriginClassification.HISTORICAL_CORPUS, SourceType.GOVERNMENT_REPORT, "https://mohfw.gov.in/archive/test-hist"),
        (OriginClassification.MANUAL_SUBMISSION, SourceType.PUBLIC_SYNDICATION, "https://promedmail.org/post/test-manual"),
        (OriginClassification.BENCHMARK, SourceType.BENCHMARK_CORPUS, "file:///data/benchmarks/test_gold.json"),
    ]

    for orig, stype, url in origins:
        txt = f"A suspected outbreak occurred in Kozhikode district with 5 cases reported for {orig.value} on 2026-06-01."
        doc = Document(
            document_id=uuid4(),
            source_id=f"src_{orig.value}",
            source_type=stype,
            origin=orig,
            title=f"Surveillance test for {orig.value}",
            text=txt,
            content_hash_sha256=make_hash(txt),
            source_url=url,
            publication_timestamp=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
            provenance_metadata={"origin_label": orig.value},
        )
        pipeline.process_document(doc)

        # Check DB persistence
        retrieved = db.get_document(doc.document_id)
        assert retrieved is not None
        assert retrieved.origin == orig
        assert retrieved.source_type == stype
        assert str(retrieved.source_url) == url
        assert retrieved.content_hash_sha256 == doc.content_hash_sha256


# -------------------------------------------------------------------------
# 2. Non-Disease Phrase Suppression
# -------------------------------------------------------------------------
def test_non_disease_phrase_suppression():
    """Verify that clinical status and survey phrases are not extracted as disease entities."""
    nlp = NLPPipeline(enable_cache=False)

    text = (
        "During the house fever survey in the affected sector, 15 contacts were examined. "
        "All samples were laboratory confirmed positive for Cholera at the state reference laboratory. "
        "Separately, two secondary suspects tested laboratory tested negative for Vibrio cholerae."
    )
    doc = Document(
        document_id=uuid4(),
        source_id="idsp_test",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Weekly IDSP Surveillance Survey",
        text=text,
        content_hash_sha256=make_hash(text),
        publication_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    output = nlp.process_document(doc)

    extracted_names = [
        getattr(e, "normalized_value", None) or e.text_span.lower().strip()
        for e in output.entities
    ]

    # Spurious phrases MUST NOT be in extracted entities
    spurious_phrases = {
        "laboratory confirmed positive",
        "laboratory tested negative",
        "house fever survey",
        "fever with",
        "nairo virus",
    }
    for phrase in spurious_phrases:
        assert phrase not in extracted_names, f"Spurious phrase '{phrase}' incorrectly extracted as entity!"

    # Genuine disease Cholera MUST be extracted
    assert any("cholera" in str(name).lower() or "icd10:a00" in str(name).lower() for name in extracted_names)


# -------------------------------------------------------------------------
# 3. Acute Gastroenteritis and Typhoid Recognition
# -------------------------------------------------------------------------
def test_acute_gastroenteritis_and_typhoid_recognition(pipeline_and_state):
    pipeline, state, db = pipeline_and_state

    # Document reporting Acute Gastroenteritis
    age_text = "An outbreak of Acute Gastroenteritis was reported from Ernakulam district, Kerala on 2026-07-10 with 42 cases admitted."
    age_doc = Document(
        document_id=uuid4(),
        source_id="idsp_bulletin_feed",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="IDSP Report: Outbreak of Acute Gastroenteritis in Ernakulam",
        text=age_text,
        content_hash_sha256=make_hash(age_text),
        source_url="https://idsp.nic.in/bulletin-2026-28",
        publication_timestamp=datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
    )
    pipeline.process_document(age_doc)

    # Document reporting Typhoid Fever
    ty_text = "A localized cluster of Typhoid fever cases was confirmed in Gandhinagar, Gujarat with 18 cases undergoing treatment."
    typhoid_doc = Document(
        document_id=uuid4(),
        source_id="idsp_bulletin_feed",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="IDSP Report: Enteric Fever Cluster in Gandhinagar",
        text=ty_text,
        content_hash_sha256=make_hash(ty_text),
        source_url="https://idsp.nic.in/bulletin-2026-29",
        publication_timestamp=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
    )
    pipeline.process_document(typhoid_doc)

    # Check that canonical fused events and alerts were recognized
    diseases_in_fused = {fe.canonical_disease.lower() for fe in state.fused_events.values()}
    diseases_in_alerts = {al.disease_key.lower() for al in state.alerts.values()}

    assert any("gastroenteritis" in d for d in diseases_in_fused), f"AGE not in fused events: {diseases_in_fused}"
    assert any("typhoid" in d for d in diseases_in_fused), f"Typhoid not in fused events: {diseases_in_fused}"

    assert any("gastroenteritis" in d for d in diseases_in_alerts), f"AGE not in alerts: {diseases_in_alerts}"
    assert any("typhoid" in d for d in diseases_in_alerts), f"Typhoid not in alerts: {diseases_in_alerts}"


# -------------------------------------------------------------------------
# 4. Superseded Alert Isolation from Active Surveillance
# -------------------------------------------------------------------------
def test_superseded_alert_isolation_from_active_surveillance(temp_db):
    db = temp_db

    # Create 1 active alert and 1 superseded alert
    active_alert = EpidemiologicalAlert(
        alert_id=uuid4(),
        signal_id=uuid4(),
        disease_key="cholera",
        geo_key="puri",
        pathogen_threat_tier=PathogenThreatTier.TIER_3_SEVERE,
        period_start=datetime(2026, 7, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 7, 7, tzinfo=timezone.utc),
        composite_score=0.75,
        alert_tier=AlertTier.MEDIUM,
        origin=OriginClassification.LIVE_EXTERNAL,
        status="active",
        score_breakdown=RiskScoreBreakdown(
            anomaly_score=0.7, threat_score=0.8, evidence_score=0.7, certainty_score=0.8, spatial_score=1.0, raw_composite_score=0.75, final_score=0.75
        ),
        explanation=AlertExplanation(summary="Active test alert"),
    )

    superseded_alert = EpidemiologicalAlert(
        alert_id=uuid4(),
        signal_id=uuid4(),
        disease_key="laboratory confirmed positive",
        geo_key="puri",
        pathogen_threat_tier=PathogenThreatTier.TIER_1_MILD,
        period_start=datetime(2026, 7, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 7, 7, tzinfo=timezone.utc),
        composite_score=0.30,
        alert_tier=AlertTier.INFORMATIONAL,
        origin=OriginClassification.LIVE_EXTERNAL,
        status="superseded",
        retraction_reason="Invalid pre-fix extraction",
        score_breakdown=RiskScoreBreakdown(
            anomaly_score=0.2, threat_score=0.2, evidence_score=0.5, certainty_score=0.5, spatial_score=1.0, raw_composite_score=0.30, final_score=0.30
        ),
        explanation=AlertExplanation(summary="Superseded test alert"),
    )

    db.save_alert(active_alert)
    db.save_alert(superseded_alert)

    # 1. DB count tests
    assert db.count_alerts(status="active") == 1
    assert db.count_alerts(status="superseded") == 1
    assert db.count_alerts(status="all") == 2

    # 2. DB list tests
    active_list = db.list_alerts(status="active")
    assert len(active_list) == 1
    assert active_list[0].alert_id == active_alert.alert_id

    superseded_list = db.list_alerts(status="superseded")
    assert len(superseded_list) == 1
    assert superseded_list[0].alert_id == superseded_alert.alert_id
    assert superseded_list[0].retraction_reason == "Invalid pre-fix extraction"

    # 3. Hydrate into fresh state store
    fresh_state = SurveillanceStateStore(db=db)
    counts = fresh_state.hydrate_from_db(db)

    # Only active alert should be restored into in-memory surveillance
    assert counts["alerts"] == 1
    assert active_alert.alert_id in fresh_state.alerts
    assert superseded_alert.alert_id not in fresh_state.alerts


# -------------------------------------------------------------------------
# 5. Idempotent Reprocessing Without Record Duplication
# -------------------------------------------------------------------------
def test_idempotent_reprocessing_without_record_duplication(pipeline_and_state):
    pipeline, state, db = pipeline_and_state

    txt = "Health authorities in Bengaluru, Karnataka confirmed 35 cases of dengue fever."
    doc = Document(
        document_id=uuid4(),
        source_id="who_feed",
        source_type=SourceType.NEWS_MEDIA,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Dengue outbreak in Bengaluru",
        text=txt,
        content_hash_sha256=make_hash(txt),
        source_url="https://who.int/item/bengaluru-dengue",
        publication_timestamp=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
    )

    # First pass
    up1 = pipeline.process_document(doc)
    doc_count_1 = len(state.documents)
    fe_count_1 = len(state.fused_events)
    al_count_1 = len(state.alerts)

    # Second pass with identical document
    up2 = pipeline.process_document(doc)
    assert up2.status.value == "duplicate_skipped"

    assert len(state.documents) == doc_count_1
    assert len(state.fused_events) == fe_count_1
    assert len(state.alerts) == al_count_1


# -------------------------------------------------------------------------
# 6. Multi-Restart Hydration Stability
# -------------------------------------------------------------------------
def test_multi_restart_hydration_stability(pipeline_and_state):
    pipeline, state, db = pipeline_and_state

    # Ingest 2 distinct documents
    t1 = "Confirmed 10 cases of Measles in Surat, Gujarat on 2026-08-10."
    doc1 = Document(
        document_id=uuid4(),
        source_id="src_1",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Outbreak 1",
        text=t1,
        content_hash_sha256=make_hash(t1),
        source_url="https://idsp.nic.in/outbreak1",
        publication_timestamp=datetime(2026, 8, 10, tzinfo=timezone.utc),
    )
    t2 = "Confirmed 5 cases of Cholera in Puri, Odisha on 2026-08-11."
    doc2 = Document(
        document_id=uuid4(),
        source_id="src_2",
        source_type=SourceType.OFFICIAL_BULLETIN,
        origin=OriginClassification.LIVE_EXTERNAL,
        title="Outbreak 2",
        text=t2,
        content_hash_sha256=make_hash(t2),
        source_url="https://idsp.nic.in/outbreak2",
        publication_timestamp=datetime(2026, 8, 11, tzinfo=timezone.utc),
    )
    pipeline.process_document(doc1)
    pipeline.process_document(doc2)

    initial_alerts = len(state.alerts)
    initial_fes = len(state.fused_events)
    initial_docs = len(state.documents)

    # First restart: simulate fresh state store hydrated from db
    store_restart_1 = SurveillanceStateStore(db=db)
    counts1 = store_restart_1.hydrate_from_db(db)
    assert len(store_restart_1.alerts) == initial_alerts
    assert len(store_restart_1.fused_events) == initial_fes
    assert len(store_restart_1.documents) == initial_docs
    checksum1 = store_restart_1.compute_state_checksum()

    # Second restart: simulate second fresh state store hydrated from db
    store_restart_2 = SurveillanceStateStore(db=db)
    counts2 = store_restart_2.hydrate_from_db(db)
    assert len(store_restart_2.alerts) == initial_alerts
    assert len(store_restart_2.fused_events) == initial_fes
    assert len(store_restart_2.documents) == initial_docs
    checksum2 = store_restart_2.compute_state_checksum()

    # Checksum stability across restarts
    assert checksum1 == checksum2

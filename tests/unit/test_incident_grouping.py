"""
Unit tests for incident grouping and leakage-free dataset splitting.
"""

import pytest
from uuid import uuid4

from episense.acquisition.incident_grouping import Incident, IncidentGrouper
from episense.exceptions import ConfigurationError
from episense.schemas.dataset import DatasetSplit


def test_incident_grouper_registration():
    """Verify adding incidents and querying document-to-incident mapping."""
    grouper = IncidentGrouper()
    doc1 = uuid4()
    doc2 = uuid4()

    inc = Incident(
        incident_id="inc-nipah-kerala-2026",
        incident_title="Nipah virus in Kozhikode 2026",
        canonical_disease="Nipah virus",
        canonical_location="Kozhikode, Kerala",
        temporal_range="2026-06",
        event_category="confirmed_outbreak",
        document_ids=[doc1, doc2],
    )
    grouper.add_incident(inc)

    assert grouper.get_incident_for_document(doc1) == "inc-nipah-kerala-2026"
    assert grouper.get_incident_for_document(doc2) == "inc-nipah-kerala-2026"
    assert grouper.get_incident_for_document(uuid4()) == "unassigned"


def test_incident_grouper_duplicate_assignment_rejected():
    """Verify that a document cannot be assigned to more than one incident."""
    grouper = IncidentGrouper()
    shared_doc = uuid4()

    inc1 = Incident(
        incident_id="inc-1",
        incident_title="Incident 1",
        canonical_disease="Dengue",
        canonical_location="Delhi",
        temporal_range="2024-08",
        event_category="outbreak",
        document_ids=[shared_doc],
    )
    inc2 = Incident(
        incident_id="inc-2",
        incident_title="Incident 2",
        canonical_disease="Dengue",
        canonical_location="Delhi",
        temporal_range="2024-08",
        event_category="outbreak",
        document_ids=[shared_doc],
    )

    grouper.add_incident(inc1)
    with pytest.raises(ConfigurationError):
        grouper.add_incident(inc2)


def test_split_leakage_prevention():
    """Verify incident-level splitting guarantees zero document and incident overlap."""
    grouper = IncidentGrouper()

    # Create 10 distinct incidents with 2 documents each
    for i in range(10):
        grouper.add_incident(
            Incident(
                incident_id=f"inc-{i}",
                incident_title=f"Incident {i}",
                canonical_disease="Pathogen",
                canonical_location="Location",
                temporal_range="2024",
                event_category="outbreak",
                document_ids=[uuid4(), uuid4()],
            )
        )

    splits = grouper.split_incidents(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42)

    train_docs = set(splits[DatasetSplit.TRAIN])
    dev_docs = set(splits[DatasetSplit.DEV])
    test_docs = set(splits[DatasetSplit.TEST])

    # Assert total documents accounted for (10 * 2 = 20)
    assert len(train_docs) + len(dev_docs) + len(test_docs) == 20

    # Assert zero overlap (leakage-free)
    assert train_docs.isdisjoint(dev_docs)
    assert train_docs.isdisjoint(test_docs)
    assert dev_docs.isdisjoint(test_docs)


def test_split_reproducibility():
    """Verify split produces identical groupings given identical seeds."""
    grouper = IncidentGrouper()
    for i in range(6):
        grouper.add_incident(
            Incident(
                incident_id=f"inc-{i}",
                incident_title=f"Incident {i}",
                canonical_disease="Pathogen",
                canonical_location="Location",
                temporal_range="2024",
                event_category="outbreak",
                document_ids=[uuid4()],
            )
        )

    splits1 = grouper.split_incidents(seed=42)
    splits2 = grouper.split_incidents(seed=42)

    assert splits1[DatasetSplit.TRAIN] == splits2[DatasetSplit.TRAIN]
    assert splits1[DatasetSplit.DEV] == splits2[DatasetSplit.DEV]
    assert splits1[DatasetSplit.TEST] == splits2[DatasetSplit.TEST]

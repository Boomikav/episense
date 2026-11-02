"""
Incident Grouping and Leakage-Free Dataset Splitting for EpiSense.
Groups related documents by epidemiological incident to ensure that the same outbreak
event never appears across both training and evaluation splits.
"""

import random
from typing import Dict, List, Set
from uuid import UUID
from pydantic import BaseModel, Field

from episense.exceptions import ConfigurationError
from episense.schemas.dataset import DatasetSplit


class Incident(BaseModel):
    """
    Represents an epidemiological event or surveillance episode
    that clusters one or more public health documents.
    """
    incident_id: str = Field(min_length=3, description="Unique slug, e.g. 'inc-nipah-kerala-2023'")
    incident_title: str = Field(min_length=3)
    canonical_disease: str
    canonical_location: str
    temporal_range: str = Field(description="e.g. '2023-09', '2024-06 to 2024-08'")
    event_category: str = Field(description="outbreak, routine_surveillance, advisory, negation")
    document_ids: List[UUID] = Field(default_factory=list)


class IncidentGrouper:
    """
    Maintains incident definitions and partitions documents into leakage-free splits.
    """

    def __init__(self) -> None:
        self._incidents: Dict[str, Incident] = {}
        self._doc_to_incident: Dict[UUID, str] = {}

    def add_incident(self, incident: Incident) -> None:
        """Registers an incident and links its documents."""
        if incident.incident_id in self._incidents:
            raise ConfigurationError(f"Incident '{incident.incident_id}' already registered.")

        for doc_id in incident.document_ids:
            if doc_id in self._doc_to_incident:
                existing = self._doc_to_incident[doc_id]
                raise ConfigurationError(
                    f"Document ID '{doc_id}' is already assigned to incident '{existing}'. Cannot reassign to '{incident.incident_id}'."
                )
            self._doc_to_incident[doc_id] = incident.incident_id

        self._incidents[incident.incident_id] = incident

    def get_incident_for_document(self, doc_id: UUID) -> str:
        """Returns the incident_id for a given document UUID."""
        return self._doc_to_incident.get(doc_id, "unassigned")

    def list_incidents(self) -> List[Incident]:
        return list(self._incidents.values())

    def split_incidents(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Dict[DatasetSplit, List[UUID]]:
        """
        Splits documents by INCIDENT (not document) to prevent data leakage.
        Returns mapping of DatasetSplit -> List[UUID].
        """
        total_ratio = train_ratio + val_ratio + test_ratio
        if abs(total_ratio - 1.0) > 1e-4:
            raise ConfigurationError(f"Split ratios must sum to 1.0, got {total_ratio:.4f}")

        incidents = list(self._incidents.values())
        if not incidents:
            return {
                DatasetSplit.TRAIN: [],
                DatasetSplit.DEV: [],
                DatasetSplit.TEST: [],
            }

        # Deterministic shuffle with pinned seed
        rng = random.Random(seed)
        shuffled_incidents = list(incidents)
        rng.shuffle(shuffled_incidents)

        n_total = len(shuffled_incidents)
        n_train = max(1, int(round(n_total * train_ratio)))
        n_val = max(1, int(round(n_total * val_ratio)))

        # Ensure all incidents allocated
        train_incidents = shuffled_incidents[:n_train]
        val_incidents = shuffled_incidents[n_train:n_train + n_val]
        test_incidents = shuffled_incidents[n_train + n_val:]

        # If test is empty due to small incident count, rebalance
        if not test_incidents and len(train_incidents) > 1:
            test_incidents.append(train_incidents.pop())

        splits: Dict[DatasetSplit, List[UUID]] = {
            DatasetSplit.TRAIN: [doc_id for inc in train_incidents for doc_id in inc.document_ids],
            DatasetSplit.DEV: [doc_id for inc in val_incidents for doc_id in inc.document_ids],
            DatasetSplit.TEST: [doc_id for inc in test_incidents for doc_id in inc.document_ids],
        }

        # Verify zero leakage across splits
        train_set = set(splits[DatasetSplit.TRAIN])
        val_set = set(splits[DatasetSplit.DEV])
        test_set = set(splits[DatasetSplit.TEST])

        assert train_set.isdisjoint(val_set), "Leakage detected between TRAIN and DEV!"
        assert train_set.isdisjoint(test_set), "Leakage detected between TRAIN and TEST!"
        assert val_set.isdisjoint(test_set), "Leakage detected between DEV and TEST!"

        return splits

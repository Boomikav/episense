"""
Abstract interfaces for statistical baseline modeling, anomaly detection, and alert scoring.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

from episense.schemas.cluster import FusedEventCluster


class BaselineModel(ABC):
    """Abstract interface for maintaining historical expected signal baselines."""

    @abstractmethod
    def compute_baseline(self, disease: str, location_id: str, epi_week: int) -> Dict[str, Any]:
        """Calculates expected mean and standard deviation for a spatiotemporal cell."""
        pass


class AnomalyDetector(ABC):
    """Abstract interface for statistical aberration detection."""

    @abstractmethod
    def detect(self, current_count: int, baseline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Applies statistical deviation test (e.g. EARS C1/C2/C3) and returns metrics."""
        pass


class AlertScorer(ABC):
    """Abstract interface for multi-criteria surveillance risk scoring."""

    @abstractmethod
    def calculate_score(
        self,
        anomaly_metrics: Dict[str, Any],
        cluster: FusedEventCluster,
    ) -> Dict[str, Any]:
        """Computes weighted composite score and assigns cautious alert tier."""
        pass

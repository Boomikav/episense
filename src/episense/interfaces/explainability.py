"""
Abstract interface for provenance traversal and evidence dossier compilation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID


class EvidenceProvider(ABC):
    """Abstract interface for bidirectional audit trail generation."""

    @abstractmethod
    def generate_dossier(self, alert_id: UUID) -> Dict[str, Any]:
        """Traverses provenance graph from Alert down to source text character spans."""
        pass

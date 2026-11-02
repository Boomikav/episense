"""
EpiSense Explainability, Audit Trails & Provenance Traversal Engine (Phase 10).
Provides evidence span reconstruction, directed acyclic lineage graphs,
decision path auditing with SHA-256 integrity, and human-readable dossiers.
"""

from episense.explainability.reconstructor import EvidenceSpanReconstructor
from episense.explainability.graph import ProvenanceGraphBuilder
from episense.explainability.auditor import AuditTrailEngine
from episense.explainability.dossier import DossierGenerator
from episense.explainability.batch import ExplainabilityBatchRunner, ExplainabilityBatchReport

__all__ = [
    "EvidenceSpanReconstructor",
    "ProvenanceGraphBuilder",
    "AuditTrailEngine",
    "DossierGenerator",
    "ExplainabilityBatchRunner",
    "ExplainabilityBatchReport",
]

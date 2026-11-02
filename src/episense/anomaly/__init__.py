"""
EpiSense Anomaly and Early Signal Detection Component (Phase 8).
EARS C1/C2/C3 and bounded Farrington-style statistical aberration detection.
"""

from episense.anomaly.ears import EARSDetector, EARSResult
from episense.anomaly.farrington import BoundedFarringtonDetector, FarringtonResult
from episense.anomaly.detector import SignalDetector
from episense.anomaly.batch import SignalBatchRunner, SignalBatchReport

__all__ = [
    "EARSDetector",
    "EARSResult",
    "BoundedFarringtonDetector",
    "FarringtonResult",
    "SignalDetector",
    "SignalBatchRunner",
    "SignalBatchReport",
]

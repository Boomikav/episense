"""
Core domain exception hierarchy for EpiSense.
Enables structured, categorized error handling without silent swallowing.
"""

class EpiSenseError(Exception):
    """Base exception for all EpiSense framework errors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(EpiSenseError):
    """Raised when application or module configuration is invalid or incomplete."""
    pass


class SchemaValidationError(EpiSenseError):
    """Raised when data contracts or schema validations fail."""
    pass


class MalformedInputError(EpiSenseError):
    """Raised when ingested text or raw document payload is corrupt or unparseable."""
    pass


class DataUnavailableError(EpiSenseError):
    """Raised when a required data source, gazetteer, or benchmark file is missing."""
    pass


class NLPExtractionError(EpiSenseError):
    """Raised when an NLP extraction or model execution step fails."""
    pass


class ProvenanceError(EpiSenseError):
    """Raised when an entity, event, or alert cannot be linked back to source text."""
    pass

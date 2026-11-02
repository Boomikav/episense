"""
Typed configuration system for EpiSense based on Pydantic.
Loads parameters from YAML and environment variables with strict validation.
"""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import yaml
from pydantic import BaseModel, Field, model_validator

from episense.exceptions import ConfigurationError


class AppConfig(BaseModel):
    name: str = "EpiSense"
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"


class StorageConfig(BaseModel):
    database_url: str = "sqlite:///./data/processed/episense.sqlite"
    data_raw_dir: str = "./data/raw"
    data_interim_dir: str = "./data/interim"
    data_processed_dir: str = "./data/processed"
    data_benchmarks_dir: str = "./data/benchmarks"


class NLPConfig(BaseModel):
    default_backend: str = "spacy"
    ner_model_name: str = "en_core_sci_sm"
    language: str = "en"
    max_sentence_length: int = 512
    confidence_threshold: float = Field(default=0.50, ge=0.0, le=1.0)


class AssertionConfig(BaseModel):
    method: str = "rule_based"
    confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    enable_context_window: bool = True
    context_window_tokens: int = 12


class TemporalConfig(BaseModel):
    reference_timezone: str = "UTC"
    default_relative_anchor: str = "publication_date"
    max_lookback_days: int = 365


class GeospatialConfig(BaseModel):
    target_scope: str = "India"
    gazetteer_provider: str = "sqlite_local"
    admin_level_default: int = 2
    fuzzy_match_threshold: float = Field(default=85.0, ge=0.0, le=100.0)


class FusionConfig(BaseModel):
    # Approved Architectural Decision D05
    temporal_window_days: int = Field(default=7, gt=0)
    spatial_aggregation_level: str = "admin_2"
    jaccard_dedup_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    min_source_diversity_for_high_alert: int = 2


class BaselineConfig(BaseModel):
    method: str = "historical_rolling"
    lookback_weeks: int = Field(default=7, gt=0)
    min_sample_size: int = Field(default=3, gt=0)


class AnomalyConfig(BaseModel):
    algorithm: str = "EARS_C2"
    z_score_threshold: float = Field(default=2.0, gt=0.0)
    p_value_threshold: float = Field(default=0.01, gt=0.0, lt=1.0)
    smoothing_epsilon: float = Field(default=0.001, gt=0.0)


class ScoringConfig(BaseModel):
    # Authoritative 5-Dimensional Heuristic Risk Weights (Sum = 1.00)
    # Note: These weights represent domain epidemiological consensus heuristics, NOT fitted parameters.
    weight_anomaly: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_threat: float = Field(default=0.25, ge=0.0, le=1.0)
    weight_evidence: float = Field(default=0.20, ge=0.0, le=1.0)
    weight_certainty: float = Field(default=0.15, ge=0.0, le=1.0)
    weight_spatial: float = Field(default=0.10, ge=0.0, le=1.0)

    # Legacy alias support for backward compatibility with older test harnesses
    weight_diversity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    weight_assertion: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    threshold_informational: float = 0.00
    threshold_low: float = 0.40
    threshold_medium: float = 0.65
    threshold_high: float = 0.80

    @model_validator(mode="before")
    @classmethod
    def resolve_legacy_weights(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if ("weight_diversity" in data or "weight_assertion" in data) and "weight_threat" not in data:
                data["weight_threat"] = 0.0
        return data

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "ScoringConfig":
        w_ev = self.weight_evidence if self.weight_diversity is None else self.weight_diversity
        w_cert = self.weight_certainty if self.weight_assertion is None else self.weight_assertion
        total = self.weight_anomaly + self.weight_threat + w_ev + w_cert + self.weight_spatial
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Scoring weights must sum to 1.0; current sum is {total:.4f}")
        return self


class APIConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    max_payload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    default_page_size: int = Field(default=20, gt=0)
    max_page_size: int = Field(default=100, gt=0)


class EpiSenseConfig(BaseModel):
    """Unified configuration root for EpiSense."""
    app: AppConfig = Field(default_factory=AppConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    nlp: NLPConfig = Field(default_factory=NLPConfig)
    assertion: AssertionConfig = Field(default_factory=AssertionConfig)
    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    geospatial: GeospatialConfig = Field(default_factory=GeospatialConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    baseline: BaselineConfig = Field(default_factory=BaselineConfig)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    api: APIConfig = Field(default_factory=APIConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "EpiSenseConfig":
        """Loads configuration from a YAML file."""
        file_path = Path(path)
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            raise ConfigurationError(f"Failed to parse configuration YAML: {e}") from e

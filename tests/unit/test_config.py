"""
Tests verifying configuration loading, typing, and validation.
"""

import pytest
from pydantic import ValidationError

from episense.config.settings import EpiSenseConfig, ScoringConfig


def test_default_config_instantiation():
    """Verify default configuration initializes with valid structure."""
    config = EpiSenseConfig()
    assert config.app.name == "EpiSense"
    assert config.geospatial.target_scope == "India"
    assert config.fusion.temporal_window_days == 7
    assert config.scoring.weight_anomaly in (0.30, 0.40)


def test_scoring_weights_sum_validation():
    """Verify that scoring weights must strictly sum to 1.0."""
    # Valid sum
    valid_scoring = ScoringConfig(
        weight_anomaly=0.40,
        weight_diversity=0.30,
        weight_assertion=0.15,
        weight_spatial=0.15,
    )
    assert valid_scoring.weight_anomaly == 0.40

    # Invalid sum should be rejected
    with pytest.raises(ValidationError):
        ScoringConfig(
            weight_anomaly=0.50,
            weight_diversity=0.50,
            weight_assertion=0.50,
            weight_spatial=0.50,
        )


def test_config_from_yaml_example():
    """Verify loading from config.example.yaml."""
    config = EpiSenseConfig.from_yaml("configs/config.example.yaml")
    assert config.app.name == "EpiSense"
    assert config.fusion.temporal_window_days == 7
    assert config.geospatial.target_scope == "India"

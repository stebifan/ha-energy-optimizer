"""Tests for battery helpers."""

from custom_components.energy_optimizer.models.battery_model import (
    pv_strom_to_watts,
    watts_to_pv_strom,
)


def test_pv_strom_mapping():
    """Verify pv_strom stage to watt mapping."""
    assert pv_strom_to_watts(0) == 0
    assert pv_strom_to_watts(10) == 800
    assert watts_to_pv_strom(800) == 10
    assert watts_to_pv_strom(400) == 5
    assert watts_to_pv_strom(900) == 10

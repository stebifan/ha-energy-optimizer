"""Tests for EPEX price parsing."""

import pytest

from custom_components.energy_optimizer.models.price_model import (
    hourly_prices,
    parse_epex_data,
    price_rank_today,
)

SLOT = {
    "start_time": "2026-06-27T08:00:00+02:00",
    "end_time": "2026-06-27T08:15:00+02:00",
}


def test_parse_epex_data():
    """Parse sample EPEX attribute data."""
    raw = [
        {**SLOT, "price_per_kwh": 0.1},
        {
            "start_time": "2026-06-27T10:15:00+02:00",
            "end_time": "2026-06-27T10:30:00+02:00",
            "price_per_kwh": 0.2,
        },
    ]
    slots = parse_epex_data(raw, surcharge_eur_kwh=0.05)
    assert len(slots) == 2
    assert slots[0].price_eur_kwh == pytest.approx(0.15)
    hourly = hourly_prices(slots)
    assert len(hourly) == 2
    assert hourly[0].price_eur_kwh == pytest.approx(0.15)


def test_price_rank():
    """Rank current price among slots."""
    raw = [
        {**SLOT, "price_per_kwh": 0.1},
        {
            "start_time": "2026-06-27T09:00:00+02:00",
            "end_time": "2026-06-27T09:15:00+02:00",
            "price_per_kwh": 0.3,
        },
        {
            "start_time": "2026-06-27T10:00:00+02:00",
            "end_time": "2026-06-27T10:15:00+02:00",
            "price_per_kwh": 0.2,
        },
    ]
    slots = parse_epex_data(raw)
    assert price_rank_today(slots, 0.1) == 1
    assert price_rank_today(slots, 0.3) == 3

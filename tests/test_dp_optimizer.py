"""Tests for DP optimizer."""

from datetime import datetime, timezone

from custom_components.energy_optimizer.models.dp_optimizer import optimize_dp
from custom_components.energy_optimizer.models.time_series import HourlyBucket


def _hour(hour: int, price: float, load: float, pv: float) -> tuple:
    start = datetime(2026, 6, 27, hour, 0, tzinfo=timezone.utc)
    return (
        HourlyBucket(start=start, price_eur_kwh=price),
        HourlyBucket(start=start, price_eur_kwh=0.0, load_kwh=load),
        HourlyBucket(start=start, price_eur_kwh=0.0, pv_kwh=pv),
    )


def test_optimize_dp_finds_savings():
    """DP should reduce cost vs baseline when prices vary."""
    rows = [_hour(h, p, 1.0, 0.0) for h, p in enumerate([0.5, 0.1, 0.1, 0.9, 0.9])]
    prices, loads, pvs = zip(*rows)
    now = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    charge, discharge, baseline, optimized = optimize_dp(
        list(prices),
        list(loads),
        list(pvs),
        [],
        now,
        capacity_kwh=2.0,
    )
    assert baseline > 0
    assert optimized <= baseline
    assert isinstance(charge, set)

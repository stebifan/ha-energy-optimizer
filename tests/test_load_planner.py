"""Tests for load planner."""

from datetime import datetime, timezone

from custom_components.energy_optimizer.models.load_planner import (
    LoadConfig,
    plan_shiftable_loads,
)
from custom_components.energy_optimizer.models.time_series import HourlyBucket


def _hour(hour: int, price: float) -> HourlyBucket:
    start = datetime(2026, 6, 27, hour, 0, tzinfo=timezone.utc)
    return HourlyBucket(start=start, price_eur_kwh=price)


def test_plan_load_in_cheap_hour():
    """Schedule load into cheapest eligible hour."""
    loads = [
        LoadConfig(
            subentry_id="pool",
            name="Pool",
            control_entity="switch.pool",
            window_start="08:00",
            window_end="20:00",
        )
    ]
    hourly = [_hour(h, float(h)) for h in range(8, 21)]
    cheap = {hourly[2].start}
    now = datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc)

    actions, states = plan_shiftable_loads(loads, hourly, now, cheap)
    assert len(states) == 1
    assert states[0].run_now is True
    assert actions[0].action == "turn_on"

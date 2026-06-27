"""Tests for optimizer coordination and KPIs."""

from datetime import datetime, timezone

from custom_components.energy_optimizer.const import (
    BATTERY_TYPE_ECOFLOW,
    OPTIMIZER_ENGINE_DP,
    OPTIMIZER_ENGINE_HEURISTIC,
)
from custom_components.energy_optimizer.models.battery_model import (
    BatteryConfig,
    BatteryState,
)
from custom_components.energy_optimizer.models.optimizer import optimize
from custom_components.energy_optimizer.models.time_series import HourlyBucket


def _hour(hour: int, price: float, load: float = 1.0, pv: float = 0.0) -> HourlyBucket:
    start = datetime(2026, 6, 27, hour, 0, tzinfo=timezone.utc)
    return HourlyBucket(
        start=start,
        price_eur_kwh=price,
        load_kwh=load,
        pv_kwh=pv,
    )


def _ecoflow(subentry_id: str, priority: int, soc: float) -> BatteryState:
    return BatteryState(
        config=BatteryConfig(
            subentry_id=subentry_id,
            name=subentry_id,
            battery_type=BATTERY_TYPE_ECOFLOW,
            capacity_kwh=3.0,
            priority=priority,
            backup_reserve_entity=f"number.{subentry_id}_backup",
        ),
        soc_percent=soc,
    )


def test_only_highest_priority_ecoflow_charges():
    """Only one EcoFlow should charge in a cheap hour."""
    hourly = [_hour(h, p) for h, p in enumerate([0.5, 0.1, 0.1, 0.9, 0.9, 0.9])]
    now = datetime(2026, 6, 27, 1, 0, tzinfo=timezone.utc)
    batteries = [
        _ecoflow("buro", priority=1, soc=50.0),
        _ecoflow("garten", priority=2, soc=50.0),
    ]

    result = optimize(
        profile="balanced",
        hourly_prices=hourly,
        hourly_load=hourly,
        hourly_pv=[_hour(h, 0.0, pv=0.0) for h in range(6)],
        batteries=batteries,
        loads=[],
        now=now,
        engine=OPTIMIZER_ENGINE_HEURISTIC,
    )

    charging = [b for b in batteries if b.charge_now]
    assert len(charging) == 1
    assert charging[0].config.subentry_id == "buro"
    assert len(result.battery_actions) == 1
    assert result.battery_actions[0].battery_id == "buro"


def test_dp_engine_returns_lower_or_equal_cost():
    """DP optimizer should not exceed baseline grid cost."""
    hourly = [_hour(h, p, load=1.5, pv=0.2) for h, p in enumerate([0.4, 0.2, 0.2, 0.8, 0.9])]
    now = datetime(2026, 6, 27, 0, 0, tzinfo=timezone.utc)
    batteries = [_ecoflow("buro", priority=1, soc=40.0)]

    result = optimize(
        profile="cost_min",
        hourly_prices=hourly,
        hourly_load=hourly,
        hourly_pv=hourly,
        batteries=batteries,
        loads=[],
        now=now,
        engine=OPTIMIZER_ENGINE_DP,
    )

    assert result.baseline_cost_eur > 0
    assert result.optimized_cost_eur <= result.baseline_cost_eur
    assert result.plan

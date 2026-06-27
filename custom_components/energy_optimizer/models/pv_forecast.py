"""PV forecast aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .time_series import HourlyBucket


@dataclass(frozen=True)
class PvPlantForecast:
    """Forecast data for one PV plant."""

    name: str
    today_kwh: float
    tomorrow_kwh: float
    power_now_w: float
    share_ratio: float = 1.0


def aggregate_pv_forecast(
    plants: list[PvPlantForecast],
    total_today_kwh: float | None = None,
    total_tomorrow_kwh: float | None = None,
) -> tuple[float, float, float]:
    """Return total today, tomorrow, and power now from plant list."""
    if not plants:
        return (total_today_kwh or 0.0, total_tomorrow_kwh or 0.0, 0.0)

    if total_today_kwh is not None:
        today = total_today_kwh
    else:
        today = sum(plant.today_kwh for plant in plants)

    if total_tomorrow_kwh is not None:
        tomorrow = total_tomorrow_kwh
    else:
        tomorrow = sum(plant.tomorrow_kwh for plant in plants)

    power_now = sum(plant.power_now_w * plant.share_ratio for plant in plants)
    return today, tomorrow, power_now


def distribute_hourly_pv(
    total_today_kwh: float,
    hour_starts: list[datetime],
    peak_hour: int = 12,
) -> list[HourlyBucket]:
    """Simple bell-curve distribution of daily PV across hours."""
    if not hour_starts or total_today_kwh <= 0:
        return [
            HourlyBucket(start=h, price_eur_kwh=0.0, pv_kwh=0.0) for h in hour_starts
        ]

    weights: list[float] = []
    for hour_start in hour_starts:
        distance = abs(hour_start.hour - peak_hour)
        weights.append(max(0.05, 1.0 - distance / 12.0))

    total_weight = sum(weights) or 1.0
    return [
        HourlyBucket(
            start=hour_start,
            price_eur_kwh=0.0,
            pv_kwh=total_today_kwh * weight / total_weight,
        )
        for hour_start, weight in zip(hour_starts, weights, strict=False)
    ]

"""Consumption forecast from recorder statistics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any

from .time_series import HourlyBucket, floor_to_hour


def _hour_key(dt: datetime) -> tuple[int, int]:
    """Weekday + hour key for profiling."""
    return (dt.weekday(), dt.hour)


def build_load_profile(
    statistics: list[dict[str, Any]],
) -> dict[tuple[int, int], float]:
    """Build average kWh per (weekday, hour) from recorder statistics."""
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)

    for stat in statistics:
        start = datetime.fromisoformat(stat["start"])
        state = stat.get("state")
        if state in (None, "unknown", "unavailable"):
            continue
        try:
            power_w = float(state)
        except (TypeError, ValueError):
            continue
        if power_w < 0:
            continue
        key = _hour_key(start)
        buckets[key].append(power_w / 1000.0)

    profile: dict[tuple[int, int], float] = {}
    for key, values in buckets.items():
        profile[key] = mean(values)
    return profile


def forecast_load_kwh(
    profile: dict[tuple[int, int], float],
    hour_starts: list[datetime],
    default_kw: float = 0.5,
) -> list[HourlyBucket]:
    """Forecast hourly load kWh using weekday/hour profile."""
    result: list[HourlyBucket] = []
    for hour_start in hour_starts:
        key = _hour_key(hour_start)
        load_kw = profile.get(key, default_kw)
        result.append(
            HourlyBucket(
                start=hour_start,
                price_eur_kwh=0.0,
                load_kwh=load_kw,
            )
        )
    return result


def statistics_to_hourly_samples(
    statistics: list[dict[str, Any]],
) -> list[tuple[datetime, float]]:
    """Convert recorder statistics to (hour, kWh) samples."""
    samples: list[tuple[datetime, float]] = []
    for stat in statistics:
        start = datetime.fromisoformat(stat["start"])
        state = stat.get("state")
        if state in (None, "unknown", "unavailable"):
            continue
        try:
            power_w = float(state)
        except (TypeError, ValueError):
            continue
        samples.append((floor_to_hour(start), power_w / 1000.0))
    return samples

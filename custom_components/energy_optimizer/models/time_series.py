"""Time series helpers for 15-minute energy slots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class PriceSlot:
    """Single 15-minute price slot."""

    start: datetime
    end: datetime
    price_eur_kwh: float


@dataclass(frozen=True)
class HourlyBucket:
    """Aggregated hourly values."""

    start: datetime
    price_eur_kwh: float
    load_kwh: float = 0.0
    pv_kwh: float = 0.0


def parse_iso(value: str) -> datetime:
    """Parse ISO timestamp from EPEX attributes."""
    return datetime.fromisoformat(value)


def floor_to_hour(dt: datetime) -> datetime:
    """Return hour start for a datetime."""
    return dt.replace(minute=0, second=0, microsecond=0)


def slots_to_hourly(slots: list[PriceSlot]) -> list[HourlyBucket]:
    """Average 15-minute prices into hourly buckets."""
    if not slots:
        return []

    hourly: dict[datetime, list[float]] = {}
    for slot in slots:
        hour = floor_to_hour(slot.start)
        hourly.setdefault(hour, []).append(slot.price_eur_kwh)

    return [
        HourlyBucket(
            start=hour,
            price_eur_kwh=sum(prices) / len(prices),
        )
        for hour, prices in sorted(hourly.items())
    ]


def next_hours(now: datetime, count: int, tz: ZoneInfo) -> list[datetime]:
    """Return upcoming hour starts in timezone."""
    local = now.astimezone(tz)
    start = floor_to_hour(local)
    return [start + timedelta(hours=offset) for offset in range(count)]

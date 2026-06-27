"""EPEX Spot price parsing and normalization."""

from __future__ import annotations

from typing import Any

from .time_series import HourlyBucket, PriceSlot, parse_iso, slots_to_hourly


def parse_epex_data(
    raw_data: list[dict[str, Any]] | None,
    surcharge_eur_kwh: float = 0.0,
) -> list[PriceSlot]:
    """Parse EPEX Spot `data` attribute into normalized slots."""
    if not raw_data:
        return []

    slots: list[PriceSlot] = []
    for item in raw_data:
        try:
            price = float(item["price_per_kwh"]) + surcharge_eur_kwh
            slots.append(
                PriceSlot(
                    start=parse_iso(item["start_time"]),
                    end=parse_iso(item["end_time"]),
                    price_eur_kwh=price,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return slots


def current_slot(slots: list[PriceSlot], now) -> PriceSlot | None:
    """Return the slot covering `now`."""
    for slot in slots:
        if slot.start <= now < slot.end:
            return slot
    return None


def price_rank_today(slots: list[PriceSlot], current_price: float) -> int | None:
    """Return 1-based rank of current price among today's slots (1=cheapest)."""
    today_prices = sorted({slot.price_eur_kwh for slot in slots})
    if not today_prices:
        return None
    try:
        return today_prices.index(current_price) + 1
    except ValueError:
        return None


def cheapest_window_start(hourly: list[HourlyBucket], window_hours: int = 3) -> str | None:
    """Find start of cheapest consecutive hourly window."""
    if len(hourly) < window_hours:
        return None

    best_start = None
    best_avg = float("inf")
    for index in range(len(hourly) - window_hours + 1):
        window = hourly[index : index + window_hours]
        avg = sum(bucket.price_eur_kwh for bucket in window) / window_hours
        if avg < best_avg:
            best_avg = avg
            best_start = window[0].start

    return best_start.isoformat() if best_start else None


def hourly_prices(slots: list[PriceSlot]) -> list[HourlyBucket]:
    """Return hourly averaged prices."""
    return slots_to_hourly(slots)

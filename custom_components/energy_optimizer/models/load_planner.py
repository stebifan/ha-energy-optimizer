"""Shiftable load scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from ..const import CONSTRAINT_HARD
from .time_series import HourlyBucket


@dataclass
class LoadConfig:
    """Configuration for a shiftable load."""

    subentry_id: str
    name: str
    control_entity: str
    priority: int = 1
    constraint_type: str = "soft"
    window_start: str = "00:00"
    window_end: str = "23:59"
    duration_minutes: int = 60


@dataclass
class LoadPlanAction:
    """Planned action for a shiftable load."""

    load_id: str
    action: str
    reason: str = ""
    scheduled_start: str | None = None


@dataclass
class LoadScheduleState:
    """Runtime state for one load."""

    config: LoadConfig
    run_now: bool = False
    scheduled_start: str | None = None
    reason: str = ""


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _in_window(hour_start: datetime, window_start: str, window_end: str) -> bool:
    start = _parse_time(window_start)
    end = _parse_time(window_end)
    current = hour_start.time().replace(second=0, microsecond=0)
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def plan_shiftable_loads(
    loads: list[LoadConfig],
    hourly_prices: list[HourlyBucket],
    now: datetime,
    cheap_hour_starts: set[datetime],
    pv_surplus_hours: set[datetime] | None = None,
) -> tuple[list[LoadPlanAction], list[LoadScheduleState]]:
    """Schedule loads into cheap or PV-surplus hours within their windows."""
    if pv_surplus_hours is None:
        pv_surplus_hours = set()

    current_hour = now.replace(minute=0, second=0, microsecond=0)
    actions: list[LoadPlanAction] = []
    states: list[LoadScheduleState] = []

    sorted_prices = sorted(hourly_prices, key=lambda bucket: bucket.price_eur_kwh)

    for load in loads:
        state = LoadScheduleState(config=load)
        eligible = [
            bucket
            for bucket in sorted_prices
            if _in_window(bucket.start, load.window_start, load.window_end)
        ]
        if not eligible:
            if load.constraint_type == CONSTRAINT_HARD:
                state.reason = "Kein Zeitfenster verfügbar"
            states.append(state)
            continue

        preferred = [
            bucket
            for bucket in eligible
            if bucket.start in cheap_hour_starts or bucket.start in pv_surplus_hours
        ]
        candidates = preferred or eligible
        slot = candidates[0]
        state.scheduled_start = slot.start.isoformat()
        state.reason = (
            "Günstige Stunde"
            if slot.start in cheap_hour_starts
            else "PV-Überschuss"
            if slot.start in pv_surplus_hours
            else "Beste verfügbare Stunde"
        )

        if slot.start == current_hour:
            state.run_now = True
            actions.append(
                LoadPlanAction(
                    load_id=load.subentry_id,
                    action="turn_on",
                    reason=state.reason,
                    scheduled_start=slot.start.isoformat(),
                )
            )
        else:
            actions.append(
                LoadPlanAction(
                    load_id=load.subentry_id,
                    action="turn_off",
                    reason=f"Geplant ab {slot.start.strftime('%H:%M')}",
                    scheduled_start=slot.start.isoformat(),
                )
            )

        states.append(state)

    return actions, states

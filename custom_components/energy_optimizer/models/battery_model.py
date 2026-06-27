"""Battery state models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..const import (
    BATTERY_TYPE_ECOFLOW,
    BATTERY_TYPE_VICTRON_BUFFER,
    DEFAULT_MAX_RESERVE,
    DEFAULT_MIN_SOC,
    DEFAULT_NORMAL_RESERVE,
    PV_STROM_MAX_STAGE,
    PV_STROM_WATTS_PER_STAGE,
)


@dataclass
class BatteryConfig:
    """Configuration for one battery asset."""

    subentry_id: str
    name: str
    battery_type: str
    capacity_kwh: float
    priority: int = 1
    soc_entity: str | None = None
    backup_reserve_entity: str | None = None
    normal_reserve: float = DEFAULT_NORMAL_RESERVE
    max_reserve: float = DEFAULT_MAX_RESERVE
    min_soc: float = DEFAULT_MIN_SOC
    pv_status_entity: str | None = None
    pv_strom_entity: str | None = None
    pv_yield_power_entity: str | None = None
    self_powered_entity: str | None = None
    ai_mode_entity: str | None = None


@dataclass
class BatteryState:
    """Runtime battery state."""

    config: BatteryConfig
    soc_percent: float = 0.0
    charge_now: bool = False
    discharge_now: bool = False
    target_reserve: float | None = None
    target_pv_strom: int | None = None
    reason: str = ""


def pv_strom_to_watts(stage: int) -> int:
    """Convert pv_strom stage to watts (10 = 800 W)."""
    clamped = max(0, min(PV_STROM_MAX_STAGE, stage))
    return clamped * PV_STROM_WATTS_PER_STAGE


def watts_to_pv_strom(watts: float) -> int:
    """Convert watts to pv_strom stage."""
    if watts <= 0:
        return 0
    stage = round(watts / PV_STROM_WATTS_PER_STAGE)
    return max(0, min(PV_STROM_MAX_STAGE, stage))


def is_active_battery(battery_type: str) -> bool:
    """Return True if EMS can control grid charging."""
    return battery_type == BATTERY_TYPE_ECOFLOW


def is_passive_battery(battery_type: str) -> bool:
    """Return True if battery only discharges via helpers."""
    return battery_type == BATTERY_TYPE_VICTRON_BUFFER


@dataclass
class BatteryPlanAction:
    """Planned action for one battery."""

    battery_id: str
    action: str
    target_value: float | int | None = None
    reason: str = ""


@dataclass
class OptimizerResult:
    """Full optimizer output."""

    plan: list[dict] = field(default_factory=list)
    battery_actions: list[BatteryPlanAction] = field(default_factory=list)
    load_actions: list = field(default_factory=list)
    load_states: list = field(default_factory=list)
    estimated_savings_eur: float = 0.0
    baseline_cost_eur: float = 0.0
    optimized_cost_eur: float = 0.0
    next_action: str = ""
    next_action_at: str | None = None

"""Energy optimizer — heuristic and DP engines."""

from __future__ import annotations

from datetime import datetime

from ..const import (
    BATTERY_TYPE_ECOFLOW,
    BATTERY_TYPE_VICTRON_BUFFER,
    OPTIMIZER_ENGINE_DP,
    OPTIMIZER_ENGINE_HEURISTIC,
    PROFILE_BALANCED,
    PROFILE_COST_MIN,
    PROFILE_SELF_SUFFICIENCY,
)
from .battery_model import (
    BatteryPlanAction,
    BatteryState,
    OptimizerResult,
    watts_to_pv_strom,
)
from .dp_optimizer import build_dp_battery_actions, optimize_dp
from .load_planner import LoadConfig, plan_shiftable_loads
from .time_series import HourlyBucket


def _profile_weights(profile: str) -> tuple[float, float]:
    """Return (price_weight, autonomy_weight)."""
    if profile == PROFILE_COST_MIN:
        return (1.0, 0.0)
    if profile == PROFILE_SELF_SUFFICIENCY:
        return (0.2, 0.8)
    if profile == PROFILE_BALANCED:
        return (0.6, 0.4)
    return (0.5, 0.5)


def _build_plan(
    hourly_prices: list[HourlyBucket],
    hourly_load: list[HourlyBucket],
    hourly_pv: list[HourlyBucket],
    charge_hours: set[datetime],
    discharge_hours: set[datetime],
) -> list[dict]:
    """Build hourly plan entries."""
    plan: list[dict] = []
    for index, price_bucket in enumerate(hourly_prices):
        load_kwh = hourly_load[index].load_kwh if index < len(hourly_load) else 0.0
        pv_kwh = hourly_pv[index].pv_kwh if index < len(hourly_pv) else 0.0
        action = "idle"
        reason = "Ausgewogen"
        if price_bucket.start in charge_hours:
            action = "charge_grid"
            reason = "Günstige Stunde für Netzladen"
        elif price_bucket.start in discharge_hours:
            action = "discharge"
            reason = "Teure Stunde – Entladen bevorzugt"
        plan.append(
            {
                "start": price_bucket.start.isoformat(),
                "price_eur_kwh": round(price_bucket.price_eur_kwh, 5),
                "load_kwh": round(load_kwh, 3),
                "pv_kwh": round(pv_kwh, 3),
                "action": action,
                "reason": reason,
            }
        )
    return plan


def _heuristic_hour_sets(
    hourly_prices: list[HourlyBucket],
) -> tuple[set[datetime], set[datetime]]:
    sorted_hours = sorted(hourly_prices, key=lambda bucket: bucket.price_eur_kwh)
    cheap = {bucket.start for bucket in sorted_hours[:6]}
    expensive = {bucket.start for bucket in sorted_hours[-6:]}
    return cheap, expensive


def _coordinate_ecoflow_charging(
    batteries: list[BatteryState],
    current_plan: dict | None,
    net_kwh: float,
) -> list[BatteryPlanAction]:
    """Only the highest-priority EcoFlow with headroom charges."""
    actions: list[BatteryPlanAction] = []
    ecoflows = sorted(
        [b for b in batteries if b.config.battery_type == BATTERY_TYPE_ECOFLOW],
        key=lambda b: b.config.priority,
    )

    charging_assigned = False
    for battery in ecoflows:
        cfg = battery.config
        if current_plan and current_plan["action"] == "charge_grid" and not charging_assigned:
            if battery.soc_percent < cfg.max_reserve - 5:
                target = min(
                    cfg.max_reserve,
                    max(cfg.normal_reserve + 20, battery.soc_percent + 15),
                )
                battery.charge_now = True
                battery.target_reserve = target
                battery.reason = current_plan["reason"]
                actions.append(
                    BatteryPlanAction(
                        battery_id=cfg.subentry_id,
                        action="set_backup_reserve",
                        target_value=target,
                        reason=current_plan["reason"],
                    )
                )
                charging_assigned = True
                continue
        battery.charge_now = False
        battery.target_reserve = cfg.normal_reserve

    return actions


def _coordinate_buffer_discharge(
    batteries: list[BatteryState],
    current_plan: dict | None,
    net_kwh: float,
) -> list[BatteryPlanAction]:
    """Discharge passive buffers in expensive hours."""
    actions: list[BatteryPlanAction] = []
    buffers = sorted(
        [b for b in batteries if b.config.battery_type == BATTERY_TYPE_VICTRON_BUFFER],
        key=lambda b: b.config.priority,
    )

    for battery in buffers:
        cfg = battery.config
        if (
            current_plan
            and current_plan["action"] == "discharge"
            and battery.soc_percent > cfg.min_soc
        ):
            discharge_w = min(800.0, net_kwh * 1000)
            stage = watts_to_pv_strom(discharge_w)
            battery.discharge_now = True
            battery.target_pv_strom = stage
            battery.reason = current_plan["reason"]
            actions.append(
                BatteryPlanAction(
                    battery_id=cfg.subentry_id,
                    action="discharge_buffer",
                    target_value=stage,
                    reason=current_plan["reason"],
                )
            )
        else:
            battery.discharge_now = False
            battery.target_pv_strom = 0

    return actions


def optimize(
    profile: str,
    hourly_prices: list[HourlyBucket],
    hourly_load: list[HourlyBucket],
    hourly_pv: list[HourlyBucket],
    batteries: list[BatteryState],
    loads: list[LoadConfig],
    now: datetime,
    engine: str = OPTIMIZER_ENGINE_HEURISTIC,
) -> OptimizerResult:
    """Run selected optimizer engine."""
    if not hourly_prices:
        return OptimizerResult(next_action="Keine Preisdaten")

    price_weight, _ = _profile_weights(profile)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    baseline_cost = 0.0
    optimized_cost = 0.0

    if engine == OPTIMIZER_ENGINE_DP:
        primary_capacity = next(
            (b.config.capacity_kwh for b in batteries if b.config.capacity_kwh > 0),
            5.0,
        )
        charge_hours, discharge_hours, baseline_cost, optimized_cost = optimize_dp(
            hourly_prices,
            hourly_load,
            hourly_pv,
            batteries,
            now,
            capacity_kwh=primary_capacity,
        )
        plan = _build_plan(hourly_prices, hourly_load, hourly_pv, charge_hours, discharge_hours)
        current_plan = next(
            (item for item in plan if item["start"] == current_hour.isoformat()),
            plan[0] if plan else None,
        )
        net_kwh = 0.0
        if current_plan:
            net_kwh = max(0.0, current_plan["load_kwh"] - current_plan["pv_kwh"])
        battery_actions = build_dp_battery_actions(
            batteries,
            charge_hours,
            discharge_hours,
            current_hour,
            net_kwh,
            "DP: günstige Stunde",
            "DP: teure Stunde",
        )
    else:
        charge_hours, discharge_hours = _heuristic_hour_sets(hourly_prices)
        plan = _build_plan(hourly_prices, hourly_load, hourly_pv, charge_hours, discharge_hours)
        current_plan = next(
            (item for item in plan if item["start"] == current_hour.isoformat()),
            plan[0] if plan else None,
        )
        net_kwh = 0.0
        if current_plan:
            net_kwh = max(0.0, current_plan["load_kwh"] - current_plan["pv_kwh"])
        battery_actions = _coordinate_ecoflow_charging(batteries, current_plan, net_kwh)
        battery_actions.extend(_coordinate_buffer_discharge(batteries, current_plan, net_kwh))

        baseline_cost = sum(
            max(0.0, hourly_load[i].load_kwh - hourly_pv[i].pv_kwh)
            * hourly_prices[i].price_eur_kwh
            for i in range(min(len(hourly_prices), len(hourly_load), len(hourly_pv)))
        )
        optimized_cost = baseline_cost

    pv_surplus = {
        hourly_pv[i].start
        for i in range(min(len(hourly_pv), len(hourly_load)))
        if hourly_pv[i].pv_kwh > hourly_load[i].load_kwh
    }
    load_actions, load_states = plan_shiftable_loads(
        loads,
        hourly_prices,
        now,
        charge_hours,
        pv_surplus,
    )

    next_action = current_plan["action"] if current_plan else "idle"
    savings = max(0.0, baseline_cost - optimized_cost)
    if engine == OPTIMIZER_ENGINE_HEURISTIC:
        sorted_hours = sorted(hourly_prices, key=lambda bucket: bucket.price_eur_kwh)
        savings = sum(
            max(
                0.0,
                hourly_load[i].load_kwh
                * (sorted_hours[-1].price_eur_kwh - hourly_prices[i].price_eur_kwh),
            )
            for i in range(min(6, len(hourly_prices), len(hourly_load)))
        ) * price_weight

    return OptimizerResult(
        plan=plan,
        battery_actions=battery_actions,
        load_actions=load_actions,
        load_states=load_states,
        estimated_savings_eur=round(savings, 2),
        baseline_cost_eur=round(baseline_cost, 2),
        optimized_cost_eur=round(optimized_cost, 2),
        next_action=next_action,
        next_action_at=current_plan["start"] if current_plan else None,
    )

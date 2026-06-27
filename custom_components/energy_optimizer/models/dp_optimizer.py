"""Dynamic programming optimizer for hourly battery scheduling."""

from __future__ import annotations

from datetime import datetime

from .battery_model import BatteryPlanAction, BatteryState
from .time_series import HourlyBucket


def optimize_dp(
    hourly_prices: list[HourlyBucket],
    hourly_load: list[HourlyBucket],
    hourly_pv: list[HourlyBucket],
    batteries: list[BatteryState],
    now: datetime,
    capacity_kwh: float = 5.0,
    max_charge_kwh: float = 1.5,
    max_discharge_kwh: float = 1.5,
    steps: int = 12,
) -> tuple[set[datetime], set[datetime], float, float]:
    """Return cheap charge hours, expensive discharge hours, baseline and optimized cost."""
    if not hourly_prices:
        return set(), set(), 0.0, 0.0

    horizon = min(len(hourly_prices), 24)
    prices = hourly_prices[:horizon]
    loads = hourly_load[:horizon]
    pvs = hourly_pv[:horizon]

    net_loads = [
        max(0.0, loads[i].load_kwh - pvs[i].pv_kwh) for i in range(horizon)
    ]
    baseline_cost = sum(
        net_loads[i] * prices[i].price_eur_kwh for i in range(horizon)
    )

    soc_states = [round(i * capacity_kwh / steps, 3) for i in range(steps + 1)]
    inf = float("inf")
    cost = [[inf] * (steps + 1) for _ in range(horizon + 1)]
    policy: list[list[str | None]] = [[None] * (steps + 1) for _ in range(horizon)]

    cost[0][0] = 0.0
    for hour in range(horizon):
        for soc_index, soc in enumerate(soc_states):
            if cost[hour][soc_index] == inf:
                continue
            current_cost = cost[hour][soc_index]
            price = prices[hour].price_eur_kwh
            need = net_loads[hour]

            # idle / pass through
            next_index = soc_index
            next_cost = current_cost + need * price
            if next_cost < cost[hour + 1][next_index]:
                cost[hour + 1][next_index] = next_cost
                policy[hour][next_index] = "idle"

            # charge from grid
            charge = min(max_charge_kwh, capacity_kwh - soc)
            if charge > 0:
                next_soc = min(capacity_kwh, soc + charge)
                next_index = min(steps, round(next_soc / capacity_kwh * steps))
                served = min(need, charge)
                grid_need = max(0.0, need - served)
                next_cost = current_cost + charge * price + grid_need * price
                if next_cost < cost[hour + 1][next_index]:
                    cost[hour + 1][next_index] = next_cost
                    policy[hour][next_index] = "charge"

            # discharge to serve load cheaper than grid
            discharge = min(max_discharge_kwh, soc)
            if discharge > 0:
                next_soc = max(0.0, soc - discharge)
                next_index = max(0, round(next_soc / capacity_kwh * steps))
                served = min(need, discharge)
                grid_need = max(0.0, need - served)
                next_cost = current_cost + grid_need * price
                if next_cost < cost[hour + 1][next_index]:
                    cost[hour + 1][next_index] = next_cost
                    policy[hour][next_index] = "discharge"

    optimized_cost = min(cost[horizon])
    charge_hours: set[datetime] = set()
    discharge_hours: set[datetime] = set()

    best_index = cost[horizon].index(optimized_cost)
    for hour in range(horizon - 1, -1, -1):
        action = policy[hour][best_index]
        if action == "charge":
            charge_hours.add(prices[hour].start)
        elif action == "discharge":
            discharge_hours.add(prices[hour].start)
        best_index = max(0, best_index - 1)

    return charge_hours, discharge_hours, round(baseline_cost, 2), round(optimized_cost, 2)


def build_dp_battery_actions(
    batteries: list[BatteryState],
    charge_hours: set[datetime],
    discharge_hours: set[datetime],
    current_hour: datetime,
    net_kwh: float,
    reason_charge: str,
    reason_discharge: str,
) -> list[BatteryPlanAction]:
    """Map DP hour sets to battery actions with priority coordination."""
    from ..const import BATTERY_TYPE_ECOFLOW, BATTERY_TYPE_VICTRON_BUFFER

    actions: list[BatteryPlanAction] = []
    ecoflows = sorted(
        [b for b in batteries if b.config.battery_type == BATTERY_TYPE_ECOFLOW],
        key=lambda b: b.config.priority,
    )
    buffers = [
        b for b in batteries if b.config.battery_type == BATTERY_TYPE_VICTRON_BUFFER
    ]

    if current_hour in charge_hours:
        for battery in ecoflows:
            cfg = battery.config
            if battery.soc_percent >= cfg.max_reserve - 5:
                continue
            target = min(
                cfg.max_reserve,
                max(cfg.normal_reserve + 20, battery.soc_percent + 15),
            )
            battery.charge_now = True
            battery.target_reserve = target
            battery.reason = reason_charge
            actions.append(
                BatteryPlanAction(
                    battery_id=cfg.subentry_id,
                    action="set_backup_reserve",
                    target_value=target,
                    reason=reason_charge,
                )
            )
            break
            break

    if current_hour in discharge_hours:
        for battery in buffers:
            cfg = battery.config
            if battery.soc_percent <= cfg.min_soc:
                continue
            from .battery_model import watts_to_pv_strom

            discharge_w = min(800.0, net_kwh * 1000)
            stage = watts_to_pv_strom(discharge_w)
            battery.discharge_now = True
            battery.target_pv_strom = stage
            battery.reason = reason_discharge
            actions.append(
                BatteryPlanAction(
                    battery_id=cfg.subentry_id,
                    action="discharge_buffer",
                    target_value=stage,
                    reason=reason_discharge,
                )
            )

    for battery in ecoflows:
        if not battery.charge_now:
            battery.target_reserve = battery.config.normal_reserve
    for battery in buffers:
        if not battery.discharge_now:
            battery.target_pv_strom = 0

    return actions

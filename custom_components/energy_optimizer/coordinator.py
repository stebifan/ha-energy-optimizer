"""DataUpdateCoordinator for Energy Optimizer."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .adapters.ecoflow import EcoFlowAdapter
from .adapters.load_shifter import LoadShifterAdapter
from .adapters.victron_buffer import VictronBufferAdapter
from .const import (
    BATTERY_TYPE_ECOFLOW,
    BATTERY_TYPE_VICTRON_BUFFER,
    CONF_BACKUP_RESERVE_ENTITY,
    CONF_BATTERY_TYPE,
    CONF_CAPACITY_KWH,
    CONF_CONSTRAINT_TYPE,
    CONF_CONTROL_ENTITY,
    CONF_DURATION_MINUTES,
    CONF_GRID_EXPORT_ENERGY_ENTITY,
    CONF_GRID_IMPORT_ENERGY_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_HISTORY_DAYS,
    CONF_LOAD_POWER_ENTITY,
    CONF_MAX_RESERVE,
    CONF_MIN_SOC,
    CONF_NORMAL_RESERVE,
    CONF_OPERATION_MODE,
    CONF_OPTIMIZER_ENGINE,
    CONF_POWER_ENTITY,
    CONF_PRIORITY,
    CONF_PROFILE,
    CONF_PV_FORECAST_TODAY_ENTITY,
    CONF_PV_FORECAST_TOMORROW_ENTITY,
    CONF_PV_POWER_ENTITY,
    CONF_PV_POWER_NOW_ENTITY,
    CONF_PV_STATUS_ENTITY,
    CONF_PV_STROM_ENTITY,
    CONF_PV_YIELD_POWER_ENTITY,
    CONF_SOC_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_MAX_RESERVE,
    DEFAULT_MIN_SOC,
    DEFAULT_NORMAL_RESERVE,
    DOMAIN,
    OPERATION_MODE_AUTO,
    OPTIMIZER_ENGINE_HEURISTIC,
    PROFILE_BALANCED,
    SUBENTRY_TYPE_BATTERY,
    SUBENTRY_TYPE_LOAD,
    SUBENTRY_TYPE_PV,
    UPDATE_INTERVAL_SECONDS,
)
from .models.battery_model import BatteryConfig, BatteryState, OptimizerResult
from .models.consumption_forecast import build_load_profile, forecast_load_kwh
from .models.grid_balance import build_matched_hourly_pv, forecast_grid_balance
from .models.load_planner import LoadConfig
from .models.optimizer import optimize
from .models.price_model import (
    cheapest_window_start,
    current_slot,
    hourly_prices,
    parse_epex_data,
    price_rank_today,
)
from .models.pv_forecast import PvPlantForecast, aggregate_pv_forecast
from .models.time_series import next_hours

_LOGGER = logging.getLogger(__name__)


class EnergyOptimizerData:
    """Runtime data container."""

    def __init__(self) -> None:
        """Initialize empty data."""
        self.price_current: float | None = None
        self.price_rank: int | None = None
        self.cheapest_window: str | None = None
        self.slots: list[dict[str, Any]] = []
        self.hourly: list[dict[str, Any]] = []
        self.load_forecast_today: float = 0.0
        self.load_forecast_tomorrow: float = 0.0
        self.load_hourly: list[dict[str, Any]] = []
        self.pv_forecast_today: float = 0.0
        self.pv_forecast_tomorrow: float = 0.0
        self.pv_power_now: float = 0.0
        self.grid_import_power_w: float = 0.0
        self.grid_export_power_w: float = 0.0
        self.grid_import_today_kwh: float = 0.0
        self.grid_export_today_kwh: float = 0.0
        self.grid_import_forecast_today_kwh: float = 0.0
        self.grid_export_forecast_today_kwh: float = 0.0
        self.grid_import_forecast_tomorrow_kwh: float = 0.0
        self.grid_export_forecast_tomorrow_kwh: float = 0.0
        self.grid_import_hourly: list[dict[str, Any]] = []
        self.grid_export_hourly: list[dict[str, Any]] = []
        self.optimizer: OptimizerResult | None = None
        self.batteries: list[BatteryState] = []
        self.loads: list[LoadConfig] = []
        self.load_states: list = []
        self.baseline_cost_eur: float = 0.0
        self.optimized_cost_eur: float = 0.0
        self.last_updated: datetime | None = None


class EnergyOptimizerCoordinator(DataUpdateCoordinator[EnergyOptimizerData]):
    """Coordinator fetching and computing EMS data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.config_entry = entry
        self.data = EnergyOptimizerData()

    async def _async_update_data(self) -> EnergyOptimizerData:
        """Fetch and compute all EMS values."""
        data = EnergyOptimizerData()
        now = dt_util.now()

        try:
            await self._update_prices(data, now)
            await self._update_load_forecast(data, now)
            await self._update_pv_forecast(data)
            self._update_grid(data, now)
            self._load_batteries(data)
            self._load_shiftable_loads(data)
            self._run_optimizer(data, now)
            if self._should_apply():
                await self._apply_plan(data)
        except Exception as err:
            raise UpdateFailed(f"Energy Optimizer update failed: {err}") from err

        data.last_updated = now
        self.data = data
        return data

    async def _update_prices(self, data: EnergyOptimizerData, now: datetime) -> None:
        """Parse EPEX price sensor."""
        price_entity = self.config_entry.data.get("price_entity")
        surcharge = float(self.config_entry.data.get("price_surcharge_eur_kwh", 0))

        state = self.hass.states.get(price_entity)
        if not state:
            return

        raw = state.attributes.get("data")
        slots = parse_epex_data(raw, surcharge)
        hourly = hourly_prices(slots)

        slot = current_slot(slots, now)
        data.price_current = slot.price_eur_kwh if slot else None
        data.price_rank = (
            price_rank_today(slots, data.price_current)
            if data.price_current is not None
            else None
        )
        data.cheapest_window = cheapest_window_start(hourly)
        data.slots = [
            {
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "price_eur_kwh": round(s.price_eur_kwh, 5),
            }
            for s in slots
        ]
        data.hourly = [
            {
                "start": h.start.isoformat(),
                "price_eur_kwh": round(h.price_eur_kwh, 5),
            }
            for h in hourly
        ]

    async def _update_load_forecast(self, data: EnergyOptimizerData, now: datetime) -> None:
        """Build consumption forecast from recorder history."""
        entity_id = self.config_entry.data.get(CONF_LOAD_POWER_ENTITY)
        days = int(self.config_entry.data.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS))
        if not entity_id:
            return

        start = now - timedelta(days=days)
        stat_rows: list[dict[str, Any]] = []

        try:
            from functools import partial

            from homeassistant.components.recorder import history

            states = await self.hass.async_add_executor_job(
                partial(
                    history.get_significant_states,
                    self.hass,
                    start,
                    now,
                    [entity_id],
                    None,
                    True,
                    False,
                )
            )
            for state in states.get(entity_id, []):
                if state.state in ("unknown", "unavailable"):
                    continue
                try:
                    stat_rows.append(
                        {
                            "start": state.last_changed.isoformat(),
                            "state": float(state.state),
                        }
                    )
                except (TypeError, ValueError):
                    continue
        except Exception as err:
            _LOGGER.warning("Load forecast history failed: %s", err)

        profile = build_load_profile(stat_rows)
        if not profile:
            current = self._state_float(entity_id) or 500.0
            profile = {(now.weekday(), hour): current / 1000.0 for hour in range(24)}

        tz = dt_util.get_time_zone(str(self.hass.config.time_zone))
        hour_starts = next_hours(now, 48, tz)
        hourly_load = forecast_load_kwh(profile, hour_starts)

        data.load_hourly = [
            {"start": h.start.isoformat(), "load_kwh": round(h.load_kwh, 3)}
            for h in hourly_load
        ]
        today_hours = [h for h in hourly_load if h.start.date() == now.date()]
        tomorrow_hours = [
            h for h in hourly_load if h.start.date() == (now + timedelta(days=1)).date()
        ]
        data.load_forecast_today = round(sum(h.load_kwh for h in today_hours), 2)
        data.load_forecast_tomorrow = round(sum(h.load_kwh for h in tomorrow_hours), 2)

    async def _update_pv_forecast(self, data: EnergyOptimizerData) -> None:
        """Aggregate PV forecast from config and subentries."""
        today_entity = self.config_entry.data.get(CONF_PV_FORECAST_TODAY_ENTITY)
        tomorrow_entity = self.config_entry.data.get(CONF_PV_FORECAST_TOMORROW_ENTITY)
        power_now_entity = self.config_entry.data.get(CONF_PV_POWER_NOW_ENTITY)

        total_today = self._state_float(today_entity)
        total_tomorrow = self._state_float(tomorrow_entity)
        power_now = self._state_float(power_now_entity) or 0.0

        plants: list[PvPlantForecast] = []
        for subentry in self._subentries(SUBENTRY_TYPE_PV):
            plants.append(
                PvPlantForecast(
                    name=subentry.title or subentry.subentry_id,
                    today_kwh=self._state_float(
                        subentry.data.get(CONF_POWER_ENTITY)
                    )
                    or 0.0,
                    tomorrow_kwh=0.0,
                    power_now_w=self._state_float(
                        subentry.data.get(CONF_PV_POWER_ENTITY)
                    )
                    or 0.0,
                )
            )

        today, tomorrow, pv_now = aggregate_pv_forecast(
            plants, total_today, total_tomorrow
        )
        data.pv_forecast_today = round(today or 0.0, 2)
        data.pv_forecast_tomorrow = round(tomorrow or 0.0, 2)
        data.pv_power_now = round(power_now or pv_now, 0)

    def _update_grid(self, data: EnergyOptimizerData, now: datetime) -> None:
        """Read grid sensors and compute import/export forecasts."""
        from .models.time_series import HourlyBucket

        grid_power = self._state_float(self._config_value(CONF_GRID_POWER_ENTITY))
        import_energy = self._state_float(
            self._config_value(CONF_GRID_IMPORT_ENERGY_ENTITY)
        )
        export_energy = self._state_float(
            self._config_value(CONF_GRID_EXPORT_ENERGY_ENTITY)
        )

        hourly_load = [
            HourlyBucket(
                start=datetime.fromisoformat(item["start"]),
                price_eur_kwh=0.0,
                load_kwh=item["load_kwh"],
            )
            for item in data.load_hourly
        ]
        hourly_pv = build_matched_hourly_pv(
            hourly_load,
            data.pv_forecast_today,
            data.pv_forecast_tomorrow,
            now,
        )
        grid = forecast_grid_balance(
            hourly_load,
            hourly_pv,
            now,
            import_energy_today_kwh=import_energy,
            export_energy_today_kwh=export_energy,
            import_power_w=grid_power,
        )
        data.grid_import_power_w = grid.import_power_w
        data.grid_export_power_w = grid.export_power_w
        data.grid_import_today_kwh = grid.import_today_kwh
        data.grid_export_today_kwh = grid.export_today_kwh
        data.grid_import_forecast_today_kwh = grid.import_forecast_today_kwh
        data.grid_export_forecast_today_kwh = grid.export_forecast_today_kwh
        data.grid_import_forecast_tomorrow_kwh = grid.import_forecast_tomorrow_kwh
        data.grid_export_forecast_tomorrow_kwh = grid.export_forecast_tomorrow_kwh
        data.grid_import_hourly = grid.hourly_import or []
        data.grid_export_hourly = grid.hourly_export or []

    def _load_batteries(self, data: EnergyOptimizerData) -> None:
        """Load battery configs from subentries."""
        batteries: list[BatteryState] = []
        for subentry in self._subentries(SUBENTRY_TYPE_BATTERY):
            cfg = BatteryConfig(
                subentry_id=subentry.subentry_id,
                name=subentry.title or subentry.subentry_id,
                battery_type=subentry.data.get(CONF_BATTERY_TYPE, BATTERY_TYPE_ECOFLOW),
                capacity_kwh=float(subentry.data.get(CONF_CAPACITY_KWH, 1.0)),
                priority=int(subentry.data.get(CONF_PRIORITY, 1)),
                soc_entity=subentry.data.get(CONF_SOC_ENTITY),
                backup_reserve_entity=subentry.data.get(CONF_BACKUP_RESERVE_ENTITY),
                normal_reserve=float(
                    subentry.data.get(CONF_NORMAL_RESERVE, DEFAULT_NORMAL_RESERVE)
                ),
                max_reserve=float(subentry.data.get(CONF_MAX_RESERVE, DEFAULT_MAX_RESERVE)),
                min_soc=float(subentry.data.get(CONF_MIN_SOC, DEFAULT_MIN_SOC)),
                pv_status_entity=subentry.data.get(CONF_PV_STATUS_ENTITY),
                pv_strom_entity=subentry.data.get(CONF_PV_STROM_ENTITY),
                pv_yield_power_entity=subentry.data.get(CONF_PV_YIELD_POWER_ENTITY),
            )
            soc = self._state_float(cfg.soc_entity) or 0.0
            batteries.append(BatteryState(config=cfg, soc_percent=soc))
        data.batteries = sorted(batteries, key=lambda b: b.config.priority)

    def _load_shiftable_loads(self, data: EnergyOptimizerData) -> None:
        """Load shiftable load configs."""
        loads: list[LoadConfig] = []
        for subentry in self._subentries(SUBENTRY_TYPE_LOAD):
            loads.append(
                LoadConfig(
                    subentry_id=subentry.subentry_id,
                    name=subentry.title or subentry.subentry_id,
                    control_entity=subentry.data.get(CONF_CONTROL_ENTITY, ""),
                    priority=int(subentry.data.get(CONF_PRIORITY, 1)),
                    constraint_type=subentry.data.get(CONF_CONSTRAINT_TYPE, "soft"),
                    window_start=subentry.data.get(CONF_WINDOW_START, "00:00"),
                    window_end=subentry.data.get(CONF_WINDOW_END, "23:59"),
                    duration_minutes=int(subentry.data.get(CONF_DURATION_MINUTES, 60)),
                )
            )
        data.loads = sorted(loads, key=lambda load: load.priority)

    def _run_optimizer(self, data: EnergyOptimizerData, now: datetime) -> None:
        """Run heuristic optimizer."""
        from .models.time_series import HourlyBucket

        hourly_price = [
            HourlyBucket(
                start=datetime.fromisoformat(item["start"]),
                price_eur_kwh=item["price_eur_kwh"],
            )
            for item in data.hourly
        ]
        hourly_load = [
            HourlyBucket(
                start=datetime.fromisoformat(item["start"]),
                price_eur_kwh=0.0,
                load_kwh=item["load_kwh"],
            )
            for item in data.load_hourly
        ]
        hourly_pv = build_matched_hourly_pv(
            hourly_load,
            data.pv_forecast_today,
            data.pv_forecast_tomorrow,
            now,
        )

        profile = self.config_entry.options.get(
            CONF_PROFILE, self.config_entry.data.get(CONF_PROFILE, PROFILE_BALANCED)
        )
        engine = self.config_entry.options.get(
            CONF_OPTIMIZER_ENGINE,
            self.config_entry.data.get(CONF_OPTIMIZER_ENGINE, OPTIMIZER_ENGINE_HEURISTIC),
        )
        data.optimizer = optimize(
            profile=profile,
            hourly_prices=hourly_price,
            hourly_load=hourly_load,
            hourly_pv=hourly_pv,
            batteries=data.batteries,
            loads=data.loads,
            now=now,
            engine=engine,
        )
        if data.optimizer:
            data.load_states = data.optimizer.load_states
            data.baseline_cost_eur = data.optimizer.baseline_cost_eur
            data.optimized_cost_eur = data.optimizer.optimized_cost_eur

    def _should_apply(self) -> bool:
        """Return True if plan should be applied to hardware."""
        mode = self.config_entry.options.get(
            CONF_OPERATION_MODE,
            self.config_entry.data.get(CONF_OPERATION_MODE),
        )
        return mode == OPERATION_MODE_AUTO

    async def _apply_plan(self, data: EnergyOptimizerData) -> None:
        """Apply optimizer actions via device adapters."""
        if not data.optimizer:
            return
        for action in data.optimizer.battery_actions:
            battery = next(
                (b for b in data.batteries if b.config.subentry_id == action.battery_id),
                None,
            )
            if not battery:
                continue
            if battery.config.battery_type == BATTERY_TYPE_ECOFLOW:
                await EcoFlowAdapter(self.hass, battery).apply_action(action)
            elif battery.config.battery_type == BATTERY_TYPE_VICTRON_BUFFER:
                await VictronBufferAdapter(self.hass, battery).apply_action(action)

        for load_action in data.optimizer.load_actions:
            load = next(
                (item for item in data.loads if item.subentry_id == load_action.load_id),
                None,
            )
            if not load:
                continue
            adapter = LoadShifterAdapter(self.hass, load)
            if load_action.action == "turn_on":
                await adapter.turn_on(load_action.reason)
            elif load_action.action == "turn_off":
                await adapter.turn_off(load_action.reason)

    async def async_recalculate(self) -> None:
        """Force refresh."""
        await self.async_request_refresh()

    async def async_apply_plan(self) -> None:
        """Manually apply current plan."""
        await self._apply_plan(self.data)

    async def async_set_profile(self, profile: str) -> None:
        """Update optimization profile in options."""
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={**self.config_entry.options, CONF_PROFILE: profile},
        )
        await self.async_request_refresh()

    def _config_value(self, key: str) -> Any:
        """Read config value from options with fallback to entry data."""
        if key in self.config_entry.options:
            return self.config_entry.options[key]
        return self.config_entry.data.get(key)

    def _subentries(self, subentry_type: str) -> list[ConfigSubentry]:
        """Return config subentries of a type."""
        return [
            sub
            for sub in self.config_entry.subentries.values()
            if sub.subentry_type == subentry_type
        ]

    def _state_float(self, entity_id: str | None) -> float | None:
        """Read entity state as float."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

"""Constants for the Energy Optimizer integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "energy_optimizer"
PLATFORMS: Final = ["sensor", "binary_sensor", "select", "switch"]

CONF_PRICE_ENTITY: Final = "price_entity"
CONF_PRICE_SURCHARGE_EUR_KWH: Final = "price_surcharge_eur_kwh"
CONF_LOAD_POWER_ENTITY: Final = "load_power_entity"
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_HISTORY_DAYS: Final = "history_days"
CONF_OPERATION_MODE: Final = "operation_mode"
CONF_PROFILE: Final = "profile"
CONF_PV_FORECAST_TODAY_ENTITY: Final = "pv_forecast_today_entity"
CONF_PV_FORECAST_TOMORROW_ENTITY: Final = "pv_forecast_tomorrow_entity"
CONF_PV_POWER_NOW_ENTITY: Final = "pv_power_now_entity"
CONF_GRID_POWER_ENTITY: Final = "grid_power_entity"
CONF_GRID_IMPORT_ENERGY_ENTITY: Final = "grid_import_energy_entity"
CONF_GRID_EXPORT_ENERGY_ENTITY: Final = "grid_export_energy_entity"

SUBENTRY_TYPE_BATTERY: Final = "battery"
SUBENTRY_TYPE_PV: Final = "pv"
SUBENTRY_TYPE_LOAD: Final = "load"

CONF_BATTERY_TYPE: Final = "battery_type"
CONF_CAPACITY_KWH: Final = "capacity_kwh"
CONF_PRIORITY: Final = "priority"
CONF_SOC_ENTITY: Final = "soc_entity"
CONF_BACKUP_RESERVE_ENTITY: Final = "backup_reserve_entity"
CONF_NORMAL_RESERVE: Final = "normal_reserve"
CONF_MAX_RESERVE: Final = "max_reserve"
CONF_PV_POWER_ENTITY: Final = "pv_power_entity"
CONF_BATTERY_POWER_ENTITY: Final = "battery_power_entity"
CONF_SELF_POWERED_ENTITY: Final = "self_powered_entity"
CONF_AI_MODE_ENTITY: Final = "ai_mode_entity"
CONF_PV_STATUS_ENTITY: Final = "pv_status_entity"
CONF_PV_STROM_ENTITY: Final = "pv_strom_entity"
CONF_PV_YIELD_POWER_ENTITY: Final = "pv_yield_power_entity"
CONF_MIN_SOC: Final = "min_soc"

CONF_ENERGY_ENTITY: Final = "energy_entity"
CONF_POWER_ENTITY: Final = "power_entity"
CONF_CONTROL_ENTITY: Final = "control_entity"
CONF_WINDOW_START: Final = "window_start"
CONF_WINDOW_END: Final = "window_end"
CONF_CONSTRAINT_TYPE: Final = "constraint_type"
CONF_DURATION_MINUTES: Final = "duration_minutes"
CONF_OPTIMIZER_ENGINE: Final = "optimizer_engine"

OPTIMIZER_ENGINE_HEURISTIC: Final = "heuristic"
OPTIMIZER_ENGINE_DP: Final = "dp"

OPTIMIZER_ENGINES: Final = [OPTIMIZER_ENGINE_HEURISTIC, OPTIMIZER_ENGINE_DP]

BATTERY_TYPE_ECOFLOW: Final = "ecoflow"
BATTERY_TYPE_VICTRON_BUFFER: Final = "victron_buffer"
BATTERY_TYPE_GENERIC: Final = "generic"

OPERATION_MODE_MONITOR: Final = "monitor"
OPERATION_MODE_VISUALIZE: Final = "visualize"
OPERATION_MODE_AUTO: Final = "auto"
OPERATION_MODE_SIGNALS_ONLY: Final = "signals_only"

OPERATION_MODES: Final = [
    OPERATION_MODE_MONITOR,
    OPERATION_MODE_VISUALIZE,
    OPERATION_MODE_AUTO,
    OPERATION_MODE_SIGNALS_ONLY,
]

PROFILE_COST_MIN: Final = "cost_min"
PROFILE_SELF_SUFFICIENCY: Final = "self_sufficiency"
PROFILE_BALANCED: Final = "balanced"
PROFILE_WINTER: Final = "winter"
PROFILE_SUMMER: Final = "summer"
PROFILE_BACKUP: Final = "backup"
PROFILE_CUSTOM: Final = "custom"

PROFILES: Final = [
    PROFILE_COST_MIN,
    PROFILE_SELF_SUFFICIENCY,
    PROFILE_BALANCED,
    PROFILE_WINTER,
    PROFILE_SUMMER,
    PROFILE_BACKUP,
    PROFILE_CUSTOM,
]

CONSTRAINT_HARD: Final = "hard"
CONSTRAINT_SOFT: Final = "soft"

DEFAULT_HISTORY_DAYS: Final = 30
DEFAULT_NORMAL_RESERVE: Final = 3
DEFAULT_MAX_RESERVE: Final = 100
DEFAULT_MIN_SOC: Final = 5
PV_STROM_MAX_STAGE: Final = 10
PV_STROM_WATTS_PER_STAGE: Final = 80

UPDATE_INTERVAL_SECONDS: Final = 300
RESERVE_CHANGE_COOLDOWN_SECONDS: Final = 900

SERVICE_RECALCULATE: Final = "recalculate"
SERVICE_APPLY_PLAN: Final = "apply_plan"
SERVICE_SET_PROFILE: Final = "set_profile"

ATTR_SLOTS: Final = "slots"
ATTR_HOURLY: Final = "hourly"
ATTR_FORECAST: Final = "forecast"
ATTR_PLAN: Final = "plan"
ATTR_GRID_IMPORT: Final = "grid_import_hourly"
ATTR_GRID_EXPORT: Final = "grid_export_hourly"
ATTR_REASON: Final = "reason"

"""Config flow for Energy Optimizer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
)
from homeassistant.helpers import selector

from .const import (
    BATTERY_TYPE_ECOFLOW,
    BATTERY_TYPE_GENERIC,
    BATTERY_TYPE_VICTRON_BUFFER,
    CONF_BACKUP_RESERVE_ENTITY,
    CONF_BATTERY_TYPE,
    CONF_CAPACITY_KWH,
    CONF_CONSTRAINT_TYPE,
    CONF_CONTROL_ENTITY,
    CONF_DURATION_MINUTES,
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
    CONF_WEATHER_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    CONSTRAINT_HARD,
    CONSTRAINT_SOFT,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_MAX_RESERVE,
    DEFAULT_MIN_SOC,
    DEFAULT_NORMAL_RESERVE,
    DOMAIN,
    OPERATION_MODE_MONITOR,
    OPERATION_MODES,
    OPTIMIZER_ENGINE_HEURISTIC,
    OPTIMIZER_ENGINES,
    PROFILE_BALANCED,
    PROFILES,
    SUBENTRY_TYPE_BATTERY,
    SUBENTRY_TYPE_LOAD,
    SUBENTRY_TYPE_PV,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOAD_POWER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required("price_entity"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_PV_FORECAST_TODAY_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        ),
        vol.Optional(CONF_PV_FORECAST_TOMORROW_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        ),
        vol.Optional(CONF_PV_POWER_NOW_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="weather")
        ),
        vol.Optional("price_surcharge_eur_kwh", default=0.0): vol.Coerce(float),
        vol.Optional(CONF_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS): vol.Coerce(int),
        vol.Optional(CONF_OPERATION_MODE, default=OPERATION_MODE_MONITOR): vol.In(
            OPERATION_MODES
        ),
        vol.Optional(CONF_PROFILE, default=PROFILE_BALANCED): vol.In(PROFILES),
    }
)


class EnergyOptimizerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    def async_get_supported_subentry_types(
        entry: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported subentry flows."""
        return {
            SUBENTRY_TYPE_BATTERY: BatterySubentryFlowHandler,
            SUBENTRY_TYPE_PV: PvSubentryFlowHandler,
            SUBENTRY_TYPE_LOAD: LoadSubentryFlowHandler,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Energy Optimizer",
                data=user_input,
                options={
                    CONF_OPERATION_MODE: user_input.get(
                        CONF_OPERATION_MODE, OPERATION_MODE_MONITOR
                    ),
                    CONF_PROFILE: user_input.get(CONF_PROFILE, PROFILE_BALANCED),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return options flow."""
        return EnergyOptimizerOptionsFlow(config_entry)


class EnergyOptimizerOptionsFlow(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_OPERATION_MODE,
                        default=self.config_entry.options.get(
                            CONF_OPERATION_MODE,
                            self.config_entry.data.get(CONF_OPERATION_MODE),
                        ),
                    ): vol.In(OPERATION_MODES),
                    vol.Optional(
                        CONF_PROFILE,
                        default=self.config_entry.options.get(
                            CONF_PROFILE,
                            self.config_entry.data.get(CONF_PROFILE, PROFILE_BALANCED),
                        ),
                    ): vol.In(PROFILES),
                    vol.Optional(
                        CONF_OPTIMIZER_ENGINE,
                        default=self.config_entry.options.get(
                            CONF_OPTIMIZER_ENGINE,
                            self.config_entry.data.get(
                                CONF_OPTIMIZER_ENGINE, OPTIMIZER_ENGINE_HEURISTIC
                            ),
                        ),
                    ): vol.In(OPTIMIZER_ENGINES),
                }
            ),
        )


class BatterySubentryFlowHandler(ConfigSubentryFlow):
    """Add or edit a battery subentry."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure battery."""
        if user_input is not None:
            title = user_input.pop("name")
            return self.async_create_entry(title=title, data=user_input)

        battery_type = vol.In(
            [BATTERY_TYPE_ECOFLOW, BATTERY_TYPE_VICTRON_BUFFER, BATTERY_TYPE_GENERIC]
        )
        schema: dict[Any, Any] = {
            vol.Required("name"): str,
            vol.Required(CONF_BATTERY_TYPE, default=BATTERY_TYPE_ECOFLOW): battery_type,
            vol.Required(CONF_CAPACITY_KWH): vol.Coerce(float),
            vol.Optional(CONF_PRIORITY, default=1): vol.Coerce(int),
            vol.Required(CONF_SOC_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }

        schema.update(
            {
                vol.Optional(CONF_NORMAL_RESERVE, default=DEFAULT_NORMAL_RESERVE): vol.Coerce(
                    float
                ),
                vol.Optional(CONF_MAX_RESERVE, default=DEFAULT_MAX_RESERVE): vol.Coerce(
                    float
                ),
                vol.Optional(CONF_MIN_SOC, default=DEFAULT_MIN_SOC): vol.Coerce(float),
                vol.Optional(CONF_BACKUP_RESERVE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="number")
                ),
                vol.Optional(CONF_PV_STATUS_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_number")
                ),
                vol.Optional(CONF_PV_STROM_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="input_number")
                ),
                vol.Optional(CONF_PV_YIELD_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))


class PvSubentryFlowHandler(ConfigSubentryFlow):
    """Add or edit a PV plant subentry."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure PV plant."""
        if user_input is not None:
            title = user_input.pop("name")
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Optional(CONF_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="energy"
                        )
                    ),
                    vol.Optional(CONF_PV_POWER_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="power"
                        )
                    ),
                }
            ),
        )


class LoadSubentryFlowHandler(ConfigSubentryFlow):
    """Add or edit a shiftable load subentry."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure shiftable load."""
        if user_input is not None:
            title = user_input.pop("name")
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required(CONF_CONTROL_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch", "script"])
                    ),
                    vol.Optional(CONF_PRIORITY, default=1): vol.Coerce(int),
                    vol.Optional(CONF_CONSTRAINT_TYPE, default=CONSTRAINT_SOFT): vol.In(
                        [CONSTRAINT_HARD, CONSTRAINT_SOFT]
                    ),
                    vol.Optional(CONF_WINDOW_START, default="08:00"): str,
                    vol.Optional(CONF_WINDOW_END, default="20:00"): str,
                    vol.Optional(CONF_DURATION_MINUTES, default=60): vol.Coerce(int),
                }
            ),
        )

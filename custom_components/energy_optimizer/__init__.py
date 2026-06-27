"""The Energy Optimizer integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS

__all__ = ["DOMAIN", "async_setup", "async_setup_entry", "async_unload_entry"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Energy Optimizer from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Optimizer from config entry."""
    from .coordinator import EnergyOptimizerCoordinator

    coordinator = EnergyOptimizerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_recalculate(_call) -> None:
        await coordinator.async_recalculate()

    async def handle_apply_plan(_call) -> None:
        await coordinator.async_apply_plan()

    async def handle_set_profile(call) -> None:
        from .const import CONF_PROFILE

        profile = call.data.get(CONF_PROFILE)
        if profile:
            await coordinator.async_set_profile(profile)

    from .const import SERVICE_APPLY_PLAN, SERVICE_RECALCULATE, SERVICE_SET_PROFILE

    hass.services.async_register(DOMAIN, SERVICE_RECALCULATE, handle_recalculate)
    hass.services.async_register(DOMAIN, SERVICE_APPLY_PLAN, handle_apply_plan)
    hass.services.async_register(DOMAIN, SERVICE_SET_PROFILE, handle_set_profile)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Energy Optimizer."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

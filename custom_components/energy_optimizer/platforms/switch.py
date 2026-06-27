"""Switch platform for Energy Optimizer."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN, OPERATION_MODE_AUTO
from ..coordinator import EnergyOptimizerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""
    coordinator: EnergyOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EnergyOptimizerAutoSwitch(coordinator, entry)])


class EnergyOptimizerAutoSwitch(
    CoordinatorEntity[EnergyOptimizerCoordinator], SwitchEntity
):
    """Toggle auto mode quickly."""

    _attr_has_entity_name = True
    _attr_name = "Automatik aktiv"
    _attr_icon = "mdi:robot"

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_auto_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energy Optimizer",
            manufacturer="Energy Optimizer",
        )

    @property
    def is_on(self) -> bool:
        """Return True if auto mode enabled."""
        from ..const import CONF_OPERATION_MODE

        mode = self._entry.options.get(
            CONF_OPERATION_MODE,
            self._entry.data.get(CONF_OPERATION_MODE),
        )
        return mode == OPERATION_MODE_AUTO

    async def async_turn_on(self, **kwargs) -> None:
        """Enable auto mode."""
        from ..const import CONF_OPERATION_MODE

        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_OPERATION_MODE: OPERATION_MODE_AUTO},
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable auto mode (monitor)."""
        from ..const import CONF_OPERATION_MODE, OPERATION_MODE_MONITOR

        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **self._entry.options,
                CONF_OPERATION_MODE: OPERATION_MODE_MONITOR,
            },
        )
        await self.coordinator.async_request_refresh()

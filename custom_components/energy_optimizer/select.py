"""Select platform for Energy Optimizer."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_OPERATION_MODE, CONF_PROFILE, DOMAIN, OPERATION_MODES, PROFILES
from .coordinator import EnergyOptimizerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up selects."""
    coordinator: EnergyOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EnergyOptimizerProfileSelect(coordinator, entry),
            EnergyOptimizerModeSelect(coordinator, entry),
        ]
    )


class EnergyOptimizerSelect(CoordinatorEntity[EnergyOptimizerCoordinator], SelectEntity):
    """Base select entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
        unique_suffix: str,
        name: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energy Optimizer",
            manufacturer="Energy Optimizer",
        )


class EnergyOptimizerProfileSelect(EnergyOptimizerSelect):
    """Optimization profile selector."""

    _attr_options = list(PROFILES)

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "profile", "Optimierungsprofil")

    @property
    def current_option(self) -> str | None:
        """Return current profile."""
        return self._entry.options.get(
            CONF_PROFILE,
            self._entry.data.get(CONF_PROFILE),
        )

    async def async_select_option(self, option: str) -> None:
        """Set profile."""
        await self.coordinator.async_set_profile(option)


class EnergyOptimizerModeSelect(EnergyOptimizerSelect):
    """Operation mode selector."""

    _attr_options = list(OPERATION_MODES)

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "operation_mode", "Betriebsmodus")

    @property
    def current_option(self) -> str | None:
        """Return current mode."""
        return self._entry.options.get(
            CONF_OPERATION_MODE,
            self._entry.data.get(CONF_OPERATION_MODE),
        )

    async def async_select_option(self, option: str) -> None:
        """Set operation mode."""
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_OPERATION_MODE: option},
        )
        await self.coordinator.async_request_refresh()

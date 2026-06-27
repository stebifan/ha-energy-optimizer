"""Binary sensor platform for Energy Optimizer."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import (
    BATTERY_TYPE_ECOFLOW,
    BATTERY_TYPE_VICTRON_BUFFER,
    CONF_BATTERY_TYPE,
    DOMAIN,
    SUBENTRY_TYPE_BATTERY,
    SUBENTRY_TYPE_LOAD,
)
from ..coordinator import EnergyOptimizerCoordinator
from ..models.battery_model import BatteryState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from config subentries."""
    coordinator: EnergyOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for subentry in entry.subentries.values():
        slug = subentry.subentry_id.replace("-", "_")[:20]
        if subentry.subentry_type == SUBENTRY_TYPE_BATTERY:
            battery_type = subentry.data.get(CONF_BATTERY_TYPE, BATTERY_TYPE_ECOFLOW)
            if battery_type == BATTERY_TYPE_ECOFLOW:
                entities.append(
                    EnergyOptimizerBatteryChargeSensor(coordinator, entry, subentry, slug)
                )
            elif battery_type == BATTERY_TYPE_VICTRON_BUFFER:
                entities.append(
                    EnergyOptimizerBatteryDischargeSensor(
                        coordinator, entry, subentry, slug
                    )
                )
        elif subentry.subentry_type == SUBENTRY_TYPE_LOAD:
            entities.append(
                EnergyOptimizerLoadRunSensor(coordinator, entry, subentry, slug)
            )
    async_add_entities(entities)


class EnergyOptimizerBatteryBinarySensor(
    CoordinatorEntity[EnergyOptimizerCoordinator], BinarySensorEntity
):
    """Base battery binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        slug: str,
        sensor_type: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._battery_id = subentry.subentry_id
        self._battery_name = subentry.title or subentry.subentry_id
        self._attr_unique_id = f"{entry.entry_id}_{slug}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id, subentry.subentry_id)},
            name=self._battery_name,
            manufacturer="Energy Optimizer",
        )

    def _find_battery(self) -> BatteryState | None:
        return next(
            (
                b
                for b in self.coordinator.data.batteries
                if b.config.subentry_id == self._battery_id
            ),
            None,
        )


class EnergyOptimizerBatteryChargeSensor(EnergyOptimizerBatteryBinarySensor):
    """EcoFlow charge recommendation."""

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        slug: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, subentry, slug, "charge")
        self._attr_name = "Netzladen empfohlen"

    @property
    def is_on(self) -> bool:
        """Return charge recommendation."""
        battery = self._find_battery()
        return bool(battery and battery.charge_now)


class EnergyOptimizerBatteryDischargeSensor(EnergyOptimizerBatteryBinarySensor):
    """Victron buffer discharge recommendation."""

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        slug: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, subentry, slug, "discharge")
        self._attr_name = "Einspeisung empfohlen"

    @property
    def is_on(self) -> bool:
        """Return discharge recommendation."""
        battery = self._find_battery()
        return bool(battery and battery.discharge_now)


class EnergyOptimizerLoadRunSensor(
    CoordinatorEntity[EnergyOptimizerCoordinator], BinarySensorEntity
):
    """Shiftable load run recommendation."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
        slug: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._load_id = subentry.subentry_id
        self._load_name = subentry.title or subentry.subentry_id
        self._attr_unique_id = f"{entry.entry_id}_{slug}_load_run"
        self._attr_name = "Lauf empfohlen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id, subentry.subentry_id)},
            name=self._load_name,
            manufacturer="Energy Optimizer",
        )

    def _find_state(self):
        return next(
            (
                item
                for item in self.coordinator.data.load_states
                if item.config.subentry_id == self._load_id
            ),
            None,
        )

    @property
    def is_on(self) -> bool:
        """Return run recommendation."""
        state = self._find_state()
        return bool(state and state.run_now)

    @property
    def extra_state_attributes(self) -> dict:
        """Return schedule info."""
        state = self._find_state()
        if not state:
            return {}
        return {
            "scheduled_start": state.scheduled_start,
            "reason": state.reason,
        }

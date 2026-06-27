"""Sensor platform for Energy Optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_FORECAST,
    ATTR_HOURLY,
    ATTR_PLAN,
    ATTR_SLOTS,
    DOMAIN,
)
from .coordinator import EnergyOptimizerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: EnergyOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EnergyOptimizerPriceSensor(coordinator, entry),
            EnergyOptimizerPriceRankSensor(coordinator, entry),
            EnergyOptimizerLoadTodaySensor(coordinator, entry),
            EnergyOptimizerLoadTomorrowSensor(coordinator, entry),
            EnergyOptimizerPvTodaySensor(coordinator, entry),
            EnergyOptimizerPvTomorrowSensor(coordinator, entry),
            EnergyOptimizerPvNowSensor(coordinator, entry),
            EnergyOptimizerSavingsSensor(coordinator, entry),
            EnergyOptimizerBaselineCostSensor(coordinator, entry),
            EnergyOptimizerOptimizedCostSensor(coordinator, entry),
            EnergyOptimizerPlanSensor(coordinator, entry),
        ]
    )


class EnergyOptimizerEntity(CoordinatorEntity[EnergyOptimizerCoordinator], SensorEntity):
    """Base sensor."""

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


class EnergyOptimizerPriceSensor(EnergyOptimizerEntity):
    """Current electricity price."""

    _attr_native_unit_of_measurement = "€/kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "price_current", "Strompreis aktuell")

    @property
    def native_value(self) -> float | None:
        """Return current price."""
        return self.coordinator.data.price_current

    @property
    def extra_state_attributes(self) -> dict:
        """Return price slots."""
        return {
            ATTR_SLOTS: self.coordinator.data.slots,
            ATTR_HOURLY: self.coordinator.data.hourly,
            "cheapest_window": self.coordinator.data.cheapest_window,
        }


class EnergyOptimizerPriceRankSensor(EnergyOptimizerEntity):
    """Price rank today."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "price_rank", "Strompreis Rang heute")

    @property
    def native_value(self) -> int | None:
        """Return rank."""
        return self.coordinator.data.price_rank


class EnergyOptimizerLoadTodaySensor(EnergyOptimizerEntity):
    """Load forecast today."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry, "load_forecast_today", "Verbrauchsprognose heute"
        )

    @property
    def native_value(self) -> float:
        """Return forecast."""
        return self.coordinator.data.load_forecast_today

    @property
    def extra_state_attributes(self) -> dict:
        """Return hourly forecast."""
        return {ATTR_FORECAST: self.coordinator.data.load_hourly}


class EnergyOptimizerLoadTomorrowSensor(EnergyOptimizerEntity):
    """Load forecast tomorrow."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry, "load_forecast_tomorrow", "Verbrauchsprognose morgen"
        )

    @property
    def native_value(self) -> float:
        """Return forecast."""
        return self.coordinator.data.load_forecast_tomorrow


class EnergyOptimizerPvTodaySensor(EnergyOptimizerEntity):
    """PV forecast today."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "pv_forecast_today", "PV Prognose heute")

    @property
    def native_value(self) -> float:
        """Return forecast."""
        return self.coordinator.data.pv_forecast_today


class EnergyOptimizerPvTomorrowSensor(EnergyOptimizerEntity):
    """PV forecast tomorrow."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry, "pv_forecast_tomorrow", "PV Prognose morgen"
        )

    @property
    def native_value(self) -> float:
        """Return forecast."""
        return self.coordinator.data.pv_forecast_tomorrow


class EnergyOptimizerPvNowSensor(EnergyOptimizerEntity):
    """PV power now."""

    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "pv_power_now", "PV Leistung jetzt")

    @property
    def native_value(self) -> float:
        """Return power."""
        return self.coordinator.data.pv_power_now


class EnergyOptimizerSavingsSensor(EnergyOptimizerEntity):
    """Estimated savings."""

    _attr_native_unit_of_measurement = "€"

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator, entry, "estimated_savings", "Geschätzte Einsparung heute"
        )

    @property
    def native_value(self) -> float:
        """Return savings."""
        if self.coordinator.data.optimizer:
            return self.coordinator.data.optimizer.estimated_savings_eur
        return 0.0


class EnergyOptimizerBaselineCostSensor(EnergyOptimizerEntity):
    """Baseline cost without optimization."""

    _attr_native_unit_of_measurement = "€"

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "baseline_cost", "Kosten Baseline heute")

    @property
    def native_value(self) -> float:
        """Return baseline cost."""
        return self.coordinator.data.baseline_cost_eur


class EnergyOptimizerOptimizedCostSensor(EnergyOptimizerEntity):
    """Optimized cost estimate."""

    _attr_native_unit_of_measurement = "€"

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "optimized_cost", "Kosten optimiert heute")

    @property
    def native_value(self) -> float:
        """Return optimized cost."""
        return self.coordinator.data.optimized_cost_eur


class EnergyOptimizerPlanSensor(EnergyOptimizerEntity):
    """Next planned action."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: EnergyOptimizerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "next_action", "Nächste Aktion")

    @property
    def native_value(self) -> str:
        """Return next action."""
        if self.coordinator.data.optimizer:
            return self.coordinator.data.optimizer.next_action
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Return full plan."""
        if not self.coordinator.data.optimizer:
            return {}
        return {
            ATTR_PLAN: self.coordinator.data.optimizer.plan,
            "next_action_at": self.coordinator.data.optimizer.next_action_at,
        }

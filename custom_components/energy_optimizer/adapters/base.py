"""Base adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.core import HomeAssistant

from ..models.battery_model import BatteryPlanAction, BatteryState


class BaseAdapter(ABC):
    """Base class for device control adapters."""

    def __init__(self, hass: HomeAssistant, battery: BatteryState) -> None:
        """Initialize adapter."""
        self.hass = hass
        self.battery = battery

    @abstractmethod
    async def apply_action(self, action: BatteryPlanAction) -> None:
        """Apply a planned action."""

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

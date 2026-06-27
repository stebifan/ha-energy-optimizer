"""Shiftable load adapter."""

from __future__ import annotations

import logging

from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.core import HomeAssistant

from ..models.load_planner import LoadConfig

_LOGGER = logging.getLogger(__name__)


class LoadShifterAdapter:
    """Turn shiftable loads on/off."""

    def __init__(self, hass: HomeAssistant, load: LoadConfig) -> None:
        """Initialize load adapter."""
        self.hass = hass
        self.load = load

    async def turn_on(self, reason: str = "") -> None:
        """Enable load."""
        if not self.load.control_entity:
            return
        domain = self.load.control_entity.split(".")[0]
        if domain == SWITCH_DOMAIN:
            await self.hass.services.async_call(
                SWITCH_DOMAIN,
                "turn_on",
                {"entity_id": self.load.control_entity},
                blocking=True,
            )
        elif domain == SCRIPT_DOMAIN:
            await self.hass.services.async_call(
                SCRIPT_DOMAIN,
                "turn_on",
                {"entity_id": self.load.control_entity},
                blocking=True,
            )
        _LOGGER.debug("Load %s ON — %s", self.load.name, reason)

    async def turn_off(self, reason: str = "") -> None:
        """Disable load."""
        if not self.load.control_entity:
            return
        domain = self.load.control_entity.split(".")[0]
        if domain == SWITCH_DOMAIN:
            await self.hass.services.async_call(
                SWITCH_DOMAIN,
                "turn_off",
                {"entity_id": self.load.control_entity},
                blocking=True,
            )
            _LOGGER.debug("Load %s OFF — %s", self.load.name, reason)

"""Control EcoFlow via backup reserve level."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.util import dt as dt_util

from ..const import RESERVE_CHANGE_COOLDOWN_SECONDS
from ..models.battery_model import BatteryPlanAction
from .base import BaseAdapter

_LOGGER = logging.getLogger(__name__)

_last_reserve_change: dict[str, datetime] = {}


class EcoFlowAdapter(BaseAdapter):
    """Control EcoFlow via backup reserve level."""

    async def apply_action(self, action: BatteryPlanAction) -> None:
        """Set backup reserve to trigger grid charging."""
        entity = self.battery.config.backup_reserve_entity
        if not entity or action.target_value is None:
            return

        battery_id = self.battery.config.subentry_id
        now = dt_util.utcnow()
        last_change = _last_reserve_change.get(battery_id)
        if last_change and now - last_change < timedelta(
            seconds=RESERVE_CHANGE_COOLDOWN_SECONDS
        ):
            _LOGGER.debug(
                "EcoFlow %s: reserve change skipped (cooldown)",
                self.battery.config.name,
            )
            return

        await self.hass.services.async_call(
            NUMBER_DOMAIN,
            "set_value",
            {"entity_id": entity, "value": float(action.target_value)},
            blocking=True,
        )
        _last_reserve_change[battery_id] = now
        _LOGGER.debug(
            "EcoFlow %s: backup reserve -> %s (%s)",
            self.battery.config.name,
            action.target_value,
            action.reason,
        )

    async def reset_to_normal(self) -> None:
        """Reset backup reserve to configured normal level."""
        entity = self.battery.config.backup_reserve_entity
        if not entity:
            return
        await self.hass.services.async_call(
            NUMBER_DOMAIN,
            "set_value",
            {"entity_id": entity, "value": float(self.battery.config.normal_reserve)},
            blocking=True,
        )

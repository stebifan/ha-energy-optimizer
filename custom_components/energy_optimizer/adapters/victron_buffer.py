"""Victron buffer adapter — discharge via pv_status / pv_strom helpers."""

from __future__ import annotations

import logging

from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN

from ..const import PV_STROM_MAX_STAGE
from ..models.battery_model import BatteryPlanAction, pv_strom_to_watts
from .base import BaseAdapter

_LOGGER = logging.getLogger(__name__)


class VictronBufferAdapter(BaseAdapter):
    """Control passive Victron buffer discharge."""

    async def apply_action(self, action: BatteryPlanAction) -> None:
        """Apply discharge stage and feed-in switch."""
        status_entity = self.battery.config.pv_status_entity
        strom_entity = self.battery.config.pv_strom_entity
        if not status_entity or not strom_entity:
            return

        stage = int(action.target_value or 0)
        stage = max(0, min(PV_STROM_MAX_STAGE, stage))

        if self.battery.soc_percent <= self.battery.config.min_soc:
            stage = 0

        await self.hass.services.async_call(
            INPUT_NUMBER_DOMAIN,
            "set_value",
            {"entity_id": strom_entity, "value": float(stage)},
            blocking=True,
        )

        status = 1.0 if stage > 0 else 0.0
        await self.hass.services.async_call(
            INPUT_NUMBER_DOMAIN,
            "set_value",
            {"entity_id": status_entity, "value": status},
            blocking=True,
        )
        _LOGGER.debug(
            "Victron buffer: pv_status=%s pv_strom=%s (%sW) — %s",
            status,
            stage,
            pv_strom_to_watts(stage),
            action.reason,
        )

    async def stop_discharge(self) -> None:
        """Turn off feed-in."""
        await self.apply_action(
            BatteryPlanAction(
                battery_id=self.battery.config.subentry_id,
                action="stop",
                target_value=0,
                reason="Entladen beendet",
            )
        )

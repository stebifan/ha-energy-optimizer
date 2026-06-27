"""Pytest configuration — minimal Home Assistant stubs for unit tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock


def _mock_module(name: str) -> MagicMock:
    module = MagicMock()
    module.__name__ = name
    sys.modules[name] = module
    return module


for path in (
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.typing",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.select",
    "homeassistant.components.switch",
    "homeassistant.components.number",
    "homeassistant.components.script",
    "homeassistant.components.input_number",
    "homeassistant.components.recorder",
    "homeassistant.components.recorder.history",
    "homeassistant.const",
    "homeassistant.util",
    "homeassistant.util.dt",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.selector",
    "voluptuous",
):
    if path not in sys.modules:
        _mock_module(path)

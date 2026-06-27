"""Tests for grid import/export balance."""

from datetime import datetime, timedelta

import pytest

from custom_components.energy_optimizer.models.grid_balance import (
    build_matched_hourly_pv,
    forecast_grid_balance,
    split_grid_power,
)
from custom_components.energy_optimizer.models.time_series import HourlyBucket


def test_split_grid_power():
    """Positive import, negative export, None -> zero."""
    assert split_grid_power(1500.0) == (1500.0, 0.0)
    assert split_grid_power(-800.0) == (0.0, 800.0)
    assert split_grid_power(None) == (0.0, 0.0)
    assert split_grid_power(0.0) == (0.0, 0.0)


def test_forecast_grid_balance_today():
    """Import when load exceeds PV, export when PV exceeds load."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    load_hourly = [
        HourlyBucket(start=datetime(2026, 6, 27, 8, 0, 0), price_eur_kwh=0.1, load_kwh=2.0),
        HourlyBucket(start=datetime(2026, 6, 27, 9, 0, 0), price_eur_kwh=0.1, load_kwh=1.0),
        HourlyBucket(start=datetime(2026, 6, 28, 8, 0, 0), price_eur_kwh=0.1, load_kwh=3.0),
    ]
    hourly_pv = [
        HourlyBucket(start=datetime(2026, 6, 27, 8, 0, 0), price_eur_kwh=0.0, pv_kwh=0.5),
        HourlyBucket(start=datetime(2026, 6, 27, 9, 0, 0), price_eur_kwh=0.0, pv_kwh=2.0),
        HourlyBucket(start=datetime(2026, 6, 28, 8, 0, 0), price_eur_kwh=0.0, pv_kwh=1.0),
    ]
    result = forecast_grid_balance(
        load_hourly,
        hourly_pv,
        now,
        import_energy_today_kwh=4.5,
        export_energy_today_kwh=1.2,
        import_power_w=900.0,
    )
    assert result.import_power_w == pytest.approx(900.0)
    assert result.export_power_w == pytest.approx(0.0)
    assert result.import_today_kwh == pytest.approx(4.5)
    assert result.export_today_kwh == pytest.approx(1.2)
    assert result.import_forecast_today_kwh == pytest.approx(1.5)
    assert result.export_forecast_today_kwh == pytest.approx(1.0)
    assert result.import_forecast_tomorrow_kwh == pytest.approx(2.0)
    assert result.export_forecast_tomorrow_kwh == pytest.approx(0.0)
    assert len(result.hourly_import) == 3
    assert result.hourly_import[0]["import_kwh"] == pytest.approx(1.5)


def test_build_matched_hourly_pv():
    """PV totals distributed across load forecast hours."""
    now = datetime(2026, 6, 27, 10, 0, 0)
    load_hourly = [
        HourlyBucket(start=datetime(2026, 6, 27, 8, 0, 0), price_eur_kwh=0.1, load_kwh=1.0),
        HourlyBucket(start=datetime(2026, 6, 27, 9, 0, 0), price_eur_kwh=0.1, load_kwh=1.0),
        HourlyBucket(start=datetime(2026, 6, 28, 8, 0, 0), price_eur_kwh=0.1, load_kwh=1.0),
    ]
    matched = build_matched_hourly_pv(load_hourly, pv_today_kwh=4.0, pv_tomorrow_kwh=2.0, now=now)
    assert len(matched) == 3
    today_pv = sum(
        bucket.pv_kwh for bucket in matched if bucket.start.date() == now.date()
    )
    tomorrow_pv = sum(
        bucket.pv_kwh
        for bucket in matched
        if bucket.start.date() == (now.date() + timedelta(days=1))
    )
    assert today_pv == pytest.approx(4.0)
    assert tomorrow_pv == pytest.approx(2.0)

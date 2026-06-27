"""Grid import/export from power readings and load/PV forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .pv_forecast import distribute_hourly_pv
from .time_series import HourlyBucket


@dataclass
class GridBalanceResult:
    """Grid import/export totals and hourly breakdown."""

    import_power_w: float = 0.0
    export_power_w: float = 0.0
    import_today_kwh: float = 0.0
    export_today_kwh: float = 0.0
    import_forecast_today_kwh: float = 0.0
    export_forecast_today_kwh: float = 0.0
    import_forecast_tomorrow_kwh: float = 0.0
    export_forecast_tomorrow_kwh: float = 0.0
    hourly_import: list[dict] | None = None
    hourly_export: list[dict] | None = None


def split_grid_power(power_w: float | None) -> tuple[float, float]:
    """Split signed grid power into import and export watts.

    Convention: positive = Netzbezug, negative = Einspeisung.
    """
    if power_w is None:
        return 0.0, 0.0
    if power_w >= 0:
        return power_w, 0.0
    return 0.0, abs(power_w)


def build_matched_hourly_pv(
    load_hourly: list[HourlyBucket],
    pv_today_kwh: float,
    pv_tomorrow_kwh: float,
    now: datetime,
) -> list[HourlyBucket]:
    """Build hourly PV buckets aligned with load forecast hours."""
    tomorrow = (now + timedelta(days=1)).date()
    today_hours = [bucket.start for bucket in load_hourly if bucket.start.date() == now.date()]
    tomorrow_hours = [
        bucket.start for bucket in load_hourly if bucket.start.date() == tomorrow
    ]
    today_pv = distribute_hourly_pv(pv_today_kwh, today_hours)
    tomorrow_pv = distribute_hourly_pv(pv_tomorrow_kwh, tomorrow_hours)
    pv_by_start = {bucket.start: bucket.pv_kwh for bucket in today_pv + tomorrow_pv}
    return [
        HourlyBucket(
            start=bucket.start,
            price_eur_kwh=0.0,
            pv_kwh=pv_by_start.get(bucket.start, 0.0),
        )
        for bucket in load_hourly
    ]


def forecast_grid_balance(
    load_hourly: list[HourlyBucket],
    hourly_pv: list[HourlyBucket],
    now: datetime,
    import_energy_today_kwh: float | None = None,
    export_energy_today_kwh: float | None = None,
    import_power_w: float | None = None,
) -> GridBalanceResult:
    """Compute grid import/export forecasts and optional actuals."""
    actual_import_w, actual_export_w = split_grid_power(import_power_w)

    hourly_import: list[dict] = []
    hourly_export: list[dict] = []
    import_forecast_today = 0.0
    export_forecast_today = 0.0
    import_forecast_tomorrow = 0.0
    export_forecast_tomorrow = 0.0
    tomorrow = (now + timedelta(days=1)).date()

    for index, load_bucket in enumerate(load_hourly):
        pv_kwh = hourly_pv[index].pv_kwh if index < len(hourly_pv) else 0.0
        import_kwh = max(0.0, load_bucket.load_kwh - pv_kwh)
        export_kwh = max(0.0, pv_kwh - load_bucket.load_kwh)
        hourly_import.append(
            {
                "start": load_bucket.start.isoformat(),
                "import_kwh": round(import_kwh, 3),
            }
        )
        hourly_export.append(
            {
                "start": load_bucket.start.isoformat(),
                "export_kwh": round(export_kwh, 3),
            }
        )
        if load_bucket.start.date() == now.date():
            import_forecast_today += import_kwh
            export_forecast_today += export_kwh
        elif load_bucket.start.date() == tomorrow:
            import_forecast_tomorrow += import_kwh
            export_forecast_tomorrow += export_kwh

    return GridBalanceResult(
        import_power_w=actual_import_w,
        export_power_w=actual_export_w,
        import_today_kwh=import_energy_today_kwh or 0.0,
        export_today_kwh=export_energy_today_kwh or 0.0,
        import_forecast_today_kwh=round(import_forecast_today, 2),
        export_forecast_today_kwh=round(export_forecast_today, 2),
        import_forecast_tomorrow_kwh=round(import_forecast_tomorrow, 2),
        export_forecast_tomorrow_kwh=round(export_forecast_tomorrow, 2),
        hourly_import=hourly_import,
        hourly_export=hourly_export,
    )

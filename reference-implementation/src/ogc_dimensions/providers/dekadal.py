"""Dekadal dimension generator — thin alias over DailyPeriodProvider.

Dekadal = 10-day periods, 36/year, month-aligned (D1=1–10, D2=11–20, D3=21–end).

References:
  - FAO ASIS: https://data.apps.fao.org/gismgr/api/v2/catalog
  - cadati (TU Wien, MIT): https://github.com/TUW-GEO/cadati
"""

from __future__ import annotations

from .daily_period import DailyPeriodConfig, DailyPeriodProvider

# Re-export config under the legacy name
DekadalConfig = DailyPeriodConfig


class DekadalProvider(DailyPeriodProvider):
    """Dekadal (10-day period) generator — ``period_days=10, scheme="monthly"``."""

    def __init__(self) -> None:
        super().__init__(period_days=10, scheme="monthly")

"""Pentadal dimension providers — thin aliases over DailyPeriodProvider.

Two pentadal systems exist:
  Monthly (72/year): CHIRPS, CDT, FAO — period_days=5, scheme="monthly"
  Annual  (73/year): GPCP, CPC/NOAA   — period_days=5, scheme="annual"
"""

from __future__ import annotations

from .daily_period import DailyPeriodConfig, DailyPeriodProvider

# Re-export config under the legacy names
PentadalMonthlyConfig = DailyPeriodConfig
PentadalAnnualConfig = DailyPeriodConfig


class PentadalMonthlyProvider(DailyPeriodProvider):
    """Month-based pentadal generator (72 periods/year) — ``period_days=5, scheme="monthly"``."""

    def __init__(self) -> None:
        super().__init__(period_days=5, scheme="monthly")


class PentadalAnnualProvider(DailyPeriodProvider):
    """Year-based pentadal generator (73 periods/year) — ``period_days=5, scheme="annual"``."""

    def __init__(self) -> None:
        super().__init__(period_days=5, scheme="annual")

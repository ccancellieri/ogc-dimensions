"""Unified daily-period dimension provider.

Covers any sub-monthly period defined by a fixed number of days:

  period_days=10, scheme="monthly"  →  Dekadal   (36/year, FAO ASIS / FEWS NET)
  period_days=5,  scheme="monthly"  →  Pentadal  (72/year, CHIRPS / CDT / FAO)
  period_days=5,  scheme="annual"   →  Pentadal  (73/year, GPCP / CPC-NOAA)

Two schemes:
  monthly — divide each month into ceil(month_days / period_days) periods,
            last period absorbs remaining days.
  annual  — consecutive periods from Jan 1, last absorbs remaining days.

Config (author-set, fixed per collection):
    period_days -- length of each period in days (default 10)
    scheme      -- "monthly" or "annual" (default "monthly")

Query parameters (client-set per request):
    sort_dir -- 'asc' (oldest first, default) | 'desc' (newest first)
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .base import (
    DimensionProvider,
    ExtentResult,
    ProducedMember,
    ProviderConfig,
    InverseError,
    PaginatedResult,
    SearchProtocol,
)


@dataclass(frozen=True)
class DailyPeriodConfig(ProviderConfig):
    """Configuration for :class:`DailyPeriodProvider`.

    Attributes:
        period_days: Number of days per period (5 = pentadal, 10 = dekadal).
        scheme: ``"monthly"`` aligns periods to month boundaries;
            ``"annual"`` counts consecutive periods from January 1.
    """

    period_days: int = 10
    scheme: str = "monthly"


# ---------------------------------------------------------------------------
# Notation helpers
# ---------------------------------------------------------------------------

#: Code prefix per scheme — "K" for dekadal (historical), "P" for pentadal,
#: generic "D" for other period sizes within monthly, "A" for annual.
_MONTHLY_PREFIX: dict[int, str] = {10: "K", 5: "P"}
_ANNUAL_PREFIX: str = "A"


def _monthly_prefix(period_days: int) -> str:
    return _MONTHLY_PREFIX.get(period_days, "D")


# ---------------------------------------------------------------------------
# Monthly scheme
# ---------------------------------------------------------------------------


def _periods_per_month(period_days: int) -> int:
    """Number of periods per month (last absorbs remainder).

    Defined as floor(30 / period_days) — the last period absorbs all
    remaining days (21–end for dekadal, 26–end for pentadal).
    """
    # 10-day → 3 (D1/D2/D3), 5-day → 6 (P1..P6)
    return 30 // period_days


def _monthly_members(
    start_year: int,
    end_year: int,
    period_days: int,
) -> list[ProducedMember]:
    """Generate all monthly-aligned periods between start_year and end_year."""
    prefix = _monthly_prefix(period_days)
    ppm = _periods_per_month(period_days)
    members: list[ProducedMember] = []
    idx = 0
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            for p in range(1, ppm + 1):
                start_day = (p - 1) * period_days + 1
                if start_day > last_day:
                    break  # fewer periods in short months
                end_day = min(p * period_days, last_day) if p < ppm else last_day

                period_num = (month - 1) * ppm + p
                code = f"{year}-{prefix}{period_num:02d}"
                start = date(year, month, start_day)
                end = date(year, month, end_day)

                members.append(
                    ProducedMember(
                        value=start.isoformat(),
                        index=idx,
                        code=code,
                        start=start.isoformat(),
                        end=end.isoformat(),
                    )
                )
                idx += 1
    return members


def _monthly_inverse(
    d: date,
    period_days: int,
) -> tuple[str, date, date, int, dict[str, Any]]:
    """Return (code, start, end, index_in_year, coordinate) for a monthly-scheme date."""
    prefix = _monthly_prefix(period_days)
    ppm = _periods_per_month(period_days)
    year, month, day = d.year, d.month, d.day

    p = min((day - 1) // period_days + 1, ppm)
    period_num = (month - 1) * ppm + p

    code = f"{year}-{prefix}{period_num:02d}"
    start_day = (p - 1) * period_days + 1
    last_day = calendar.monthrange(year, month)[1]
    end_day = min(p * period_days, last_day) if p < ppm else last_day

    start = date(year, month, start_day)
    end = date(year, month, end_day)
    coordinate: dict[str, Any] = {"year": year, "month": month, "period": p}

    return code, start, end, period_num - 1, coordinate


# ---------------------------------------------------------------------------
# Annual scheme
# ---------------------------------------------------------------------------


def _annual_periods_count(period_days: int) -> int:
    """Number of periods per year (last absorbs remainder).

    Uses 365 as the base — the last period absorbs the extra day(s)
    on leap years.  E.g. 5-day → 73 (P73 = 5 or 6 days).
    """
    return math.ceil(365 / period_days)


def _annual_members(
    start_year: int,
    end_year: int,
    period_days: int,
) -> list[ProducedMember]:
    """Generate all annual-aligned periods between start_year and end_year."""
    n_max = _annual_periods_count(period_days)
    members: list[ProducedMember] = []
    idx = 0
    for year in range(start_year, end_year + 1):
        jan1 = date(year, 1, 1)
        dec31 = date(year, 12, 31)
        for p in range(1, n_max + 1):
            start = jan1 + timedelta(days=(p - 1) * period_days)
            if start > dec31:
                break
            if p < n_max:
                end = jan1 + timedelta(days=p * period_days - 1)
                if end > dec31:
                    end = dec31
            else:
                end = dec31

            code = f"{year}-{_ANNUAL_PREFIX}{p:02d}"
            members.append(
                ProducedMember(
                    value=start.isoformat(),
                    index=idx,
                    code=code,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
            )
            idx += 1
    return members


def _annual_inverse(
    d: date,
    period_days: int,
) -> tuple[str, date, date, int, dict[str, Any]]:
    """Return (code, start, end, index, coordinate) for an annual-scheme date."""
    n_max = _annual_periods_count(period_days)
    year = d.year
    jan1 = date(year, 1, 1)
    dec31 = date(year, 12, 31)
    day_of_year = (d - jan1).days  # 0-based

    p = min(day_of_year // period_days + 1, n_max)
    code = f"{year}-{_ANNUAL_PREFIX}{p:02d}"
    start = jan1 + timedelta(days=(p - 1) * period_days)
    if p < n_max:
        end = jan1 + timedelta(days=p * period_days - 1)
        if end > dec31:
            end = dec31
    else:
        end = dec31

    coordinate: dict[str, Any] = {"year": year, "period": p}
    return code, start, end, p - 1, coordinate


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class DailyPeriodProvider(DimensionProvider):
    """Unified daily-period provider.

    Handles any fixed-length sub-monthly period aligned to either
    month boundaries (``scheme="monthly"``) or year start
    (``scheme="annual"``).

    Conformance: Basic + Invertible + Searchable (exact, range)
    """

    def __init__(self, period_days: int = 10, scheme: str = "monthly") -> None:
        self.period_days = period_days
        self.scheme = scheme

    # ------------------------------------------------------------------
    # DimensionProvider protocol
    # ------------------------------------------------------------------

    @property
    def provider_type(self) -> str:
        return "daily-period"

    @property
    def config(self) -> DailyPeriodConfig:
        return DailyPeriodConfig(period_days=self.period_days, scheme=self.scheme)

    @property
    def invertible(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _all_members(self, start_year: int, end_year: int) -> list[ProducedMember]:
        if self.scheme == "annual":
            return _annual_members(start_year, end_year, self.period_days)
        return _monthly_members(start_year, end_year, self.period_days)

    def _year_range(self, extent_min: Any, extent_max: Any) -> tuple[int, int]:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        return start_year, end_year

    def _periods_per_year(self) -> int:
        if self.scheme == "annual":
            return _annual_periods_count(self.period_days)
        return 12 * _periods_per_month(self.period_days)

    # ------------------------------------------------------------------
    # Basic conformance
    # ------------------------------------------------------------------

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        start_year, end_year = self._year_range(extent_min, extent_max)
        sort_dir: str = params.get("sort_dir", "asc")

        all_members = self._all_members(start_year, end_year)
        if sort_dir == "desc":
            all_members.reverse()
        total = len(all_members)
        page = all_members[offset : offset + limit]

        return PaginatedResult(
            dimension="time",
            number_matched=total,
            number_returned=len(page),
            members=page,
            offset=offset,
            limit=limit,
        )

    def extent(self, extent_min: Any, extent_max: Any, **_params: Any) -> ExtentResult:
        start_year, end_year = self._year_range(extent_min, extent_max)
        ppy = self._periods_per_year()
        total = (end_year - start_year + 1) * ppy

        if self.scheme == "annual":
            prefix = _ANNUAL_PREFIX
        else:
            prefix = _monthly_prefix(self.period_days)

        return ExtentResult(
            native_min=f"{start_year}-{prefix}01",
            native_max=f"{end_year}-{prefix}{ppy:02d}",
            standard_min=date(start_year, 1, 1).isoformat(),
            standard_max=date(end_year, 12, 31).isoformat(),
            size=total,
        )

    # ------------------------------------------------------------------
    # Invertible conformance
    # ------------------------------------------------------------------

    def inverse(self, value: str) -> ProducedMember:
        try:
            d = date.fromisoformat(value[:10])
        except (ValueError, TypeError) as exc:
            raise InverseError(
                code="InvalidFormat",
                description=f"Cannot parse '{value}' as an ISO-8601 date.",
            ) from exc

        if self.scheme == "annual":
            code, start, end, index, _coord = _annual_inverse(d, self.period_days)
        else:
            code, start, end, index, _coord = _monthly_inverse(d, self.period_days)

        return ProducedMember(
            value=start.isoformat(),
            index=index,
            code=code,
            start=start.isoformat(),
            end=end.isoformat(),
        )

    # ------------------------------------------------------------------
    # Searchable conformance
    # ------------------------------------------------------------------

    def search(
        self,
        protocol: SearchProtocol,
        extent_min: Any,
        extent_max: Any,
        **query: Any,
    ) -> PaginatedResult:
        start_year, end_year = self._year_range(extent_min, extent_max)
        all_members = self._all_members(start_year, end_year)

        if protocol == SearchProtocol.EXACT:
            code = query.get("exact", "")
            matches = [m for m in all_members if m.code == code]
        elif protocol == SearchProtocol.RANGE:
            min_code = query.get("min", "")
            max_code = query.get("max", "")
            matches = [
                m
                for m in all_members
                if m.code is not None and min_code <= m.code <= max_code
            ]
        else:
            raise NotImplementedError(f"Search protocol '{protocol}' not supported.")

        return PaginatedResult(
            dimension="time",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

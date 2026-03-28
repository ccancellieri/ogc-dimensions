"""Pentadal dimension generators.

Two systems:
  - Month-based (72/year): CHIRPS, CDT, FAO -- P6 absorbs remaining days 26-end
  - Year-based (73/year): GPCP, CPC/NOAA -- consecutive 5-day periods, P73 has 5 or 6 days
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

from .base import (
    DimensionGenerator,
    ExtentResult,
    GeneratedMember,
    InverseResult,
    PaginatedResult,
    SearchProtocol,
)


# --- Month-Based Pentadal (72/year) ---


def _monthly_pentads(start_year: int, end_year: int):
    """Yield all month-based pentads between start_year and end_year."""
    idx = 0
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            for p in range(1, 7):
                start_day = (p - 1) * 5 + 1
                if p < 6:
                    end_day = p * 5
                else:
                    end_day = last_day  # P6 absorbs 26-end

                pentad_num = (month - 1) * 6 + p
                code = f"{year}-P{pentad_num:02d}"
                start = date(year, month, start_day)
                end = date(year, month, end_day)

                yield GeneratedMember(
                    value=start.isoformat(),
                    index=idx,
                    code=code,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
                idx += 1


class PentadalMonthlyGenerator(DimensionGenerator):
    """Month-based pentadal generator (72 periods/year).

    Each month has 6 pentads of 5 days each.
    P6 absorbs remaining days (26 to end of month: 3-6 days).
    Used by CHIRPS, CDT, FAO.
    """

    @property
    def generator_type(self) -> str:
        return "pentadal-monthly"

    @property
    def bijective(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE]

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        all_members = list(_monthly_pentads(start_year, end_year))
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

    def extent(self, extent_min: Any, extent_max: Any, **params: Any) -> ExtentResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        total = (end_year - start_year + 1) * 72

        return ExtentResult(
            native_min=f"{start_year}-P01",
            native_max=f"{end_year}-P72",
            standard_min=date(start_year, 1, 1).isoformat(),
            standard_max=date(end_year, 12, 31).isoformat(),
            size=total,
        )

    def inverse(self, value: str) -> InverseResult:
        try:
            d = date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return InverseResult(valid=False, reason=f"Cannot parse '{value}' as a date.")

        year, month, day = d.year, d.month, d.day

        if day <= 5:
            p = 1
        elif day <= 10:
            p = 2
        elif day <= 15:
            p = 3
        elif day <= 20:
            p = 4
        elif day <= 25:
            p = 5
        else:
            p = 6

        pentad_num = (month - 1) * 6 + p
        code = f"{year}-P{pentad_num:02d}"
        start_day = (p - 1) * 5 + 1
        last_day = calendar.monthrange(year, month)[1]
        end_day = p * 5 if p < 6 else last_day

        return InverseResult(
            valid=True,
            member=code,
            coordinate={"year": year, "month": month, "pentad": p},
            range={
                "start": date(year, month, start_day).isoformat(),
                "end": date(year, month, end_day).isoformat(),
            },
            index=pentad_num - 1,
        )

    def search(
        self,
        protocol: SearchProtocol,
        extent_min: Any,
        extent_max: Any,
        **query: Any,
    ) -> PaginatedResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        all_members = list(_monthly_pentads(start_year, end_year))

        if protocol == SearchProtocol.EXACT:
            code = query.get("exact", "")
            matches = [m for m in all_members if m.code == code]
        elif protocol == SearchProtocol.RANGE:
            min_code = query.get("min", "")
            max_code = query.get("max", "")
            matches = [
                m for m in all_members
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


# --- Year-Based Pentadal (73/year) ---


def _annual_pentads(start_year: int, end_year: int):
    """Yield all year-based pentads. Consecutive 5-day periods from Jan 1."""
    idx = 0
    for year in range(start_year, end_year + 1):
        jan1 = date(year, 1, 1)
        dec31 = date(year, 12, 31)
        days_in_year = (dec31 - jan1).days + 1
        n_pentads = 73  # Always 73: last pentad is 5 or 6 days

        for p in range(1, n_pentads + 1):
            start = jan1 + timedelta(days=(p - 1) * 5)
            if p < n_pentads:
                end = jan1 + timedelta(days=p * 5 - 1)
            else:
                end = dec31  # P73 absorbs remaining days

            if start > dec31:
                break

            code = f"{year}-A{p:02d}"
            yield GeneratedMember(
                value=start.isoformat(),
                index=idx,
                code=code,
                start=start.isoformat(),
                end=end.isoformat(),
            )
            idx += 1


class PentadalAnnualGenerator(DimensionGenerator):
    """Year-based pentadal generator (73 periods/year).

    Consecutive 5-day periods starting January 1.
    Period 73 has 5 days (non-leap) or 6 days (leap year).
    Used by GPCP, CPC/NOAA.
    """

    @property
    def generator_type(self) -> str:
        return "pentadal-annual"

    @property
    def bijective(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE]

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        all_members = list(_annual_pentads(start_year, end_year))
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

    def extent(self, extent_min: Any, extent_max: Any, **params: Any) -> ExtentResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        total = (end_year - start_year + 1) * 73

        return ExtentResult(
            native_min=f"{start_year}-A01",
            native_max=f"{end_year}-A73",
            standard_min=date(start_year, 1, 1).isoformat(),
            standard_max=date(end_year, 12, 31).isoformat(),
            size=total,
        )

    def inverse(self, value: str) -> InverseResult:
        try:
            d = date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return InverseResult(valid=False, reason=f"Cannot parse '{value}' as a date.")

        year = d.year
        jan1 = date(year, 1, 1)
        day_of_year = (d - jan1).days  # 0-based

        p = day_of_year // 5 + 1
        if p > 73:
            p = 73

        code = f"{year}-A{p:02d}"
        start = jan1 + timedelta(days=(p - 1) * 5)
        dec31 = date(year, 12, 31)
        if p < 73:
            end = jan1 + timedelta(days=p * 5 - 1)
        else:
            end = dec31

        return InverseResult(
            valid=True,
            member=code,
            coordinate={"year": year, "pentad": p},
            range={"start": start.isoformat(), "end": end.isoformat()},
            index=p - 1,
        )

    def search(
        self,
        protocol: SearchProtocol,
        extent_min: Any,
        extent_max: Any,
        **query: Any,
    ) -> PaginatedResult:
        start_year = date.fromisoformat(str(extent_min)[:10]).year
        end_year = date.fromisoformat(str(extent_max)[:10]).year
        all_members = list(_annual_pentads(start_year, end_year))

        if protocol == SearchProtocol.EXACT:
            matches = [m for m in all_members if m.code == query.get("exact", "")]
        elif protocol == SearchProtocol.RANGE:
            min_code, max_code = query.get("min", ""), query.get("max", "")
            matches = [
                m for m in all_members
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

"""Dekadal dimension generator.

Each month is split into 3 dekads:
  D1: days 1-10
  D2: days 11-20
  D3: days 21-end (varies: 8 days Feb non-leap, up to 11 days for 31-day months)

36 dekads per year. Index formula: (month - 1) * 3 + d

References:
  - FAO ASIS: https://data.apps.fao.org/gismgr/api/v2/catalog
  - cadati (TU Wien, MIT): https://github.com/TUW-GEO/cadati
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
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


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _dekad_start(year: int, month: int, d: int) -> date:
    """Start date of dekad d (1-3) in given year/month."""
    return date(year, month, [1, 11, 21][d - 1])


def _dekad_end(year: int, month: int, d: int) -> date:
    """End date of dekad d (1-3) in given year/month."""
    if d == 1:
        return date(year, month, 10)
    elif d == 2:
        return date(year, month, 20)
    else:
        return date(year, month, _last_day(year, month))


def _dekad_code(year: int, month: int, d: int) -> str:
    """YYYY-Knn notation."""
    index = (month - 1) * 3 + d
    return f"{year}-K{index:02d}"


def _all_dekads(start_year: int, end_year: int):
    """Yield all dekads between start_year and end_year (inclusive)."""
    idx = 0
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            for d in range(1, 4):
                start = _dekad_start(year, month, d)
                end = _dekad_end(year, month, d)
                code = _dekad_code(year, month, d)
                days = (end - start).days + 1
                yield GeneratedMember(
                    value=start.isoformat(),
                    index=idx,
                    code=code,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
                idx += 1


class DekadalGenerator(DimensionGenerator):
    """Dekadal (10-day period) generator.

    Conformance: Basic + Invertible + Searchable
    """

    @property
    def generator_type(self) -> str:
        return "dekadal"

    @property
    def invertible(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE, SearchProtocol.LIKE]

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

        all_members = list(_all_dekads(start_year, end_year))
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
        start_date = date.fromisoformat(str(extent_min)[:10])
        end_date = date.fromisoformat(str(extent_max)[:10])
        start_year = start_date.year
        end_year = end_date.year
        total = (end_year - start_year + 1) * 36

        return ExtentResult(
            native_min=_dekad_code(start_year, 1, 1),
            native_max=_dekad_code(end_year, 12, 3),
            standard_min=date(start_year, 1, 1).isoformat(),
            standard_max=date(end_year, 12, 31).isoformat(),
            size=total,
        )

    def inverse(self, value: str) -> InverseResult:
        try:
            d = date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return InverseResult(
                valid=False,
                reason=f"Cannot parse '{value}' as a date.",
            )

        year, month, day = d.year, d.month, d.day

        if day <= 10:
            dekad = 1
        elif day <= 20:
            dekad = 2
        else:
            dekad = 3

        code = _dekad_code(year, month, dekad)
        start = _dekad_start(year, month, dekad)
        end = _dekad_end(year, month, dekad)
        index = (year - 2000) * 36 + (month - 1) * 3 + dekad - 1  # 0-based from year 2000

        return InverseResult(
            valid=True,
            member=code,
            coordinate={"year": year, "month": month, "dekad": dekad},
            range={"start": start.isoformat(), "end": end.isoformat()},
            index=index,
        )

    def search(
        self,
        protocol: SearchProtocol,
        extent_min: Any,
        extent_max: Any,
        **query: Any,
    ) -> PaginatedResult:
        if protocol == SearchProtocol.EXACT:
            return self._search_exact(query.get("exact", ""), extent_min, extent_max)
        elif protocol == SearchProtocol.RANGE:
            return self._search_range(
                query.get("min", ""), query.get("max", ""), extent_min, extent_max
            )
        elif protocol == SearchProtocol.LIKE:
            return self._search_like(
                query.get("like", ""), extent_min, extent_max, query.get("limit", 100)
            )
        raise NotImplementedError(f"Search protocol '{protocol}' not supported.")

    def _search_exact(
        self, code: str, extent_min: Any, extent_max: Any
    ) -> PaginatedResult:
        all_members = list(
            _all_dekads(
                date.fromisoformat(str(extent_min)[:10]).year,
                date.fromisoformat(str(extent_max)[:10]).year,
            )
        )
        matches = [m for m in all_members if m.code == code]
        return PaginatedResult(
            dimension="time",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

    def _search_range(
        self, min_code: str, max_code: str, extent_min: Any, extent_max: Any
    ) -> PaginatedResult:
        all_members = list(
            _all_dekads(
                date.fromisoformat(str(extent_min)[:10]).year,
                date.fromisoformat(str(extent_max)[:10]).year,
            )
        )
        matches = [
            m
            for m in all_members
            if m.code is not None and min_code <= m.code <= max_code
        ]
        return PaginatedResult(
            dimension="time",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

    def _search_like(
        self, pattern: str, extent_min: Any, extent_max: Any, limit: int = 100
    ) -> PaginatedResult:
        import fnmatch

        all_members = list(
            _all_dekads(
                date.fromisoformat(str(extent_min)[:10]).year,
                date.fromisoformat(str(extent_max)[:10]).year,
            )
        )
        matches = [
            m
            for m in all_members
            if m.code is not None and fnmatch.fnmatch(m.code, pattern)
        ][:limit]
        return PaginatedResult(
            dimension="time",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

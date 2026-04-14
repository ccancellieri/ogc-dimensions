"""Integer range dimension generator.

Generates evenly-spaced integer members within a range.
Use cases: elevation bands, percentile bins, age groups, grid indices.

Config (author-set, fixed per collection):
    step  -- bin width in the same unit as the extent (default 1)

Query parameters (client-set per request):
    sort_by  -- 'code' or 'index' (default: 'code' asc = lowest band first)
    sort_dir -- 'asc' | 'desc'
"""

from __future__ import annotations

from dataclasses import dataclass
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
class IntegerRangeConfig(ProviderConfig):
    """Configuration for :class:`IntegerRangeProvider`."""

    step: int = 1


class IntegerRangeProvider(DimensionProvider):
    """Integer range generator.

    Conformance: Basic + Invertible + Searchable
    """

    def __init__(self, step: int = 1) -> None:
        self.step = step

    # ------------------------------------------------------------------
    # DimensionProvider protocol
    # ------------------------------------------------------------------

    @property
    def provider_type(self) -> str:
        return "integer-range"

    @property
    def config(self) -> IntegerRangeConfig:
        return IntegerRangeConfig(step=self.step)

    @property
    def invertible(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _members(self, min_val: int, max_val: int) -> list[ProducedMember]:
        members: list[ProducedMember] = []
        idx = 0
        val = min_val
        while val <= max_val:
            upper = min(val + self.step - 1, max_val)
            members.append(
                ProducedMember(
                    value=val,
                    index=idx,
                    code=str(val),
                    extra={
                        "code": str(val),
                        "index": idx,
                        "lower": val,
                        "upper": upper,
                    },
                )
            )
            idx += 1
            val += self.step
        return members

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
        # step is config-only — not overridable by query params
        sort_dir: str = params.get("sort_dir", "asc")

        all_members = self._members(int(extent_min), int(extent_max))
        if sort_dir == "desc":
            all_members = list(reversed(all_members))

        total = len(all_members)
        page = all_members[offset: offset + limit]

        return PaginatedResult(
            dimension="value",
            number_matched=total,
            number_returned=len(page),
            members=page,
            offset=offset,
            limit=limit,
        )

    def extent(self, extent_min: Any, extent_max: Any, **params: Any) -> ExtentResult:
        min_val = int(extent_min)
        max_val = int(extent_max)
        size = (max_val - min_val) // self.step + 1

        return ExtentResult(
            native_min=min_val,
            native_max=max_val,
            standard_min=str(min_val),
            standard_max=str(max_val),
            size=size,
        )

    # ------------------------------------------------------------------
    # Invertible conformance
    # ------------------------------------------------------------------

    def inverse(self, value: str) -> ProducedMember:
        try:
            val = int(value)
        except (ValueError, TypeError) as exc:
            raise InverseError(
                code="InvalidFormat",
                description=f"Cannot parse '{value}' as an integer.",
            ) from exc

        bin_start = (val // self.step) * self.step
        index = bin_start // self.step
        upper = bin_start + self.step - 1

        return ProducedMember(
            value=bin_start,
            index=index,
            code=str(bin_start),
            extra={"lower": bin_start, "upper": upper},
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
        all_members = self._members(int(extent_min), int(extent_max))

        if protocol == SearchProtocol.EXACT:
            exact_val = str(query.get("exact", ""))
            matches = [m for m in all_members if m.code == exact_val]
        elif protocol == SearchProtocol.RANGE:
            min_v = int(query.get("min", extent_min))
            max_v = int(query.get("max", extent_max))
            matches = [m for m in all_members if min_v <= int(m.value) <= max_v]
        else:
            raise NotImplementedError(f"Search protocol '{protocol}' not supported.")

        return PaginatedResult(
            dimension="value",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

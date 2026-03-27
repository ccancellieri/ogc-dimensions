"""Integer range dimension generator.

Generates evenly-spaced integer members within a range.
Use cases: elevation bands, percentile bins, age groups, grid indices.
"""

from __future__ import annotations

from typing import Any

from .base import (
    DimensionGenerator,
    ExtentResult,
    GeneratedMember,
    InverseResult,
    PaginatedResult,
    SearchProtocol,
)


class IntegerRangeGenerator(DimensionGenerator):
    """Integer range generator.

    Conformance: Basic + Invertible + Searchable
    """

    def __init__(self, step: int = 1):
        self.step = step

    @property
    def generator_type(self) -> str:
        return "integer-range"

    @property
    def bijective(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.RANGE]

    def _members(self, min_val: int, max_val: int) -> list[GeneratedMember]:
        members = []
        idx = 0
        val = min_val
        while val <= max_val:
            members.append(
                GeneratedMember(
                    value=val,
                    index=idx,
                    code=str(val),
                )
            )
            idx += 1
            val += self.step
        return members

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        step = params.get("step", self.step)
        all_members = self._members(int(extent_min), int(extent_max))
        total = len(all_members)
        page = all_members[offset : offset + limit]

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

    def inverse(self, value: str) -> InverseResult:
        try:
            val = int(value)
        except (ValueError, TypeError):
            return InverseResult(valid=False, reason=f"Cannot parse '{value}' as integer.")

        # Find which bin this value belongs to
        bin_start = (val // self.step) * self.step
        index = bin_start // self.step

        return InverseResult(
            valid=True,
            member=str(bin_start),
            coordinate={"value": bin_start},
            range={"start": str(bin_start), "end": str(bin_start + self.step - 1)},
            index=index,
        )

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
            matches = [m for m in all_members if min_v <= m.value <= max_v]
        else:
            raise NotImplementedError(f"Search protocol '{protocol}' not supported.")

        return PaginatedResult(
            dimension="value",
            number_matched=len(matches),
            number_returned=len(matches),
            members=matches,
        )

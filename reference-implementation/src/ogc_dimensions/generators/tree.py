"""Static tree generator for hierarchical dimensions.

Implements the Hierarchical conformance level using an in-memory tree:
  /generate              -- root members (parent_code is null)
  /generate?parent=X     -- direct children of X (alias for /children)
  /children?parent=X     -- direct children of X
  /ancestors?member=X    -- ancestor chain from root to X (inclusive)

The bundled ``WORLD_ADMIN_NODES`` dataset provides a two-level
continent → country tree suitable for the ``world-admin`` demo dimension.
"""

from __future__ import annotations

import fnmatch
from typing import Any

from .base import (
    DimensionGenerator,
    ExtentResult,
    GeneratedMember,
    PaginatedResult,
    SearchProtocol,
)

# ---------------------------------------------------------------------------
# Demo dataset: continent → country (2 levels)
# ---------------------------------------------------------------------------

WORLD_ADMIN_NODES: list[dict[str, Any]] = [
    # Level 0 — Continents (root, parent_code=null)
    {"code": "Africa",   "label": "Africa",   "parent_code": None, "level": 0},
    {"code": "Americas", "label": "Americas", "parent_code": None, "level": 0},
    {"code": "Asia",     "label": "Asia",     "parent_code": None, "level": 0},
    {"code": "Europe",   "label": "Europe",   "parent_code": None, "level": 0},
    {"code": "Oceania",  "label": "Oceania",  "parent_code": None, "level": 0},

    # Level 1 — Countries: Africa
    {"code": "DZA", "label": "Algeria",       "parent_code": "Africa",   "level": 1},
    {"code": "AGO", "label": "Angola",        "parent_code": "Africa",   "level": 1},
    {"code": "EGY", "label": "Egypt",         "parent_code": "Africa",   "level": 1},
    {"code": "ETH", "label": "Ethiopia",      "parent_code": "Africa",   "level": 1},
    {"code": "KEN", "label": "Kenya",         "parent_code": "Africa",   "level": 1},
    {"code": "MDG", "label": "Madagascar",    "parent_code": "Africa",   "level": 1},
    {"code": "MLI", "label": "Mali",          "parent_code": "Africa",   "level": 1},
    {"code": "MOZ", "label": "Mozambique",    "parent_code": "Africa",   "level": 1},
    {"code": "NGA", "label": "Nigeria",       "parent_code": "Africa",   "level": 1},
    {"code": "SDN", "label": "Sudan",         "parent_code": "Africa",   "level": 1},
    {"code": "TZA", "label": "Tanzania",      "parent_code": "Africa",   "level": 1},
    {"code": "ZAF", "label": "South Africa",  "parent_code": "Africa",   "level": 1},
    {"code": "ZMB", "label": "Zambia",        "parent_code": "Africa",   "level": 1},

    # Level 1 — Countries: Americas
    {"code": "ARG", "label": "Argentina",     "parent_code": "Americas", "level": 1},
    {"code": "BOL", "label": "Bolivia",       "parent_code": "Americas", "level": 1},
    {"code": "BRA", "label": "Brazil",        "parent_code": "Americas", "level": 1},
    {"code": "CAN", "label": "Canada",        "parent_code": "Americas", "level": 1},
    {"code": "COL", "label": "Colombia",      "parent_code": "Americas", "level": 1},
    {"code": "GTM", "label": "Guatemala",     "parent_code": "Americas", "level": 1},
    {"code": "MEX", "label": "Mexico",        "parent_code": "Americas", "level": 1},
    {"code": "PER", "label": "Peru",          "parent_code": "Americas", "level": 1},
    {"code": "USA", "label": "United States", "parent_code": "Americas", "level": 1},
    {"code": "VEN", "label": "Venezuela",     "parent_code": "Americas", "level": 1},

    # Level 1 — Countries: Asia
    {"code": "AFG", "label": "Afghanistan",   "parent_code": "Asia",     "level": 1},
    {"code": "BGD", "label": "Bangladesh",    "parent_code": "Asia",     "level": 1},
    {"code": "CHN", "label": "China",         "parent_code": "Asia",     "level": 1},
    {"code": "IND", "label": "India",         "parent_code": "Asia",     "level": 1},
    {"code": "IDN", "label": "Indonesia",     "parent_code": "Asia",     "level": 1},
    {"code": "IRN", "label": "Iran",          "parent_code": "Asia",     "level": 1},
    {"code": "IRQ", "label": "Iraq",          "parent_code": "Asia",     "level": 1},
    {"code": "JPN", "label": "Japan",         "parent_code": "Asia",     "level": 1},
    {"code": "PAK", "label": "Pakistan",      "parent_code": "Asia",     "level": 1},
    {"code": "PHL", "label": "Philippines",   "parent_code": "Asia",     "level": 1},
    {"code": "TUR", "label": "Turkey",        "parent_code": "Asia",     "level": 1},
    {"code": "YEM", "label": "Yemen",         "parent_code": "Asia",     "level": 1},

    # Level 1 — Countries: Europe
    {"code": "DEU", "label": "Germany",       "parent_code": "Europe",   "level": 1},
    {"code": "ESP", "label": "Spain",         "parent_code": "Europe",   "level": 1},
    {"code": "FRA", "label": "France",        "parent_code": "Europe",   "level": 1},
    {"code": "GBR", "label": "United Kingdom","parent_code": "Europe",   "level": 1},
    {"code": "ITA", "label": "Italy",         "parent_code": "Europe",   "level": 1},
    {"code": "NLD", "label": "Netherlands",   "parent_code": "Europe",   "level": 1},
    {"code": "POL", "label": "Poland",        "parent_code": "Europe",   "level": 1},
    {"code": "ROU", "label": "Romania",       "parent_code": "Europe",   "level": 1},
    {"code": "UKR", "label": "Ukraine",       "parent_code": "Europe",   "level": 1},

    # Level 1 — Countries: Oceania
    {"code": "AUS", "label": "Australia",         "parent_code": "Oceania",  "level": 1},
    {"code": "FJI", "label": "Fiji",              "parent_code": "Oceania",  "level": 1},
    {"code": "NZL", "label": "New Zealand",       "parent_code": "Oceania",  "level": 1},
    {"code": "PNG", "label": "Papua New Guinea",  "parent_code": "Oceania",  "level": 1},
    {"code": "SLB", "label": "Solomon Islands",   "parent_code": "Oceania",  "level": 1},
]


def _to_member(node: dict[str, Any], index: int) -> GeneratedMember:
    return GeneratedMember(
        value=node,
        index=index,
        code=node["code"],
        extra=node,
    )


class StaticTreeGenerator(DimensionGenerator):
    """In-memory static tree generator for hierarchical nominal dimensions.

    Supports Hierarchical conformance level: ``/children``, ``/ancestors``,
    and ``?parent=`` filter on ``/generate``. Designed for the ``world-admin``
    demo dimension but accepts any list of nodes with ``code``, ``label``,
    and ``parent_code`` fields.
    """

    def __init__(self, nodes: list[dict[str, Any]] | None = None) -> None:
        self._nodes = nodes if nodes is not None else WORLD_ADMIN_NODES
        self._by_code: dict[str, dict[str, Any]] = {n["code"]: n for n in self._nodes}

    # ------------------------------------------------------------------
    # DimensionGenerator protocol
    # ------------------------------------------------------------------

    @property
    def generator_type(self) -> str:
        return "static-tree"

    @property
    def bijective(self) -> bool:
        return False

    @property
    def hierarchical(self) -> bool:
        return True

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        return [SearchProtocol.EXACT, SearchProtocol.LIKE]

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        """Return root members, or children of ``parent`` if given."""
        parent: str | None = params.get("parent")
        if parent is not None:
            candidates = [n for n in self._nodes if n["parent_code"] == parent]
        else:
            candidates = [n for n in self._nodes if n["parent_code"] is None]

        total = len(candidates)
        page = candidates[offset: offset + limit]
        members = [_to_member(node, offset + i) for i, node in enumerate(page)]

        return PaginatedResult(
            dimension="",
            number_matched=total,
            number_returned=len(members),
            members=members,
            offset=offset,
            limit=limit,
        )

    def extent(self, extent_min: Any, extent_max: Any, **params: Any) -> ExtentResult:
        """Return total node count as size; no numeric extent applies."""
        return ExtentResult(
            native_min=None,
            native_max=None,
            standard_min="",
            standard_max="",
            size=len(self._nodes),
        )

    # ------------------------------------------------------------------
    # Hierarchical conformance
    # ------------------------------------------------------------------

    def children(
        self,
        parent_code: str,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Return paginated direct children of *parent_code*."""
        candidates = [n for n in self._nodes if n["parent_code"] == parent_code]
        total = len(candidates)
        page = candidates[offset: offset + limit]
        members = [_to_member(node, offset + i) for i, node in enumerate(page)]

        return PaginatedResult(
            dimension="",
            number_matched=total,
            number_returned=len(members),
            members=members,
            offset=offset,
            limit=limit,
        )

    def ancestors(self, member_code: str) -> list[dict[str, Any]]:
        """Return ancestor chain from root to *member_code* (inclusive).

        The chain is ordered from coarsest ancestor to the member itself.
        Returns an empty list if *member_code* is not found.
        """
        chain: list[dict[str, Any]] = []
        code: str | None = member_code
        seen: set[str] = set()

        while code is not None:
            if code in seen:
                break
            seen.add(code)
            node = self._by_code.get(code)
            if node is None:
                break
            chain.insert(0, node)
            code = node.get("parent_code")

        return chain

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
        if protocol == SearchProtocol.EXACT:
            code = query.get("exact", "")
            node = self._by_code.get(code)
            members = [_to_member(node, 0)] if node else []
            return PaginatedResult(
                dimension="",
                number_matched=len(members),
                number_returned=len(members),
                members=members,
            )

        if protocol == SearchProtocol.LIKE:
            pattern = query.get("like", "*")
            limit = int(query.get("limit", 100))
            matched = [
                n for n in self._nodes
                if fnmatch.fnmatch(n["code"], pattern)
                or fnmatch.fnmatch(n["label"], pattern)
            ]
            page = matched[:limit]
            members = [_to_member(n, i) for i, n in enumerate(page)]
            return PaginatedResult(
                dimension="",
                number_matched=len(matched),
                number_returned=len(members),
                members=members,
            )

        raise NotImplementedError(
            f"StaticTreeGenerator does not support search protocol '{protocol}'."
        )


class LeveledTreeGenerator(StaticTreeGenerator):
    """Tree generator supporting level-based filtering (leveled strategy).

    Extends ``StaticTreeGenerator`` with a ``level`` parameter on ``/generate``.
    Nodes must carry a ``level`` integer field.  Clients can filter by level
    (condition-based), by parent (tree navigation), or both::

        ?level=0             → all continents
        ?level=1             → all countries
        ?level=1&parent=AFR  → African countries only
        ?parent=ITA          → Italian regions (children of ITA)
    """

    @property
    def generator_type(self) -> str:
        return "leveled-tree"

    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        level = params.get("level")
        if level is not None:
            level_int = int(level)
            parent: str | None = params.get("parent")
            candidates = [n for n in self._nodes if n.get("level") == level_int]
            if parent is not None:
                candidates = [n for n in candidates if n["parent_code"] == parent]
            total = len(candidates)
            page = candidates[offset: offset + limit]
            members = [_to_member(node, offset + i) for i, node in enumerate(page)]
            return PaginatedResult(
                dimension="",
                number_matched=total,
                number_returned=len(members),
                members=members,
                offset=offset,
                limit=limit,
            )
        return super().generate(extent_min, extent_max, limit, offset, **params)

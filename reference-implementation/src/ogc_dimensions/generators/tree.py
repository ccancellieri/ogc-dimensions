"""Static tree generators for hierarchical dimensions.

Two generator types are provided, each encapsulating its own hierarchy strategy:

  StaticTreeGenerator  (type: "static-tree")
    Recursive strategy: each member carries a ``parent_code`` field.
    /members          → root members (parent_code is None)
    /members?parent=X → delegates to /children (alias)
    /children?parent=X → direct children of X
    /ancestors?member=X → ancestor chain from root to X

  LeveledTreeGenerator  (type: "leveled-tree")
    Leveled strategy: hierarchy is imposed by named level definitions.
    Extends StaticTreeGenerator with a ``?level=N`` parameter that filters
    members to a specific level, mirroring the ``parameters`` object declared
    in each hierarchy level's metadata.
    /members?level=N         → all members at level N
    /members?level=N&parent=X → members at level N that are children of X

Adding a new hierarchy strategy means adding a new generator subclass —
no changes to the spec schema are required.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .base import (
    DimensionGenerator,
    ExtentResult,
    GeneratedMember,
    GeneratorConfig,
    PaginatedResult,
    SearchProtocol,
)


@dataclass(frozen=True)
class StaticTreeConfig(GeneratorConfig):
    """Configuration for :class:`StaticTreeGenerator` — no fields (fully data-driven)."""

# ---------------------------------------------------------------------------
# Demo dataset: continent → country (2 levels)
# ---------------------------------------------------------------------------

WORLD_ADMIN_NODES: list[dict[str, Any]] = [
    # Level 0 — Continents (root, parent_code=null) — ISO 3-letter + UN languages
    {"code": "AFR", "label": "Africa",   "labels": {"en": "Africa",   "fr": "Afrique",   "ar": "أفريقيا",    "es": "África",   "zh": "非洲"},  "parent_code": None, "level": 0},
    {"code": "AMR", "label": "Americas", "labels": {"en": "Americas", "fr": "Amériques", "ar": "الأمريكتان", "es": "Américas", "zh": "美洲"},  "parent_code": None, "level": 0},
    {"code": "ASI", "label": "Asia",     "labels": {"en": "Asia",     "fr": "Asie",      "ar": "آسيا",       "es": "Asia",     "zh": "亚洲"},  "parent_code": None, "level": 0},
    {"code": "EUR", "label": "Europe",   "labels": {"en": "Europe",   "fr": "Europe",    "ar": "أوروبا",     "es": "Europa",   "zh": "欧洲"},  "parent_code": None, "level": 0},
    {"code": "OCE", "label": "Oceania",  "labels": {"en": "Oceania",  "fr": "Océanie",   "ar": "أوقيانوسيا", "es": "Oceanía",  "zh": "大洋洲"}, "parent_code": None, "level": 0},

    # Level 1 — Countries: Africa
    {"code": "DZA", "label": "Algeria",      "labels": {"en": "Algeria",      "fr": "Algérie",        "ar": "الجزائر",      "es": "Argelia",      "zh": "阿尔及利亚"}, "parent_code": "AFR", "level": 1},
    {"code": "AGO", "label": "Angola",       "labels": {"en": "Angola",       "fr": "Angola",         "ar": "أنغولا",       "es": "Angola",       "zh": "安哥拉"},     "parent_code": "AFR", "level": 1},
    {"code": "EGY", "label": "Egypt",        "labels": {"en": "Egypt",        "fr": "Égypte",         "ar": "مصر",          "es": "Egipto",       "zh": "埃及"},       "parent_code": "AFR", "level": 1},
    {"code": "ETH", "label": "Ethiopia",     "labels": {"en": "Ethiopia",     "fr": "Éthiopie",       "ar": "إثيوبيا",      "es": "Etiopía",      "zh": "埃塞俄比亚"}, "parent_code": "AFR", "level": 1},
    {"code": "KEN", "label": "Kenya",        "labels": {"en": "Kenya",        "fr": "Kenya",          "ar": "كينيا",        "es": "Kenia",        "zh": "肯尼亚"},     "parent_code": "AFR", "level": 1},
    {"code": "NGA", "label": "Nigeria",      "labels": {"en": "Nigeria",      "fr": "Nigeria",        "ar": "نيجيريا",      "es": "Nigeria",      "zh": "尼日利亚"},   "parent_code": "AFR", "level": 1},
    {"code": "MOZ", "label": "Mozambique",   "labels": {"en": "Mozambique",   "fr": "Mozambique",     "ar": "موزمبيق",      "es": "Mozambique",   "zh": "莫桑比克"},   "parent_code": "AFR", "level": 1},
    {"code": "TZA", "label": "Tanzania",     "labels": {"en": "Tanzania",     "fr": "Tanzanie",       "ar": "تنزانيا",      "es": "Tanzania",     "zh": "坦桑尼亚"},   "parent_code": "AFR", "level": 1},
    {"code": "ZAF", "label": "South Africa", "labels": {"en": "South Africa", "fr": "Afrique du Sud", "ar": "جنوب أفريقيا", "es": "Sudáfrica",    "zh": "南非"},       "parent_code": "AFR", "level": 1},

    # Level 1 — Countries: Americas
    {"code": "ARG", "label": "Argentina",     "labels": {"en": "Argentina",     "fr": "Argentine",   "ar": "الأرجنتين",        "es": "Argentina",      "zh": "阿根廷"},   "parent_code": "AMR", "level": 1},
    {"code": "BRA", "label": "Brazil",        "labels": {"en": "Brazil",        "fr": "Brésil",      "ar": "البرازيل",         "es": "Brasil",         "zh": "巴西"},     "parent_code": "AMR", "level": 1},
    {"code": "CAN", "label": "Canada",        "labels": {"en": "Canada",        "fr": "Canada",      "ar": "كندا",             "es": "Canadá",         "zh": "加拿大"},   "parent_code": "AMR", "level": 1},
    {"code": "COL", "label": "Colombia",      "labels": {"en": "Colombia",      "fr": "Colombie",    "ar": "كولومبيا",         "es": "Colombia",       "zh": "哥伦比亚"}, "parent_code": "AMR", "level": 1},
    {"code": "MEX", "label": "Mexico",        "labels": {"en": "Mexico",        "fr": "Mexique",     "ar": "المكسيك",          "es": "México",         "zh": "墨西哥"},   "parent_code": "AMR", "level": 1},
    {"code": "PER", "label": "Peru",          "labels": {"en": "Peru",          "fr": "Pérou",       "ar": "بيرو",             "es": "Perú",           "zh": "秘鲁"},     "parent_code": "AMR", "level": 1},
    {"code": "USA", "label": "United States", "labels": {"en": "United States", "fr": "États-Unis",  "ar": "الولايات المتحدة", "es": "Estados Unidos",  "zh": "美国"},    "parent_code": "AMR", "level": 1},

    # Level 1 — Countries: Asia
    {"code": "AFG", "label": "Afghanistan", "labels": {"en": "Afghanistan", "fr": "Afghanistan", "ar": "أفغانستان", "es": "Afganistán",  "zh": "阿富汗"},     "parent_code": "ASI", "level": 1},
    {"code": "BGD", "label": "Bangladesh",  "labels": {"en": "Bangladesh",  "fr": "Bangladesh",  "ar": "بنغلاديش",  "es": "Bangladés",   "zh": "孟加拉国"},   "parent_code": "ASI", "level": 1},
    {"code": "CHN", "label": "China",       "labels": {"en": "China",       "fr": "Chine",       "ar": "الصين",     "es": "China",       "zh": "中国"},       "parent_code": "ASI", "level": 1},
    {"code": "IND", "label": "India",       "labels": {"en": "India",       "fr": "Inde",        "ar": "الهند",     "es": "India",       "zh": "印度"},       "parent_code": "ASI", "level": 1},
    {"code": "IDN", "label": "Indonesia",   "labels": {"en": "Indonesia",   "fr": "Indonésie",   "ar": "إندونيسيا", "es": "Indonesia",   "zh": "印度尼西亚"}, "parent_code": "ASI", "level": 1},
    {"code": "JPN", "label": "Japan",       "labels": {"en": "Japan",       "fr": "Japon",       "ar": "اليابان",   "es": "Japón",       "zh": "日本"},       "parent_code": "ASI", "level": 1},
    {"code": "PAK", "label": "Pakistan",    "labels": {"en": "Pakistan",    "fr": "Pakistan",    "ar": "باكستان",   "es": "Pakistán",    "zh": "巴基斯坦"},   "parent_code": "ASI", "level": 1},

    # Level 1 — Countries: Europe
    {"code": "DEU", "label": "Germany",        "labels": {"en": "Germany",        "fr": "Allemagne",   "ar": "ألمانيا",          "es": "Alemania",    "zh": "德国"},   "parent_code": "EUR", "level": 1},
    {"code": "ESP", "label": "Spain",          "labels": {"en": "Spain",          "fr": "Espagne",     "ar": "إسبانيا",          "es": "España",      "zh": "西班牙"}, "parent_code": "EUR", "level": 1},
    {"code": "FRA", "label": "France",         "labels": {"en": "France",         "fr": "France",      "ar": "فرنسا",            "es": "Francia",     "zh": "法国"},   "parent_code": "EUR", "level": 1},
    {"code": "GBR", "label": "United Kingdom", "labels": {"en": "United Kingdom", "fr": "Royaume-Uni", "ar": "المملكة المتحدة",  "es": "Reino Unido", "zh": "英国"},   "parent_code": "EUR", "level": 1},
    {"code": "ITA", "label": "Italy",          "labels": {"en": "Italy",          "fr": "Italie",      "ar": "إيطاليا",          "es": "Italia",      "zh": "意大利"}, "parent_code": "EUR", "level": 1},
    {"code": "POL", "label": "Poland",         "labels": {"en": "Poland",         "fr": "Pologne",     "ar": "بولندا",           "es": "Polonia",     "zh": "波兰"},   "parent_code": "EUR", "level": 1},
    {"code": "ROU", "label": "Romania",        "labels": {"en": "Romania",        "fr": "Roumanie",    "ar": "رومانيا",          "es": "Rumanía",     "zh": "罗马尼亚"}, "parent_code": "EUR", "level": 1},

    # Level 1 — Countries: Oceania
    {"code": "AUS", "label": "Australia",        "labels": {"en": "Australia",        "fr": "Australie",        "ar": "أستراليا",  "es": "Australia",        "zh": "澳大利亚"}, "parent_code": "OCE", "level": 1},
    {"code": "NZL", "label": "New Zealand",      "labels": {"en": "New Zealand",      "fr": "Nouvelle-Zélande", "ar": "نيوزيلندا", "es": "Nueva Zelanda",    "zh": "新西兰"},   "parent_code": "OCE", "level": 1},
    {"code": "PNG", "label": "Papua New Guinea", "labels": {"en": "Papua New Guinea", "fr": "Papouasie-Nouvelle-Guinée", "ar": "بابوا غينيا الجديدة", "es": "Papúa Nueva Guinea", "zh": "巴布亚新几内亚"}, "parent_code": "OCE", "level": 1},
]


def _to_member(
    node: dict[str, Any],
    index: int,
    has_children: bool = False,
) -> GeneratedMember:
    return GeneratedMember(
        value=node,
        index=index,
        code=node["code"],
        extra=node,
        has_children=has_children,
    )


def _resolve_label(node: dict[str, Any], language: str | None) -> str:
    """Return the best label for *node* given the requested *language*.

    Falls back to the default 'label' field when no multilingual 'labels'
    map is present or the requested language is not available.
    """
    if language and "labels" in node:
        return node["labels"].get(language, node.get("label", ""))
    return node.get("label", "")


def _paginate_nodes(
    candidates: list[dict[str, Any]],
    offset: int,
    limit: int,
    sort_by: str | None = None,
    sort_dir: str = "asc",
    language: str | None = None,
    has_children_fn: "Callable[[str], bool] | None" = None,
) -> PaginatedResult:
    """Shared pagination helper for all tree generators.

    Args:
        candidates: Pre-filtered node list to paginate.
        offset: Zero-based start index.
        limit: Maximum members to return.
        sort_by: Node field to sort by ('code', 'label', 'rank', or any
            output field).  When 'label', locale-aware key uses
            ``_resolve_label`` with *language*.
        sort_dir: 'asc' (default) or 'desc'.
        language: RFC 5646 Language-Tag for label selection and sort
            collation.  Mirrors the ``?language=`` query parameter
            (STAC API Language Extension).
        has_children_fn: Optional callable ``(code) -> bool`` used to set
            ``GeneratedMember.has_children`` on each returned member.
    """
    if sort_by:
        reverse = sort_dir == "desc"
        if sort_by == "label":
            candidates = sorted(
                candidates,
                key=lambda n: _resolve_label(n, language).casefold(),
                reverse=reverse,
            )
        else:
            candidates = sorted(
                candidates,
                key=lambda n: n.get(sort_by, ""),
                reverse=reverse,
            )

    total = len(candidates)
    page = candidates[offset: offset + limit]
    members = [
        _to_member(
            node,
            offset + i,
            has_children=has_children_fn(node["code"]) if has_children_fn else False,
        )
        for i, node in enumerate(page)
    ]
    return PaginatedResult(
        dimension="",
        number_matched=total,
        number_returned=len(members),
        members=members,
        offset=offset,
        limit=limit,
    )


class StaticTreeGenerator(DimensionGenerator):
    """In-memory recursive tree generator for hierarchical nominal dimensions.

    Strategy: recursive — each member carries a ``parent_code`` field.
    The generator itself owns the hierarchy logic: adding a new strategy
    means adding a new generator subclass, not changing the spec schema.

    Supports Hierarchical conformance level: ``/children``, ``/ancestors``,
    and ``?parent=`` filter on ``/members``.
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
    def config(self) -> StaticTreeConfig:
        return StaticTreeConfig()

    @property
    def invertible(self) -> bool:
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
        """Return root members, or delegate to children() when parent is given."""
        parent: str | None = params.get("parent")
        if parent is not None:
            return self.children(
                parent,
                limit=limit,
                offset=offset,
                sort_by=params.get("sort_by"),
                sort_dir=params.get("sort_dir", "asc"),
                language=params.get("language"),
            )
        candidates = [n for n in self._nodes if n["parent_code"] is None]
        return _paginate_nodes(
            candidates,
            offset,
            limit,
            sort_by=params.get("sort_by"),
            sort_dir=params.get("sort_dir", "asc"),
            language=params.get("language"),
            has_children_fn=self.has_children,
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
        sort_by: str | None = None,
        sort_dir: str = "asc",
        language: str | None = None,
    ) -> PaginatedResult:
        """Return paginated direct children of *parent_code*."""
        candidates = [n for n in self._nodes if n["parent_code"] == parent_code]
        return _paginate_nodes(
            candidates,
            offset,
            limit,
            sort_by=sort_by,
            sort_dir=sort_dir,
            language=language,
            has_children_fn=self.has_children,
        )

    def ancestors(self, member_code: str) -> list[dict[str, Any]]:
        """Return ancestor chain from root to *member_code* (inclusive).

        Ordered from coarsest ancestor to the member itself.
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

    def has_children(self, member_code: str) -> bool:
        """Return True if any node lists *member_code* as its parent."""
        return any(n["parent_code"] == member_code for n in self._nodes)

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
            language: str | None = query.get("language")
            matched = [
                n for n in self._nodes
                if fnmatch.fnmatch(n["code"], pattern)
                or fnmatch.fnmatch(_resolve_label(n, language), pattern)
            ]
            page = matched[:limit]
            members = [
                _to_member(n, i, has_children=self.has_children(n["code"]))
                for i, n in enumerate(page)
            ]
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
    """In-memory leveled tree generator for hierarchical nominal dimensions.

    Strategy: leveled — hierarchy is imposed by named level definitions;
    the tree structure is NOT encoded in member data alone. The ``?level=N``
    parameter filters members to a specific level, mirroring the
    ``parameters`` object declared in each hierarchy level's metadata.

    Supports all StaticTreeGenerator operations plus level-based filtering::

        ?level=0             → all continents (root level)
        ?level=1             → all countries
        ?level=1&parent=AFR  → African countries only
        ?parent=ITA          → Italian regions (recursive children of ITA)

    Adding a new strategy (e.g., composite) means adding another subclass here.
    No spec schema changes are required.
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
        if level is None:
            return super().generate(extent_min, extent_max, limit, offset, **params)

        level_int = int(level)
        candidates = [n for n in self._nodes if n.get("level") == level_int]
        parent: str | None = params.get("parent")
        if parent is not None:
            candidates = [n for n in candidates if n["parent_code"] == parent]
        return _paginate_nodes(
            candidates,
            offset,
            limit,
            sort_by=params.get("sort_by"),
            sort_dir=params.get("sort_dir", "asc"),
            language=params.get("language"),
            has_children_fn=self.has_children,
        )

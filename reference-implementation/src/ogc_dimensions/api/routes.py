"""API routes for dimension generators.

Implements the generator capabilities per dimension:
  GET  /dimensions                              -- list registered dimensions
  GET  /dimensions/{dimension_id}/members      -- paginated members
  GET  /dimensions/{dimension_id}/extent        -- boundaries
  GET  /dimensions/{dimension_id}/inverse       -- single value inverse
  POST /dimensions/{dimension_id}/inverse       -- batch inverse
  GET  /dimensions/{dimension_id}/search        -- search members
  GET  /dimensions/{dimension_id}/children      -- direct children of a node
  GET  /dimensions/{dimension_id}/ancestors     -- ancestor chain for a member
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..generators import (
    DekadalGenerator,
    DimensionGenerator,
    IntegerRangeGenerator,
    LeveledTreeGenerator,
    PentadalAnnualGenerator,
    PentadalMonthlyGenerator,
    StaticTreeGenerator,
)
from ..generators.base import SearchProtocol

router = APIRouter()

# ---------------------------------------------------------------------------
# URL helpers — produce fully-qualified, proxy-aware links
# ---------------------------------------------------------------------------
_FORCE_HTTPS: bool = __import__("os").getenv("FORCE_HTTPS", "false").lower() in (
    "true", "1", "yes",
)


def _self_url(request: Request) -> str:
    """Full URL of the current request *without* query parameters.

    Respects ``FORCE_HTTPS`` env var for deployments behind TLS-terminating
    proxies that forward plain HTTP internally.
    """
    url = request.url.remove_query_params(keys=request.query_params.keys())
    scheme = "https" if _FORCE_HTTPS else url.scheme
    return f"{scheme}://{url.netloc}{url.path.rstrip('/')}"


def _parent_url(request: Request, levels_up: int = 1) -> str:
    """URL *n* path segments above the current request URL."""
    current = _self_url(request)
    parts = current.split("/")
    return "/".join(parts[: -levels_up]) if levels_up else current


@dataclass
class DimensionConfig:
    """A named dimension backed by a generator."""
    generator: DimensionGenerator
    description: str = ""
    extent_min: str = "2024-01-01"
    extent_max: str = "2024-12-31"


# Registry of named dimensions — each backed by a generator instance
DIMENSIONS: dict[str, DimensionConfig] = {
    "dekadal": DimensionConfig(
        generator=DekadalGenerator(),
        description="10-day periods (36/year). Used by FAO ASIS, FEWS NET, TUW-GEO.",
    ),
    "pentadal-monthly": DimensionConfig(
        generator=PentadalMonthlyGenerator(),
        description="5-day periods aligned to months (72/year). Used by CHIRPS, CDT, FAO.",
    ),
    "pentadal-annual": DimensionConfig(
        generator=PentadalAnnualGenerator(),
        description="5-day periods aligned to year start (73/year). Used by GPCP, CPC/NOAA.",
    ),
    "integer-range": DimensionConfig(
        generator=IntegerRangeGenerator(step=100),
        description="Evenly-spaced integer bins (step=100). Elevation bands, percentiles.",
        extent_min="0",
        extent_max="5000",
    ),
    "world-admin": DimensionConfig(
        generator=LeveledTreeGenerator(),
        description=(
            "Hierarchical administrative boundaries: 5 continents → 49 countries. "
            "Demonstrates the Hierarchical conformance level (/children, /ancestors)."
        ),
        extent_min="",
        extent_max="",
    ),
}


def _get_dimension(dimension_id: str) -> DimensionConfig:
    dim = DIMENSIONS.get(dimension_id)
    if dim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dimension '{dimension_id}' not found. "
            f"Available: {list(DIMENSIONS.keys())}",
        )
    return dim


def _member_to_dict(
    m,
    *,
    gen: DimensionGenerator | None = None,
    dim_base_url: str | None = None,
) -> dict[str, Any]:
    if m.extra:
        d = dict(m.extra)
    else:
        d: dict[str, Any] = {"value": m.value, "index": m.index}
        if m.code is not None:
            d["code"] = m.code
        if m.start is not None:
            d["start"] = m.start
        if m.end is not None:
            d["end"] = m.end

    # Member-level navigation links (opt-in via ?links=true)
    if gen is not None and dim_base_url is not None and m.code is not None:
        member_links: list[dict[str, str]] = []
        if gen.has_children(m.code):
            member_links.append({
                "rel": "children",
                "href": f"{dim_base_url}/children?parent={m.code}",
                "type": "application/json",
            })
        member_links.append({
            "rel": "ancestors",
            "href": f"{dim_base_url}/ancestors?member={m.code}",
            "type": "application/json",
        })
        d["links"] = member_links

    return d


@router.get("/")
async def list_dimensions(request: Request):
    """List registered dimensions and their generator capabilities."""
    base = _self_url(request)  # e.g. https://host/prefix/dimensions
    return {
        "dimensions": [
            {
                "id": dim_id,
                "description": cfg.description,
                "generator": {
                    "type": cfg.generator.generator_type,
                    "invertible": cfg.generator.invertible,
                    "capabilities": [c.value for c in cfg.generator.capabilities],
                    "search_protocols": [s.value for s in cfg.generator.search_protocols],
                },
                "links": [
                    {
                        "rel": "members",
                        "href": f"{base}/{dim_id}/members",
                        "type": "application/json",
                    },
                    {
                        "rel": "extent",
                        "href": f"{base}/{dim_id}/extent",
                        "type": "application/json",
                    },
                ],
            }
            for dim_id, cfg in DIMENSIONS.items()
        ]
    }


@router.get("/{dimension_id}/members")
async def generate(
    request: Request,
    dimension_id: str,
    extent_min: str | None = Query(None, description="Extent minimum (defaults to dimension config)"),
    extent_max: str | None = Query(None, description="Extent maximum (defaults to dimension config)"),
    limit: int = Query(100, ge=1, le=10000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    format: str = Query("structured", description="Output format: structured, datetime, native"),
    parent: str | None = Query(None, description="Filter to direct children of this member code (Hierarchical conformance)"),
    level: int | None = Query(None, description="Hierarchy level filter — return only members at this level (leveled strategy)"),
    links: bool = Query(False, description="Include per-member navigation links (children, ancestors). Only effective for hierarchical dimensions."),
):
    """Generate paginated dimension members within extent.

    For hierarchical dimensions, ``?parent=X`` returns direct children of X,
    equivalent to ``/children?parent=X``.  Without ``parent``, root members
    (those with no parent) are returned.  The ``?level=N`` parameter filters
    to a specific hierarchy level (leveled strategy).
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    ext_min = extent_min or cfg.extent_min
    ext_max = extent_max or cfg.extent_max

    result = gen.generate(ext_min, ext_max, limit=limit, offset=offset, parent=parent, level=level)

    # Build member-level link context only when opt-in and hierarchical
    emit_member_links = links and gen.hierarchical
    link_gen = gen if emit_member_links else None
    link_base = _parent_url(request) if emit_member_links else None  # .../dimensions/{id}

    values: list[Any]
    if format == "datetime":
        values = [m.value for m in result.members]
    elif format == "native":
        values = [m.code for m in result.members]
    else:
        values = [_member_to_dict(m, gen=link_gen, dim_base_url=link_base) for m in result.members]

    self_url = _self_url(request)  # e.g. https://host/prefix/dimensions/{id}/members
    _extra_qs = ""
    if parent:
        _extra_qs += f"&parent={parent}"
    if level is not None:
        _extra_qs += f"&level={level}"

    links = [
        {"rel": "self", "href": f"{self_url}?limit={limit}&offset={offset}{_extra_qs}", "type": "application/json"},
    ]
    if offset + limit < result.number_matched:
        links.append(
            {"rel": "next", "href": f"{self_url}?limit={limit}&offset={offset + limit}{_extra_qs}", "type": "application/json"}
        )
    if offset > 0:
        prev_offset = max(0, offset - limit)
        links.append(
            {"rel": "prev", "href": f"{self_url}?limit={limit}&offset={prev_offset}{_extra_qs}", "type": "application/json"}
        )
    if parent and gen.hierarchical:
        dim_base = _parent_url(request)  # .../dimensions/{id}
        links.append(
            {"rel": "parent", "href": f"{dim_base}/members?code={parent}", "type": "application/json"}
        )

    response: dict[str, Any] = {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "numberMatched": result.number_matched,
        "numberReturned": result.number_returned,
        "values": values,
        "links": links,
    }
    if parent:
        response["parent"] = parent
    return response


@router.get("/{dimension_id}/extent")
async def extent(
    dimension_id: str,
    extent_min: str | None = Query(None, description="Extent minimum"),
    extent_max: str | None = Query(None, description="Extent maximum"),
):
    """Return dimension boundaries in native and standard representations."""
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    ext_min = extent_min or cfg.extent_min
    ext_max = extent_max or cfg.extent_max

    result = gen.extent(ext_min, ext_max)

    return {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "native": {"min": result.native_min, "max": result.native_max},
        "standard": {"min": result.standard_min, "max": result.standard_max},
        "size": result.size,
    }


@router.get("/{dimension_id}/inverse")
async def inverse(
    dimension_id: str,
    value: str = Query(..., description="Value to map to a dimension member"),
):
    """Map a value to its dimension member (single value)."""
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    if not gen.invertible:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (generator: {gen.generator_type}) "
            f"is not invertible and does not support inverse.",
        )

    result = gen.inverse(value)
    response: dict[str, Any] = {"valid": result.valid, "dimension": dimension_id}

    if result.valid:
        response["member"] = result.member
        response["coordinate"] = result.coordinate
        response["range"] = result.range
        response["index"] = result.index
    else:
        response["reason"] = result.reason
        if result.nearest:
            response["nearest"] = result.nearest

    return response


class BatchInverseRequest(BaseModel):
    values: list[str]
    on_invalid: str = "reject"


@router.post("/{dimension_id}/inverse")
async def inverse_batch(
    dimension_id: str,
    request: BatchInverseRequest,
):
    """Batch inverse for pipeline operations."""
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    if not gen.invertible:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (generator: {gen.generator_type}) "
            f"is not invertible.",
        )

    results = gen.inverse_batch(request.values, on_invalid=request.on_invalid)

    return {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "count": len(results),
        "results": [
            {
                "valid": r.valid,
                **({"member": r.member, "index": r.index} if r.valid else {}),
                **({"reason": r.reason} if not r.valid else {}),
                **({"nearest": r.nearest} if r.nearest else {}),
            }
            for r in results
        ],
    }


@router.get("/{dimension_id}/search")
async def search(
    dimension_id: str,
    exact: str | None = Query(None, description="Exact match on member code"),
    min: str | None = Query(None, description="Range minimum"),
    max: str | None = Query(None, description="Range maximum"),
    like: str | None = Query(None, description="Pattern match (fnmatch)"),
    extent_min: str | None = Query(None, description="Extent minimum"),
    extent_max: str | None = Query(None, description="Extent maximum"),
    limit: int = Query(100, ge=1, le=10000),
):
    """Search for dimension members matching a query."""
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    ext_min = extent_min or cfg.extent_min
    ext_max = extent_max or cfg.extent_max

    if exact is not None:
        protocol = SearchProtocol.EXACT
        query = {"exact": exact, "limit": limit}
    elif min is not None or max is not None:
        protocol = SearchProtocol.RANGE
        query = {
            "min": min or ext_min,
            "max": max or ext_max,
            "limit": limit,
        }
    elif like is not None:
        protocol = SearchProtocol.LIKE
        query = {"like": like, "limit": limit}
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one search parameter: exact, min/max, or like.",
        )

    if protocol not in gen.search_protocols:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (generator: {gen.generator_type}) "
            f"does not support search protocol '{protocol.value}'. "
            f"Supported: {[s.value for s in gen.search_protocols]}",
        )

    result = gen.search(protocol, ext_min, ext_max, **query)

    return {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "protocol": protocol.value,
        "numberMatched": result.number_matched,
        "numberReturned": result.number_returned,
        "values": [_member_to_dict(m) for m in result.members],
    }


@router.get("/{dimension_id}/children")
async def children(
    request: Request,
    dimension_id: str,
    parent: str = Query(..., description="Return direct children of this member code"),
    limit: int = Query(100, ge=1, le=10000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    links: bool = Query(False, description="Include per-member navigation links (children, ancestors)."),
):
    """Return paginated direct children of a hierarchy node.

    Mirrors the STAC API Children Extension (https://api.stacspec.org/v1.0.0-rc.2/children)
    applied to dimension members rather than STAC Collections.
    Requires Hierarchical conformance level on the generator.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    if not gen.hierarchical:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (generator: {gen.generator_type}) "
            "does not support Hierarchical operations (/children, /ancestors).",
        )

    result = gen.children(parent, limit=limit, offset=offset)

    self_url = _self_url(request)
    dim_base = _parent_url(request)

    # Member-level link context (opt-in)
    link_gen = gen if links else None
    link_base = dim_base if links else None

    resp_links = [
        {"rel": "self", "href": f"{self_url}?parent={parent}&limit={limit}&offset={offset}", "type": "application/json"},
    ]
    if offset + limit < result.number_matched:
        resp_links.append(
            {"rel": "next", "href": f"{self_url}?parent={parent}&limit={limit}&offset={offset + limit}", "type": "application/json"}
        )
    if offset > 0:
        prev_offset = max(0, offset - limit)
        resp_links.append(
            {"rel": "prev", "href": f"{self_url}?parent={parent}&limit={limit}&offset={prev_offset}", "type": "application/json"}
        )
    resp_links.append(
        {"rel": "parent", "href": f"{dim_base}/members?code={parent}", "type": "application/json"}
    )

    return {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "parent": parent,
        "numberMatched": result.number_matched,
        "numberReturned": result.number_returned,
        "values": [_member_to_dict(m, gen=link_gen, dim_base_url=link_base) for m in result.members],
        "links": resp_links,
    }


@router.get("/{dimension_id}/ancestors")
async def ancestors(
    dimension_id: str,
    member: str = Query(..., description="Return ancestors of this member code"),
):
    """Return the ancestor chain for a member, from root to the member (inclusive).

    Requires Hierarchical conformance level on the generator.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.generator
    if not gen.hierarchical:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (generator: {gen.generator_type}) "
            "does not support Hierarchical operations (/children, /ancestors).",
        )

    chain = gen.ancestors(member)
    if not chain:
        raise HTTPException(
            status_code=404,
            detail=f"Member '{member}' not found in dimension '{dimension_id}'.",
        )

    return {
        "dimension": dimension_id,
        "generator": gen.generator_type,
        "member": member,
        "ancestors": chain,
    }

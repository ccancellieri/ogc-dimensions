"""API routes for dimension generators.

Implements the four generator capabilities:
  GET  /generators                           -- list available generators
  GET  /generators/{type}/generate           -- paginated members
  GET  /generators/{type}/extent             -- boundaries
  GET  /generators/{type}/inverse            -- single value inverse
  POST /generators/{type}/inverse            -- batch inverse
  GET  /generators/{type}/search             -- search members
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..generators import (
    DekadalGenerator,
    DimensionGenerator,
    IntegerRangeGenerator,
    PentadalAnnualGenerator,
    PentadalMonthlyGenerator,
)
from ..generators.base import SearchProtocol

router = APIRouter()

# Registry of available generators
GENERATORS: dict[str, DimensionGenerator] = {
    "dekadal": DekadalGenerator(),
    "pentadal-monthly": PentadalMonthlyGenerator(),
    "pentadal-annual": PentadalAnnualGenerator(),
    "integer-range": IntegerRangeGenerator(step=100),
}


def _get_generator(generator_type: str) -> DimensionGenerator:
    gen = GENERATORS.get(generator_type)
    if gen is None:
        raise HTTPException(
            status_code=404,
            detail=f"Generator '{generator_type}' not found. "
            f"Available: {list(GENERATORS.keys())}",
        )
    return gen


def _member_to_dict(m) -> dict[str, Any]:
    d: dict[str, Any] = {"value": m.value, "index": m.index}
    if m.code is not None:
        d["code"] = m.code
    if m.start is not None:
        d["start"] = m.start
    if m.end is not None:
        d["end"] = m.end
    return d


@router.get("")
async def list_generators():
    """List available dimension generators and their capabilities."""
    return {
        "generators": [
            {
                "type": gen.generator_type,
                "bijective": gen.bijective,
                "capabilities": [c.value for c in gen.capabilities],
                "search_protocols": [s.value for s in gen.search_protocols],
                "links": [
                    {
                        "rel": "generate",
                        "href": f"/generators/{gen.generator_type}/generate",
                    },
                    {
                        "rel": "extent",
                        "href": f"/generators/{gen.generator_type}/extent",
                    },
                ],
            }
            for gen in GENERATORS.values()
        ]
    }


@router.get("/{generator_type}/generate")
async def generate(
    generator_type: str,
    extent_min: str = Query("2024-01-01", description="Extent minimum"),
    extent_max: str = Query("2024-12-31", description="Extent maximum"),
    limit: int = Query(100, ge=1, le=10000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    format: str = Query("structured", description="Output format: structured, datetime, native"),
):
    """Generate paginated dimension members within extent."""
    gen = _get_generator(generator_type)
    result = gen.generate(extent_min, extent_max, limit=limit, offset=offset)

    values: list[Any]
    if format == "datetime":
        values = [m.value for m in result.members]
    elif format == "native":
        values = [m.code for m in result.members]
    else:
        values = [_member_to_dict(m) for m in result.members]

    links = [
        {"rel": "self", "href": f"/generators/{generator_type}/generate?limit={limit}&offset={offset}", "type": "application/json"},
    ]
    if offset + limit < result.number_matched:
        links.append(
            {"rel": "next", "href": f"/generators/{generator_type}/generate?limit={limit}&offset={offset + limit}", "type": "application/json"}
        )
    if offset > 0:
        prev_offset = max(0, offset - limit)
        links.append(
            {"rel": "prev", "href": f"/generators/{generator_type}/generate?limit={limit}&offset={prev_offset}", "type": "application/json"}
        )

    return {
        "dimension": result.dimension,
        "generator": generator_type,
        "numberMatched": result.number_matched,
        "numberReturned": result.number_returned,
        "values": values,
        "links": links,
    }


@router.get("/{generator_type}/extent")
async def extent(
    generator_type: str,
    extent_min: str = Query("2024-01-01", description="Extent minimum"),
    extent_max: str = Query("2024-12-31", description="Extent maximum"),
):
    """Return dimension boundaries in native and standard representations."""
    gen = _get_generator(generator_type)
    result = gen.extent(extent_min, extent_max)

    return {
        "generator": generator_type,
        "native": {"min": result.native_min, "max": result.native_max},
        "standard": {"min": result.standard_min, "max": result.standard_max},
        "size": result.size,
    }


@router.get("/{generator_type}/inverse")
async def inverse(
    generator_type: str,
    value: str = Query(..., description="Value to map to a dimension member"),
):
    """Map a value to its dimension member (single value)."""
    gen = _get_generator(generator_type)
    if not gen.bijective:
        raise HTTPException(
            status_code=501,
            detail=f"Generator '{generator_type}' is not bijective and does not support inverse.",
        )

    result = gen.inverse(value)
    response: dict[str, Any] = {"valid": result.valid}

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


@router.post("/{generator_type}/inverse")
async def inverse_batch(
    generator_type: str,
    request: BatchInverseRequest,
):
    """Batch inverse for pipeline operations."""
    gen = _get_generator(generator_type)
    if not gen.bijective:
        raise HTTPException(
            status_code=501,
            detail=f"Generator '{generator_type}' is not bijective.",
        )

    results = gen.inverse_batch(request.values, on_invalid=request.on_invalid)

    return {
        "generator": generator_type,
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


@router.get("/{generator_type}/search")
async def search(
    generator_type: str,
    exact: str | None = Query(None, description="Exact match on member code"),
    min: str | None = Query(None, description="Range minimum"),
    max: str | None = Query(None, description="Range maximum"),
    like: str | None = Query(None, description="Pattern match (fnmatch)"),
    extent_min: str = Query("2024-01-01", description="Extent minimum"),
    extent_max: str = Query("2024-12-31", description="Extent maximum"),
    limit: int = Query(100, ge=1, le=10000),
):
    """Search for dimension members matching a query."""
    gen = _get_generator(generator_type)

    if exact is not None:
        protocol = SearchProtocol.EXACT
        query = {"exact": exact, "limit": limit}
    elif min is not None or max is not None:
        protocol = SearchProtocol.RANGE
        query = {
            "min": min or extent_min,
            "max": max or extent_max,
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
            detail=f"Generator '{generator_type}' does not support search protocol '{protocol.value}'. "
            f"Supported: {[s.value for s in gen.search_protocols]}",
        )

    result = gen.search(protocol, extent_min, extent_max, **query)

    return {
        "dimension": result.dimension,
        "generator": generator_type,
        "protocol": protocol.value,
        "numberMatched": result.number_matched,
        "numberReturned": result.number_returned,
        "values": [_member_to_dict(m) for m in result.members],
    }

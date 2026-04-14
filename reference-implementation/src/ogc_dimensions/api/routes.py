"""API routes for OGC API - Dimensions.

Serves dimension collections as OGC API - Records and dimension members as
GeoJSON Features (``geometry: null``), following the OGC Dimensions Building
Blocks profile (a Records profile).

Endpoints:
  GET  /dimensions                              -- list dimension collections
  GET  /dimensions/conformance                  -- conformance declaration
  GET  /dimensions/{dimension_id}               -- dimension collection (full provider definition)
  GET  /dimensions/{dimension_id}/items         -- paginated members (OGC Records /items)
  GET  /dimensions/{dimension_id}/extent        -- boundaries
  GET  /dimensions/{dimension_id}/inverse       -- single value → member mapping
  POST /dimensions/{dimension_id}/inverse       -- batch inverse
  GET  /dimensions/{dimension_id}/search        -- search members
  GET  /dimensions/{dimension_id}/children      -- direct children (STAC Children Extension pattern)
  GET  /dimensions/{dimension_id}/ancestors     -- ancestor chain from root to member
  GET  /dimensions/{dimension_id}/queryables    -- queryable member properties
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..providers import (
    DailyPeriodProvider,
    DimensionProvider,
    InverseError,
    IntegerRangeProvider,
    LeveledTreeProvider,
    StaticTreeProvider,
)
from ..providers.base import SearchProtocol

router = APIRouter()

# ---------------------------------------------------------------------------
# Conformance URIs
# ---------------------------------------------------------------------------
OGC_DIMENSIONS_CONFORMANCE = [
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-core",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-collection",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/core",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-inverse",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-hierarchical",
]

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
    """A named dimension backed by a provider."""
    provider: DimensionProvider
    description: str = ""
    dimension_type: str = "other"
    extent_min: str = "2024-01-01"
    extent_max: str = "2024-12-31"


# Registry of named dimensions — each backed by a provider instance
DIMENSIONS: dict[str, DimensionConfig] = {
    "dekadal": DimensionConfig(
        provider=DailyPeriodProvider(period_days=10, scheme="monthly"),
        description="10-day periods (36/year). Used by FAO ASIS, FEWS NET, TUW-GEO.",
        dimension_type="temporal",
    ),
    "pentadal-monthly": DimensionConfig(
        provider=DailyPeriodProvider(period_days=5, scheme="monthly"),
        description="5-day periods aligned to months (72/year). Used by CHIRPS, CDT, FAO.",
        dimension_type="temporal",
    ),
    "pentadal-annual": DimensionConfig(
        provider=DailyPeriodProvider(period_days=5, scheme="annual"),
        description="5-day periods aligned to year start (73/year). Used by GPCP, CPC/NOAA.",
        dimension_type="temporal",
    ),
    "integer-range": DimensionConfig(
        provider=IntegerRangeProvider(step=100),
        description="Evenly-spaced integer bins (step=100). Elevation bands, percentiles.",
        dimension_type="other",
        extent_min="0",
        extent_max="5000",
    ),
    "world-admin": DimensionConfig(
        provider=LeveledTreeProvider(),
        description=(
            "Hierarchical administrative boundaries: 5 continents -> 49 countries. "
            "Demonstrates the Hierarchical conformance level (/children, /ancestors)."
        ),
        dimension_type="nominal",
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


# ---------------------------------------------------------------------------
# Member -> GeoJSON Feature conversion
# ---------------------------------------------------------------------------

def _member_to_feature(
    m,
    *,
    dim_type: str = "other",
    gen: DimensionProvider | None = None,
    dim_base_url: str | None = None,
) -> dict[str, Any]:
    """Convert a ``ProducedMember`` to a GeoJSON Feature (OGC Record).

    Follows the ``dimension-member`` building block schema:
    ``type: Feature``, ``id``, ``geometry: null``, ``properties``
    with ``dimension:*`` namespaced fields.
    """
    code = m.code or str(m.value)
    extra = m.extra or {}

    props: dict[str, Any] = {
        "type": "dimension-member",
        "dimension:type": dim_type,
        "dimension:code": code,
        "dimension:index": m.index,
    }

    # Title — use label from extra, or the code
    props["title"] = extra.get("label") or code

    # Temporal interval (Records time object)
    if m.start is not None and m.end is not None:
        props["time"] = {"interval": [str(m.start), str(m.end)]}
        props["dimension:start"] = str(m.start)
        props["dimension:end"] = str(m.end)

    # Integer range bounds
    if "lower" in extra:
        props["dimension:start"] = extra["lower"]
    if "upper" in extra:
        props["dimension:end"] = extra["upper"]

    # Multilingual labels
    labels = extra.get("labels")
    if labels and isinstance(labels, dict):
        props["labels"] = labels

    # Hierarchy properties
    parent_code = extra.get("parent_code")
    if parent_code is not None:
        props["dimension:parent"] = parent_code
    level = extra.get("level")
    if level is not None:
        props["dimension:level"] = level
    if m.has_children:
        props["dimension:has_children"] = True

    # Pass-through extra fields
    for key in ("unit", "rank"):
        if key in extra:
            props[key] = extra[key]

    # Build links
    feature_links: list[dict[str, str]] = []
    if gen is not None and dim_base_url is not None and code:
        feature_links.append({
            "href": f"{dim_base_url}/items/{code}",
            "rel": "self",
            "type": "application/geo+json",
        })
        feature_links.append({
            "href": dim_base_url,
            "rel": "collection",
            "type": "application/json",
        })
        if gen.has_children(code):
            feature_links.append({
                "rel": "children",
                "href": f"{dim_base_url}/children?parent={code}",
                "type": "application/geo+json",
            })
        feature_links.append({
            "rel": "ancestors",
            "href": f"{dim_base_url}/ancestors?member={code}",
            "type": "application/json",
        })

    feature: dict[str, Any] = {
        "type": "Feature",
        "id": code,
        "geometry": None,
        "properties": props,
    }
    if feature_links:
        feature["links"] = feature_links

    return feature


def _ancestor_dict_to_feature(
    node: dict[str, Any],
    *,
    dim_type: str = "other",
    gen: DimensionProvider | None = None,
    dim_base_url: str | None = None,
) -> dict[str, Any]:
    """Convert a raw ancestor dict (from ``gen.ancestors()``) to a GeoJSON Feature."""
    code = node.get("code", "")
    props: dict[str, Any] = {
        "type": "dimension-member",
        "dimension:type": dim_type,
        "dimension:code": code,
    }
    props["title"] = node.get("label") or code

    labels = node.get("labels")
    if labels and isinstance(labels, dict):
        props["labels"] = labels

    parent_code = node.get("parent_code")
    if parent_code is not None:
        props["dimension:parent"] = parent_code
    level = node.get("level")
    if level is not None:
        props["dimension:level"] = level

    feature_links: list[dict[str, str]] = []
    if gen is not None and dim_base_url is not None and code:
        feature_links.append({
            "href": f"{dim_base_url}/items/{code}",
            "rel": "self",
            "type": "application/geo+json",
        })
        if gen.has_children(code):
            feature_links.append({
                "rel": "children",
                "href": f"{dim_base_url}/children?parent={code}",
                "type": "application/geo+json",
            })

    feature: dict[str, Any] = {
        "type": "Feature",
        "id": code,
        "geometry": None,
        "properties": props,
    }
    if feature_links:
        feature["links"] = feature_links

    return feature


def _build_feature_collection(
    features: list[dict[str, Any]],
    *,
    number_matched: int,
    number_returned: int,
    links: list[dict[str, str]],
) -> dict[str, Any]:
    """Build an OGC Records-style FeatureCollection response envelope."""
    return {
        "type": "FeatureCollection",
        "numberMatched": number_matched,
        "numberReturned": number_returned,
        "features": features,
        "links": links,
    }


# ---------------------------------------------------------------------------
# Dimension collection helper
# ---------------------------------------------------------------------------

def _dimension_to_collection(
    dim_id: str, cfg: DimensionConfig, base_url: str,
) -> dict[str, Any]:
    """Convert a DimensionConfig to an OGC Records collection object."""
    gen = cfg.provider
    dim_url = f"{base_url}/{dim_id}"
    # Full provider definition (lives at the dimension collection level)
    provider: dict[str, Any] = {
        "type": gen.provider_type,
        "config": gen.config_as_dict(),
        "invertible": gen.invertible,
        "hierarchical": gen.hierarchical,
        "search": [s.value for s in gen.search_protocols],
    }
    if hasattr(gen, "language_support") and gen.language_support:
        provider["language_support"] = gen.language_support

    # Conformance URIs — core always present; add optional capabilities
    conforms_to = [
        "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/core",
        "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection",
        "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member",
        "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination",
    ]
    if gen.invertible:
        conforms_to.append("http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-inverse")
    if gen.hierarchical:
        conforms_to.append("http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-hierarchical")

    # Links — always include self, items, queryables; add capability links conditionally
    links: list[dict[str, str]] = [
        {"rel": "self", "href": dim_url, "type": "application/json"},
        {"rel": "items", "href": f"{dim_url}/items", "type": "application/geo+json", "title": "Paginated members"},
        {"rel": "queryables", "href": f"{dim_url}/queryables", "type": "application/schema+json", "title": "Queryable and sortable member properties"},
    ]
    if gen.invertible:
        links.append({"rel": "inverse", "href": f"{dim_url}/inverse", "type": "application/json", "title": "Value-to-member inverse mapping"})
    if gen.hierarchical:
        links.append({"rel": "children", "href": f"{dim_url}/children", "type": "application/geo+json", "title": "Direct children of a hierarchy node"})
        links.append({"rel": "ancestors", "href": f"{dim_url}/ancestors", "type": "application/json", "title": "Ancestor chain from root to member"})

    collection: dict[str, Any] = {
        "id": dim_id,
        "title": dim_id.replace("-", " ").title(),
        "description": cfg.description,
        "itemType": "record",
        # Full provider definition at collection level
        "provider": provider,
        "conformsTo": conforms_to,
        # Slim cube:dimensions reference for STAC clients
        "cube:dimensions": {
            dim_id: {
                "type": cfg.dimension_type,
                "provider": {
                    "type": gen.provider_type,
                    "href": dim_url,
                },
            }
        },
        "links": links,
    }

    # Add extent for temporal dimensions
    if cfg.dimension_type == "temporal" and cfg.extent_min and cfg.extent_max:
        collection["extent"] = {
            "temporal": {
                "interval": [[f"{cfg.extent_min}T00:00:00Z", f"{cfg.extent_max}T00:00:00Z"]]
            }
        }

    return collection


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def list_dimensions(request: Request):
    """List registered dimensions as OGC Records collections."""
    base = _self_url(request)
    return {
        "collections": [
            _dimension_to_collection(dim_id, cfg, base)
            for dim_id, cfg in DIMENSIONS.items()
        ],
        "links": [
            {"rel": "self", "href": base, "type": "application/json"},
        ],
    }


@router.get("/conformance")
async def conformance():
    """OGC API conformance declaration."""
    return {"conformsTo": OGC_DIMENSIONS_CONFORMANCE}


@router.get("/{dimension_id}/queryables")
async def queryables(
    request: Request,
    dimension_id: str,
):
    """Return the queryable and sortable properties for this dimension's members.

    Follows OGC API - Features Part 3 (Filtering) -- a JSON Schema document
    listing the output fields that clients may use as filter or sort targets.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    self_url = _self_url(request)

    output_schema: dict[str, Any] = {}
    if hasattr(gen, "output_schema"):
        output_schema = gen.output_schema or {}

    properties = output_schema.get("properties", {
        "code": {"type": "string", "title": "Member code"},
    })

    x_ogc_params: dict[str, Any] = {
        "sort_dir": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "asc",
            "title": "Sort direction",
        },
    }
    sortable_fields = ["code"]
    if any("label" in str(p) for p in properties):
        sortable_fields.append("label")
    if "rank" in properties:
        sortable_fields.append("rank")
    x_ogc_params["sort_by"] = {
        "type": "string",
        "enum": sortable_fields,
        "title": "Sort field",
    }
    if gen.hierarchical and hasattr(gen, "language_support"):
        langs = [ls.get("code") for ls in (gen.language_support or []) if ls.get("code")]
        if langs:
            x_ogc_params["language"] = {
                "type": "string",
                "title": "Language",
                "description": "RFC 5646 Language-Tag.",
                "examples": langs,
            }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{self_url}",
        "type": "object",
        "title": f"Queryables for dimension '{dimension_id}'",
        "properties": properties,
        "x-ogc-config": gen.config_as_dict(),
        "x-ogc-parameters": x_ogc_params,
    }


@router.get("/{dimension_id}/items")
async def items(
    request: Request,
    dimension_id: str,
    extent_min: str | None = Query(None, description="Extent minimum (defaults to dimension config)"),
    extent_max: str | None = Query(None, description="Extent maximum (defaults to dimension config)"),
    limit: int = Query(100, ge=1, le=10000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    parent: str | None = Query(None, description="Filter to direct children of this member code (Hierarchical conformance, cf. OGC Common #298)"),
    level: int | None = Query(None, description="Hierarchy level filter (leveled strategy)"),
    language: str | None = Query(None, description="RFC 5646 Language-Tag selecting label language and sort collation."),
    sort_by: str | None = Query(None, description="Output field to sort members by (e.g. 'code', 'label', 'rank')."),
    sort_dir: str = Query("asc", description="Sort direction: 'asc' (default) or 'desc'."),
):
    """Paginated dimension members as an OGC Records FeatureCollection.

    Standard Records /items endpoint backed by the dimension provider.
    Each member is a GeoJSON Feature with ``geometry: null`` and
    ``dimension:*`` properties per the dimension-member building block.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    ext_min = extent_min or cfg.extent_min
    ext_max = extent_max or cfg.extent_max

    effective_lang = language or request.headers.get("accept-language", "").split(",")[0].split(";")[0].strip() or None

    result = gen.generate(
        ext_min, ext_max,
        limit=limit, offset=offset,
        parent=parent, level=level,
        language=effective_lang,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    # Build member-level link context for hierarchical dimensions.
    # dim_base is the collection URL (one level up from /items).
    emit_links = gen.hierarchical
    link_gen = gen if emit_links else None
    dim_base = _parent_url(request, levels_up=1) if emit_links else None

    features = [
        _member_to_feature(m, dim_type=cfg.dimension_type, gen=link_gen, dim_base_url=dim_base)
        for m in result.members
    ]

    self_url = _self_url(request)
    extra_qs = ""
    if parent:
        extra_qs += f"&parent={parent}"
    if level is not None:
        extra_qs += f"&level={level}"
    if effective_lang:
        extra_qs += f"&language={effective_lang}"
    if sort_by:
        extra_qs += f"&sort_by={sort_by}&sort_dir={sort_dir}"

    resp_links = [
        {"rel": "self", "href": f"{self_url}?limit={limit}&offset={offset}{extra_qs}", "type": "application/geo+json"},
        {"rel": "collection", "href": _parent_url(request), "type": "application/json"},
    ]
    if offset + limit < result.number_matched:
        resp_links.append(
            {"rel": "next", "href": f"{self_url}?limit={limit}&offset={offset + limit}{extra_qs}", "type": "application/geo+json"}
        )
    if offset > 0:
        prev_offset = max(0, offset - limit)
        resp_links.append(
            {"rel": "prev", "href": f"{self_url}?limit={limit}&offset={prev_offset}{extra_qs}", "type": "application/geo+json"}
        )

    body = _build_feature_collection(
        features,
        number_matched=result.number_matched,
        number_returned=result.number_returned,
        links=resp_links,
    )

    if effective_lang:
        return JSONResponse(content=body, headers={"Content-Language": effective_lang})
    return body


@router.get("/{dimension_id}/extent")
async def extent(
    dimension_id: str,
    extent_min: str | None = Query(None, description="Extent minimum"),
    extent_max: str | None = Query(None, description="Extent maximum"),
):
    """Return dimension boundaries in native and standard representations."""
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    ext_min = extent_min or cfg.extent_min
    ext_max = extent_max or cfg.extent_max

    result = gen.extent(ext_min, ext_max)

    return {
        "dimension": dimension_id,
        "provider": gen.provider_type,
        "native": {"min": result.native_min, "max": result.native_max},
        "standard": {"min": result.standard_min, "max": result.standard_max},
        "size": result.size,
    }


@router.get("/{dimension_id}/inverse")
async def inverse(
    request: Request,
    dimension_id: str,
    value: str = Query(..., description="Value to map to a dimension member"),
):
    """Map a value to its dimension member.

    Returns the member Record as a GeoJSON Feature on success, or
    ``404 {code, description[, nearest]}`` if the value cannot be mapped.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    if not gen.invertible:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (provider: {gen.provider_type}) "
            f"is not invertible and does not support inverse.",
        )

    try:
        member = gen.inverse(value)
    except InverseError as err:
        return JSONResponse(status_code=404, content=err.to_dict())

    dim_base = _parent_url(request)
    return _member_to_feature(
        member,
        dim_type=cfg.dimension_type,
        gen=gen,
        dim_base_url=dim_base,
    )


class BatchInverseRequest(BaseModel):
    values: list[str]


@router.post("/{dimension_id}/inverse")
async def inverse_batch(
    request: Request,
    dimension_id: str,
    body: BatchInverseRequest,
):
    """Batch inverse for pipeline operations.

    Returns a FeatureCollection of mapped members. Values that cannot be
    mapped appear in a parallel ``errors`` array (not part of the normative
    ``dimension-inverse`` conformance class — batch is an implementation
    convenience).
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    if not gen.invertible:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (provider: {gen.provider_type}) "
            f"is not invertible.",
        )

    dim_base = _parent_url(request)
    features: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for value, result in zip(body.values, gen.inverse_batch(body.values)):
        if isinstance(result, InverseError):
            errors.append({"value": value, **result.to_dict()})
        else:
            features.append(
                _member_to_feature(
                    result,
                    dim_type=cfg.dimension_type,
                    gen=gen,
                    dim_base_url=dim_base,
                )
            )

    return {
        "type": "FeatureCollection",
        "numberMatched": len(features),
        "numberReturned": len(features),
        "features": features,
        "errors": errors,
    }


@router.get("/{dimension_id}/search")
async def search(
    request: Request,
    dimension_id: str,
    exact: str | None = Query(None, description="Exact match on member code"),
    min: str | None = Query(None, description="Range minimum"),
    max: str | None = Query(None, description="Range maximum"),
    like: str | None = Query(None, description="Pattern match (fnmatch)"),
    extent_min: str | None = Query(None, description="Extent minimum"),
    extent_max: str | None = Query(None, description="Extent maximum"),
    limit: int = Query(100, ge=1, le=10000),
    language: str | None = Query(None, description="RFC 5646 Language-Tag."),
):
    """Search for dimension members matching a query.

    Returns an OGC Records FeatureCollection.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
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
        effective_lang = language or request.headers.get("accept-language", "").split(",")[0].split(";")[0].strip() or None
        protocol = SearchProtocol.LIKE
        query = {"like": like, "limit": limit, "language": effective_lang}
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one search parameter: exact, min/max, or like.",
        )

    if protocol not in gen.search_protocols:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (provider: {gen.provider_type}) "
            f"does not support search protocol '{protocol.value}'. "
            f"Supported: {[s.value for s in gen.search_protocols]}",
        )

    result = gen.search(protocol, ext_min, ext_max, **query)

    features = [
        _member_to_feature(m, dim_type=cfg.dimension_type)
        for m in result.members
    ]

    self_url = _self_url(request)
    resp_links = [
        {"rel": "self", "href": self_url, "type": "application/geo+json"},
    ]

    return _build_feature_collection(
        features,
        number_matched=result.number_matched,
        number_returned=result.number_returned,
        links=resp_links,
    )


@router.get("/{dimension_id}/children")
async def children(
    request: Request,
    dimension_id: str,
    parent: str = Query(..., description="Return direct children of this member code"),
    limit: int = Query(100, ge=1, le=10000, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    language: str | None = Query(None, description="RFC 5646 Language-Tag."),
    sort_by: str | None = Query(None, description="Output field to sort members by."),
    sort_dir: str = Query("asc", description="Sort direction: 'asc' or 'desc'."),
):
    """Return paginated direct children of a hierarchy node as a FeatureCollection.

    Mirrors the STAC API Children Extension applied to dimension members.
    Requires Hierarchical conformance level.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    if not gen.hierarchical:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (provider: {gen.provider_type}) "
            "does not support Hierarchical operations (/children, /ancestors).",
        )

    effective_lang = language or request.headers.get("accept-language", "").split(",")[0].split(";")[0].strip() or None
    result = gen.children(
        parent, limit=limit, offset=offset,
        sort_by=sort_by, sort_dir=sort_dir, language=effective_lang,
    )

    dim_base = _parent_url(request)

    features = [
        _member_to_feature(m, dim_type=cfg.dimension_type, gen=gen, dim_base_url=dim_base)
        for m in result.members
    ]

    self_url = _self_url(request)
    resp_links = [
        {"rel": "self", "href": f"{self_url}?parent={parent}&limit={limit}&offset={offset}", "type": "application/geo+json"},
        {"rel": "collection", "href": dim_base, "type": "application/json"},
    ]
    if offset + limit < result.number_matched:
        resp_links.append(
            {"rel": "next", "href": f"{self_url}?parent={parent}&limit={limit}&offset={offset + limit}", "type": "application/geo+json"}
        )
    if offset > 0:
        prev_offset = max(0, offset - limit)
        resp_links.append(
            {"rel": "prev", "href": f"{self_url}?parent={parent}&limit={limit}&offset={prev_offset}", "type": "application/geo+json"}
        )

    body = _build_feature_collection(
        features,
        number_matched=result.number_matched,
        number_returned=result.number_returned,
        links=resp_links,
    )

    if effective_lang:
        return JSONResponse(content=body, headers={"Content-Language": effective_lang})
    return body


@router.get("/{dimension_id}/ancestors")
async def ancestors(
    request: Request,
    dimension_id: str,
    member: str = Query(..., description="Return ancestors of this member code"),
):
    """Return the ancestor chain as a FeatureCollection, from root to member (inclusive).

    Requires Hierarchical conformance level.
    """
    cfg = _get_dimension(dimension_id)
    gen = cfg.provider
    if not gen.hierarchical:
        raise HTTPException(
            status_code=501,
            detail=f"Dimension '{dimension_id}' (provider: {gen.provider_type}) "
            "does not support Hierarchical operations (/children, /ancestors).",
        )

    chain = gen.ancestors(member)
    if not chain:
        raise HTTPException(
            status_code=404,
            detail=f"Member '{member}' not found in dimension '{dimension_id}'.",
        )

    dim_base = _parent_url(request)

    # ancestors() returns list[dict] (raw node dicts), not ProducedMember
    features = [
        _ancestor_dict_to_feature(node, dim_type=cfg.dimension_type, gen=gen, dim_base_url=dim_base)
        for node in chain
    ]

    self_url = _self_url(request)
    return _build_feature_collection(
        features,
        number_matched=len(chain),
        number_returned=len(chain),
        links=[
            {"rel": "self", "href": f"{self_url}?member={member}", "type": "application/geo+json"},
            {"rel": "collection", "href": dim_base, "type": "application/json"},
        ],
    )

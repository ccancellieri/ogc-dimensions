# OGC Dimensions

**Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes**

This repository contains the specification, scientific publication, and reference implementation for extending geospatial datacube standards (STAC Datacube Extension, OGC GeoDataCube API) with:

1. **Paginated dimension members** -- `size` + `href` for dimensions with thousands to millions of members
2. **Dimension providers** -- algorithmic member generation with machine-discoverable OpenAPI definitions
3. **Bijective inversion** -- value-to-coordinate mapping enabling dimension integrity enforcement at data ingestion
4. **Similarity-driven navigation** -- searching dimension spaces by concept proximity, bridging OGC metadata with AI/ML

## The Problem

Current standards (STAC, OGC Coverages, EDR, openEO) embed dimension members as monolithic JSON arrays. This works for small dimensions (spectral bands, ensemble members) but fails for:

- Daily time series spanning decades (9,000+ values)
- FAO agricultural indicator catalogs (10,000+ codes)
- Administrative boundary hierarchies (50,000+ members)
- Non-Gregorian calendars: **dekadal** (36/year) and **pentadal** (72 or 73/year) periods used globally in food security and drought monitoring

OGC Testbeds 17-20 ([21-027](https://docs.ogc.org/per/21-027.html), [23-047](https://docs.ogc.org/per/23-047.html), [24-035](https://docs.ogc.org/per/24-035.html)) all identified these as open gaps. The GeoDataCube SWG ([charter 22-052](https://portal.ogc.org/files/?artifact_id=104874)) was formed to address datacube interoperability but dimension member scalability remains unresolved.

## Repository Structure

```
ogc-dimensions/
├── spec/                         # Formal specification
│   ├── schema/                   # JSON Schema for extended cube:dimensions fields
│   │   ├── dimension.json        # Extended dimension schema (size, href, slim provider)
│   │   ├── provider.json         # Full provider object schema
│   │   └── hierarchy.json        # Hierarchy descriptor schema
│   ├── building-blocks/          # OGC Building Blocks (OGC API - Dimensions profile)
│   │   ├── bblocks.json          # Building block registry (5 blocks, status: under-development)
│   │   ├── dimension-collection/ # BB: Records catalogue exposing provider + cube:dimensions
│   │   ├── dimension-member/     # BB: Record representing a single dimension member
│   │   ├── dimension-pagination/ # BB: OGC Common Part 2 pagination (numberMatched + next/prev)
│   │   ├── dimension-inverse/    # BB: /inverse endpoint (value → member mapping)
│   │   └── dimension-hierarchical/ # BB: /children + /ancestors endpoints + ?parent= filter
│   └── examples/                 # Full collection JSON examples
│       ├── dekadal.json          # Dekadal temporal dimension
│       ├── pentadal.json         # Pentadal variants (monthly 72/year, annual 73/year)
│       ├── integer-range.json    # Elevation bands
│       ├── admin-hierarchy.json  # Administrative boundary hierarchy
│       ├── indicator-tree.json   # FAO indicator catalog (tree generator)
│       └── RESPONSES.md          # Annotated API response examples
├── paper/                        # Scientific publication
│   ├── manuscript.md             # Paper (Markdown source, IMRAD structure)
│   ├── figures/                  # Diagrams and schematics
│   └── references.bib            # Bibliography
├── reference-implementation/     # Reference implementation (pip: ogc-dimensions)
│   ├── src/ogc_dimensions/
│   │   ├── providers/            # Python dimension providers (member producers)
│   │   │   ├── base.py           # Abstract producer protocol (DimensionProvider)
│   │   │   ├── dekadal.py        # Dekadal provider (36/year, D1-D3 per month)
│   │   │   ├── pentadal.py       # Pentadal providers (monthly 72/year + annual 73/year)
│   │   │   ├── daily_period.py   # Generic daily-period provider
│   │   │   ├── integer_range.py  # Integer range provider (elevation, indices)
│   │   │   └── tree.py           # Tree/hierarchy provider (admin boundaries, indicator catalogs)
│   │   └── api/                  # FastAPI application
│   │       ├── app.py            # API entry point + dimension registry
│   │       └── routes.py         # All endpoints (see API Surface below)
│   └── tests/                    # pytest test suite
│       ├── test_api.py           # Integration tests (all endpoints)
│       ├── test_daily_period.py  # Daily period provider unit tests
│       ├── test_integer_range.py # Integer range provider unit tests
│       └── test_tree.py          # Tree provider unit tests
├── docs/                         # GitHub Pages documentation
├── CHANGELOG.md
├── LICENSE                       # Apache-2.0
└── README.md
```

## Quick Start

### Run the reference implementation

```bash
cd reference-implementation
pip install -e .
uvicorn ogc_dimensions.api.app:app --reload
```

Or with Docker:

```bash
docker compose up
```

Then explore:

```bash
# List all registered dimensions
curl "http://localhost:8000/dimensions"

# OGC API conformance declaration
curl "http://localhost:8000/dimensions/conformance"

# Queryable properties for a dimension
curl "http://localhost:8000/dimensions/dekadal/queryables"

# Generate dekadal members for 2024
curl "http://localhost:8000/dimensions/dekadal/items?limit=36"

# Generate pentadal-monthly members (72/year, CHIRPS/FAO)
curl "http://localhost:8000/dimensions/pentadal-monthly/items?limit=12"

# Generate pentadal-annual members (73/year, GPCP/NOAA)
curl "http://localhost:8000/dimensions/pentadal-annual/items?limit=10"

# Inverse: what dekad does January 15 belong to?
curl "http://localhost:8000/dimensions/dekadal/inverse?value=2024-01-15"

# Inverse batch (POST): multiple values at once
curl -X POST "http://localhost:8000/dimensions/dekadal/inverse" \
  -H "Content-Type: application/json" \
  -d '{"values": ["2024-01-15", "2024-03-25", "2024-12-31"]}'

# Search: all dekads matching a pattern
curl "http://localhost:8000/dimensions/dekadal/search?like=2024-K*"

# Hierarchical: children of an admin boundary node
curl "http://localhost:8000/dimensions/admin/children?parent=ITA"

# Hierarchical: ancestors of a leaf node
curl "http://localhost:8000/dimensions/admin/ancestors?member=ITA.01.001"
```

## Live Demo

A live deployment is available on the FAO Agro-Informatics Platform review environment, integrated as an extension of the [GeoID](https://github.com/un-fao/geoid) catalog platform:

**Swagger UI:** https://data.review.fao.org/geospatial/v2/api/tools/docs

### Pagination walkthrough

A dekadal dimension has 36 members per year. With `limit=5`, a client paginates through 8 pages to retrieve all members. Each response includes navigable `next`/`prev` links:

```bash
# Page 1: first 5 dekads of 2024
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/items?limit=5"
# → numberMatched: 36, numberReturned: 5
# → links: [self, next → offset=5]

# Page 2: follow the "next" link
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/items?limit=5&offset=5"
# → links: [self, next → offset=10, prev → offset=0]

# Last page: offset=35
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/items?limit=5&offset=35"
# → numberReturned: 1, links: [self, prev → offset=30]
```

### Provider capabilities

```bash
# List all registered dimensions and their capabilities
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/"

# Pentadal-monthly (72/year, CHIRPS/FAO)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/pentadal-monthly/items?limit=5"

# Pentadal-annual (73/year, GPCP/NOAA)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/pentadal-annual/items?limit=5"

# Integer range (elevation bands, step=100m)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/integer-range/items?limit=5"
```

### Bijective inversion

```bash
# What dekad does January 15 belong to?
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-15"
# → {valid: true, member: "2024-K02", range: {start: "2024-01-11", end: "2024-01-20"}}

# Invalid date → rejected with nearest valid member
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-32"
# → {valid: false, reason: "Cannot parse '2024-01-32' as a date."}
```

### Search

```bash
# Exact match by code
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?exact=2024-K15"

# Range: first 6 dekads of the year
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?min=2024-K01&max=2024-K06"

# Pattern: all dekads in 2024 starting with K1 (K10-K18 = 9 dekads)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?like=2024-K1*"
```

### STAC Collection integration

A dimension in `cube:dimensions` carries `size` (cardinality) and a slim `provider` object pointing at the dimension collection. Clients discover the paginated members endpoint by following the OGC API - Records `rel="items"` link on that collection response — no separate dimension-level items URL is required. See [`spec/examples/dekadal.json`](spec/examples/dekadal.json) for a complete example:

```json
{
  "cube:dimensions": {
    "time": {
      "type": "temporal",
      "size": 900,
      "provider": {
        "type": "daily-period",
        "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal"
      }
    }
  }
}
```

Client flow: `GET provider.href` → read `links[rel="items"]` → `GET` that URL for paginated `FeatureCollection`. Additional capabilities (`/inverse`, `/search`, `/children`, `/ancestors`) are advertised as Records `links[]` on the same collection response with their own `rel` values.

The reference implementation is deployed on the FAO Agro-Informatics Platform (Google Cloud Run) as a pip-installable FastAPI extension. The `ogc-dimensions` package is mounted alongside the production STAC catalog services with no code duplication.

## API Surface

All endpoints are mounted under a configurable prefix (default `/dimensions`).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List all registered dimensions with provider metadata |
| `/conformance` | GET | OGC API conformance classes |
| `/{id}/queryables` | GET | JSON Schema of queryable member properties |
| `/{id}/items` | GET | Paginated dimension members (OGC Records FeatureCollection) |
| `/{id}/extent` | GET | Spatial + temporal extent of the dimension |
| `/{id}/inverse` | GET | Value → member mapping (bijective inversion) |
| `/{id}/inverse` | POST | Batch value → member mapping |
| `/{id}/search` | GET | Member search: `exact=`, `min=`/`max=`, `like=` |
| `/{id}/children` | GET | Hierarchical children of a node (`?parent=`) |
| `/{id}/ancestors` | GET | Ancestor chain of a member node |

## Conformance Levels

The specification groups capabilities into five **adoption levels** for narrative clarity. Each level is realised by one or more of the five **Building Blocks** listed in [spec/building-blocks/bblocks.json](spec/building-blocks/bblocks.json); adopters consume BBs, while readers discuss levels.

| Level | Capabilities | Realised by Building Block(s) | Requirement |
|---|---|---|---|
| **Basic** | `/items` + `/extent` + `/conformance` + `/queryables` | `dimension-collection`, `dimension-member`, `dimension-pagination` | All providers MUST support |
| **Invertible** | + `/inverse` (GET + POST batch) | `dimension-inverse` | Invertible providers only |
| **Searchable** | + `/search` (exact, range, like) | `dimension-collection` (query capability) | SHOULD support |
| **Hierarchical** | + `/children` + `/ancestors` + `?parent=` filter | `dimension-hierarchical` | Required when the dimension declares a `hierarchy` property |
| *Similarity (informative)* | + `/search` (vector embedding, k-NN) | *— no Building Block ships in 1.0; future work* | MAY support |

The *Similarity* row is retained as an informative architectural hook for embedding-based dimension navigation; it has no normative schema, no conformance class URI, and no reference implementation in this release. Implementations that claim "Similarity" conformance are advertising an extension, not a standard capability.

Conformance class URIs follow the pattern `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/{building-block-id}` and are declared in each Building Block's `description.md`.

## Standardization Pathway

This proposal follows the OGC formal standardization process:

1. **Scientific publication** — peer-reviewed paper establishing the technical contribution
2. **STAC Community Extension** — JSON Schema changes to `stac-extensions/datacube`
3. **OGC GeoDataCube SWG** — Change Request Proposal for the GeoDataCube specification
4. **OGC Temporal WKT SWG + Naming Authority** — calendar algorithm definitions and URI registration
5. **OGC Innovation Program** — testbed participation for interoperability validation
6. **OGC RFC + formal vote** — candidate specification through the OGC Technical Committee

## Key References

**OGC GeoDataCube lineage:**
- [GDC SWG Charter (22-052)](https://portal.ogc.org/files/?artifact_id=104874) — Iacopino, Simonis, Meißl. Approved 2023-05-03.
- [TB-17 GDC API ER (21-027)](https://docs.ogc.org/per/21-027.html) — first GDC API draft
- [TB-19 GDC ER (23-047)](https://docs.ogc.org/per/23-047.html) — draft API submitted to SWG
- [TB-19 Draft API (23-048)](https://docs.ogc.org/per/23-048.html) — OpenAPI spec ([GitHub](https://github.com/m-mohr/geodatacube-api))
- [TB-20 GDC Profile (24-035)](https://docs.ogc.org/per/24-035.html) — profiles approach
- [TB-20 Usability Report (24-037)](https://docs.ogc.org/per/24-037.html) — 44% interop success, STAC metadata gaps

**Standards:**
- [STAC Datacube Extension](https://github.com/stac-extensions/datacube) (issue [#31](https://github.com/stac-extensions/datacube/issues/31))
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)
- [cadati](https://github.com/TUW-GEO/cadati) — dekadal date arithmetic (MIT)

## Author

**Carlo Cancellieri** -- [ccancellieri.github.io](https://ccancellieri.github.io/)

## License

Apache-2.0

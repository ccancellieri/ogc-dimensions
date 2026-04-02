# OGC Dimensions

**Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes**

This repository contains the specification, scientific publication, and reference implementation for extending geospatial datacube standards (STAC Datacube Extension, OGC GeoDataCube API) with:

1. **Paginated dimension members** -- `size` + `href` for dimensions with thousands to millions of members
2. **Dimension generators** -- algorithmic member generation with machine-discoverable OpenAPI definitions
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
├── spec/                     # Formal specification
│   ├── schema/               # JSON Schema for generator, size, href
│   │   ├── dimension.json    # Extended dimension schema
│   │   └── generator.json    # Generator object schema
│   └── examples/             # Full collection JSON examples
│       ├── dekadal.json      # Dekadal temporal dimension
│       ├── pentadal.json     # Pentadal variants
│       ├── integer-range.json # Elevation bands
│       └── legacy-bridge.json # Legacy client compatibility
├── paper/                    # Scientific publication
│   ├── manuscript.md         # Paper (Markdown source)
│   ├── figures/              # Diagrams and schematics
│   └── references.bib        # Bibliography
├── reference-implementation/  # Reference implementation (pip: ogc-dimensions)
│   └── src/ogc_dimensions/
│       ├── generators/       # Python generator algorithms
│       │   ├── base.py       # Abstract generator protocol
│       │   ├── dekadal.py    # Dekadal generator
│       │   ├── pentadal.py   # Pentadal generators (monthly + annual)
│       │   └── integer_range.py  # Integer range generator
│       ├── api/              # FastAPI application
│       │   ├── app.py        # API entry point
│       │   └── routes.py     # /members, /extent, /inverse, /search
│       └── data/             # Sample datasets
├── docs/                     # GitHub Pages documentation
├── CHANGELOG.md
├── LICENSE                   # Apache-2.0
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

# Generate dekadal members for 2024
curl "http://localhost:8000/dimensions/dekadal/members?limit=36"

# Generate pentadal-monthly members (72/year, CHIRPS/FAO)
curl "http://localhost:8000/dimensions/pentadal-monthly/members?limit=12"

# Generate pentadal-annual members (73/year, GPCP/NOAA)
curl "http://localhost:8000/dimensions/pentadal-annual/members?limit=10"

# Inverse: what dekad does January 15 belong to?
curl "http://localhost:8000/dimensions/dekadal/inverse?value=2024-01-15"

# Search: all dekads matching a pattern
curl "http://localhost:8000/dimensions/dekadal/search?like=2024-K*"
```

## Live Demo

A live deployment is available on the FAO Agro-Informatics Platform review environment, integrated as an extension of the [GeoID](https://github.com/un-fao/geoid) catalog platform:

**Swagger UI:** https://data.review.fao.org/geospatial/v2/api/tools/docs

### Pagination walkthrough

A dekadal dimension has 36 members per year. With `limit=5`, a client paginates through 8 pages to retrieve all members. Each response includes navigable `next`/`prev` links:

```bash
# Page 1: first 5 dekads of 2024
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5"
# → numberMatched: 36, numberReturned: 5
# → links: [self, next → offset=5]

# Page 2: follow the "next" link
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5&offset=5"
# → links: [self, next → offset=10, prev → offset=0]

# Last page: offset=35
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5&offset=35"
# → numberReturned: 1, links: [self, prev → offset=30]
```

### Generator capabilities

```bash
# List all registered dimensions and their capabilities
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/"

# Pentadal-monthly (72/year, CHIRPS/FAO)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/pentadal-monthly/members?limit=5"

# Pentadal-annual (73/year, GPCP/NOAA)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/pentadal-annual/members?limit=5"

# Integer range (elevation bands, step=100m)
curl "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/integer-range/members?limit=5"
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

The `href` property in a STAC collection points directly to the generator's paginated endpoint. See [`spec/examples/dekadal.json`](spec/examples/dekadal.json) for a complete collection example where:

```json
{
  "cube:dimensions": {
    "time": {
      "type": "temporal",
      "generator": { "type": "dekadal", "invertible": true },
      "size": 900,
      "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5"
    }
  }
}
```

Legacy clients follow `href` and see standard paginated JSON. Generator-aware clients read the `generator` object and use `/inverse`, `/search`, and format negotiation (`?format=datetime` vs `?format=native`).

The reference implementation is deployed on the FAO Agro-Informatics Platform (Google Cloud Run) as a pip-installable FastAPI extension. The `ogc-dimensions` package is mounted alongside the production STAC catalog services with no code duplication.

## Conformance Levels

| Level | Capabilities | Requirement |
|---|---|---|
| **Basic** | `/members` + `/extent` | All generators MUST support |
| **Invertible** | + `/inverse` | Enables ingestion validation |
| **Searchable** | + `/search` (exact, range, like) | SHOULD support |
| **Similarity** | + `/search` (vector) | MAY support (AI/ML) |
| **Intelligent** | + `/embed` (member → vector), `/project` (2D/3D projection) | Future extension |

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

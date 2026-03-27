# OGC Dimensions

**Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes**

This repository contains the specification, scientific publication, and reference implementation for extending geospatial datacube standards (STAC Datacube Extension, OGC GeoDataCube API) with:

1. **Paginated dimension members** -- `size` + `values_href` for dimensions with thousands to millions of members
2. **Dimension generators** -- algorithmic member generation with machine-discoverable OpenAPI definitions
3. **Bijective inversion** -- value-to-coordinate mapping enabling dimension integrity enforcement at data ingestion
4. **Similarity-driven navigation** -- searching dimension spaces by concept proximity, bridging OGC metadata with AI/ML

## The Problem

Current standards (STAC, OGC Coverages, EDR, openEO) embed dimension members as monolithic JSON arrays. This works for small dimensions (spectral bands, ensemble members) but fails for:

- Daily time series spanning decades (9,000+ values)
- FAO agricultural indicator catalogs (10,000+ codes)
- Administrative boundary hierarchies (50,000+ members)
- Non-Gregorian calendars: **dekadal** (36/year) and **pentadal** (72 or 73/year) periods used globally in food security and drought monitoring

OGC Testbed 19 ([doc 23-047](https://docs.ogc.org/per/23-047.html)) and Testbed 20 ([doc 24-035](https://docs.ogc.org/per/24-035.html)) both identified these as open gaps.

## Repository Structure

```
ogc-dimensions/
├── spec/                     # Formal specification
│   ├── schema/               # JSON Schema for generator, size, values_href
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
├── testbed/                  # Reference implementation
│   ├── generators/           # Python generator algorithms
│   │   ├── base.py           # Abstract generator protocol
│   │   ├── dekadal.py        # Dekadal generator
│   │   ├── pentadal.py       # Pentadal generators (monthly + annual)
│   │   └── integer_range.py  # Integer range generator
│   ├── api/                  # FastAPI application
│   │   ├── app.py            # API entry point
│   │   └── routes.py         # /generate, /extent, /inverse, /search
│   ├── data/                 # Sample datasets
│   └── Dockerfile            # One-command demo
├── docs/                     # GitHub Pages documentation
├── CHANGELOG.md
├── LICENSE                   # Apache-2.0
└── README.md
```

## Quick Start

### Run the testbed

```bash
cd testbed
pip install -e .
uvicorn api.app:app --reload
```

Or with Docker:

```bash
docker compose up
```

Then explore:

```bash
# Generate dekadal members for 2024
curl "http://localhost:8000/generators/dekadal/generate?limit=36&offset=0&year=2024"

# Inverse: what dekad does January 15 belong to?
curl "http://localhost:8000/generators/dekadal/inverse?value=2024-01-15"

# Search: all dekads in Q1 2024
curl "http://localhost:8000/generators/dekadal/search?min=2024-K01&max=2024-K09"
```

## Conformance Levels

| Level | Capabilities | Requirement |
|---|---|---|
| **Basic** | `/generate` + `/extent` | All generators MUST support |
| **Invertible** | + `/inverse` | Enables ingestion validation |
| **Searchable** | + `/search` (exact, range, like) | SHOULD support |
| **Similarity** | + `/search` (vector) | MAY support (AI/ML) |
| **Intelligent** | + `/embed`, `/project` | Future extension |

## Standardization Pathway

| Phase | Target | Timeline |
|---|---|---|
| A | Scientific publication (EarthArXiv preprint) | Months 0-2 |
| B | STAC Community Extension PR | Months 2-4 |
| C | OGC GeoDataCube SWG engagement | Months 3-6 |
| D | OGC Temporal WKT SWG + Naming Authority | Months 3-9 |
| E | OGC Testbed participation (optional) | Months 6-18 |
| F | OGC RFC + formal vote | Months 12-24 |

## Key References

- [STAC Datacube Extension](https://github.com/stac-extensions/datacube) (issue [#31](https://github.com/stac-extensions/datacube/issues/31))
- [OGC TB-19 GeoDataCubes ER (23-047)](https://docs.ogc.org/per/23-047.html)
- [OGC TB-20 GDC Profile (24-035)](https://docs.ogc.org/per/24-035.html)
- [OGC GeoDataCube SWG](https://www.ogc.org/press-release/ogc-forms-new-geodatacube-standards-working-group/) (formed Jan 2025)
- [cadati](https://github.com/TUW-GEO/cadati) -- dekadal date arithmetic (MIT)
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)

## Author

**Carlo Cancellieri** -- FAO, OGC Member

## License

Apache-2.0

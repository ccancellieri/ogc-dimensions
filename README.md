# OGC Dimensions *(Withdrawn / Evolved into EDR Sparse Tile Cubes & UAD)*

> **ARCHITECTURAL PIVOT & WITHDRAWAL NOTICE (November 2026):** The standalone paginated *OGC API – Dimensions* draft and Python `reference-implementation/` are formally **retired / withdrawn from further standalone standardization and software development**.
>
> Embracing community feedback on [`stac-extensions/datacube#36`](https://github.com/stac-extensions/datacube/issues/36) (adopting OGC API – Common Part 2 UAD `definition` URI + `variableType` and `size`) and operational validation in [**Tellurion**](https://github.com/ccancellieri/tellurion) and [**GeoID**](https://github.com/un-fao/geoid), this work now converges on **100% existing OGC standards**: **[OGC API – EDR Sparse Tile Cubes (`S_INTERSECTS` + `CoverageJSON` `Domain`) & Common Part 2 UAD](docs/EDR_SPARSE_TILE_CUBES_PROPOSAL.md)**.
>
> This evolution resolves the FAO sparse multi-file Cloud-Optimized GeoTIFF (COG) pentadal/dekadal use case — contrasting embedded `coords` in GeoZarr against multi-file sparse COGs where inline `coords` cannot exist — without inventing non-standard endpoints: nominal calendars $D$ are queried via standard UAD `GET /dimensions/{id}/items?filter=T_INTERSECTS(...)`, while populated sparse tile intersections $S(\text{AOI}, \Delta t) \subsetneq D$ (and DuckDB/Portolan SDI virtual datacube joins) are discovered via standard `GET /edr/.../collections/{cid}/items?filter=S_INTERSECTS(...)&f=CoverageJSON` (`Domain`).

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
│   │   ├── bblocks.json          # Building block registry (6 blocks, v1.0.0 stable)
│   │   ├── dimension-collection/ # BB: Records catalogue exposing provider + cube:dimensions
│   │   ├── dimension-member/     # BB: Record representing a single dimension member
│   │   ├── dimension-pagination/ # BB: OGC Common Part 2 pagination (numberMatched + next/prev)
│   │   ├── dimension-inverse/    # BB (retired/archived): historical /inverse endpoint (value → member mapping)
│   │   ├── dimension-hierarchical/ # BB: /children + /ancestors endpoints + ?parent= filter
│   │   └── dimension-similarity/ # BB: /search?similar= endpoint + RFC 7807 501 stub
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

## Live Demo & Reproducible Server (Tellurion)

> **Historical Note:** The earlier FAO Agro-Informatics Platform review sandbox (`data.review.fao.org`) referenced in the original 2026 drafts is decommissioned and kept only as historical pilot context. Reproducible UAD `/dimensions` and sparse COG/GeoZarr/GeoPackage EDR endpoints are now served via [**Tellurion**](https://github.com/ccancellieri/tellurion) and the [**Tellurion Demos Gallery**](https://ccancellieri.github.io/tellurion-demos/). See [`docs/EDR_SPARSE_TILE_CUBES_PROPOSAL.md`](docs/EDR_SPARSE_TILE_CUBES_PROPOSAL.md) for the full live walkthrough.

- **Public STAC + Records UAD & Sparse EDR Cube Demo (Render):**
  - Live interactive workbench: `https://ccancellieri.github.io/tellurion-demos/demos/stac/`
  - UAD Collection / Dimension descriptor: `https://tellurion-stac-harvest-demo.onrender.com/public/records/catalogs/default/dimensions/dekadal-2021`
  - Paginated members (`dekadal-2021`): `https://tellurion-stac-harvest-demo.onrender.com/public/records/catalogs/default/dimensions/dekadal-2021/items?limit=12`
  - Temporal resolution (`2021-01-15` → `2021-01-D2`) via standard OGC API – Features Part 3 CQL2: `https://tellurion-stac-harvest-demo.onrender.com/public/records/catalogs/default/dimensions/dekadal-2021/items?filter=T_INTERSECTS(interval,TIMESTAMP('2021-01-15T12:00:00Z'))`
  - Populated sparse pentadal granule discovery $S(\text{AOI}, \Delta t) \subsetneq D$ via standard OGC API – EDR Part 1 (`/items` + CQL2 `S_INTERSECTS` + CoverageJSON `Domain`): `https://tellurion-stac-harvest-demo.onrender.com/public/edr/catalogs/default/collections/fao_chirps_pentadal_2021_italy/items?bbox=12.2,39.2,12.5,39.5&datetime=2021-01-01T00:00:00Z/2021-01-31T23:59:59Z&f=CoverageJSON`
- **Local reproducible Tellurion demo (Port `10099`, Sparse Pentadal/Dekadal COG + GeoZarr + GeoPackage + EDR `CoverageJSON`):**

```bash
# Pentadal domain definition D (72/yr) & standard CQL2 T_INTERSECTS member lookup
curl "http://127.0.0.1:10099/public/records/catalogs/default/dimensions/pentadal-2021"
curl "http://127.0.0.1:10099/public/records/catalogs/default/dimensions/pentadal-2021/items?datetime=2021-01-12T00:00:00Z"

# Standard EDR /items with CQL2 S_INTERSECTS + f=CoverageJSON (returns populated Domain.axes.t.values)
curl "http://127.0.0.1:10099/public/edr/catalogs/default/collections/fao_chirps_pentadal_2021_italy/items?bbox=12.2,39.2,12.5,39.5&datetime=2021-01-01T00:00:00Z/2021-01-31T23:59:59Z&f=CoverageJSON"

# Sparse Pentadal COG Cube (CoverageJSON data slice with explicit temporal bounds & null gaps)
curl "http://127.0.0.1:10099/public/edr/catalogs/default/collections/fao_chirps_pentadal_2021_italy/cube?bbox=12.2,39.2,12.5,39.5&datetime=2021-01-01T00:00:00Z/2021-01-31T23:59:59Z"
```

### STAC Collection integration (UAD Minimal Form)

A dimension in `cube:dimensions` carries `size` (cardinality), `definition` (OGC API – Common Part 2 UAD link-out to `/dimensions/{id}`), and `variableType` (UAD measurement scale enum). Clients discover paginated members by following `links[rel="items"]` on the UAD definition target, resolve arbitrary timestamps via standard CQL2 `T_INTERSECTS`, and discover populated sparse granules in an AOI via standard `GET /edr/.../collections/{cid}/items?filter=S_INTERSECTS(...)&f=CoverageJSON` (`Domain`) before calling `/cube`. See [`spec/examples/dekadal.json`](spec/examples/dekadal.json) and [`spec/examples/pentadal.json`](spec/examples/pentadal.json):

```json
{
  "cube:dimensions": {
    "time": {
      "type": "temporal",
      "extent": ["2021-01-01T00:00:00Z", "2021-12-31T23:59:59Z"],
      "size": 72,
      "definition": "https://tellurion-stac-harvest-demo.onrender.com/public/records/catalogs/default/dimensions/pentadal-2021",
      "variableType": "categoricalOrdinal"
    }
  }
}
```

Historical client flow in the retired Python prototype: `GET reference-implementation` endpoints remain frozen for archival reference in [`reference-implementation/`](reference-implementation/) and [`docs/dimensions-307-email.md`](docs/dimensions-307-email.md) without further development.

## API Surface *(Retired Historical Prototype)*

All endpoints of the archived Python `reference-implementation/` below are retired in favor of standard OGC API – Common Part 2 UAD (`/dimensions/{id}/items?filter=T_INTERSECTS(...)`) and OGC API – EDR Part 1 (`/collections/{cid}/items?filter=S_INTERSECTS(...)&f=CoverageJSON`).

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

The specification groups capabilities into five **adoption levels** for narrative clarity. Each level is realised by one or more of the six **Building Blocks** listed in [spec/building-blocks/bblocks.json](spec/building-blocks/bblocks.json) (registry status: **stable, v1.0.0**); adopters consume BBs, while readers discuss levels. Conformance class URIs include the `/1.0/` segment, so an assertion made today against this registry stays meaningful across future revisions.

| Level | Capabilities | Realised by Building Block(s) | Requirement |
|---|---|---|---|
| **Basic** | `/items` + `/extent` + `/conformance` + `/queryables` | `dimension-collection`, `dimension-member`, `dimension-pagination` | All providers MUST support |
| **Invertible** | + `/inverse` (GET + POST batch) | `dimension-inverse` | Invertible providers only |
| **Searchable** | + `/search` (exact, range, like) | `dimension-collection` (query capability) | SHOULD support |
| **Hierarchical** | + `/children` + `/ancestors` + `?parent=` filter | `dimension-hierarchical` | Required when the dimension declares a `hierarchy` property |
| **Similarity** | + `/search?similar=...` (vector embedding, k-NN) | `dimension-similarity` | Optional; conformant servers without a backing index MUST return the prescribed 501 problem-detail [^similarity-stub] |

[^similarity-stub]: The reference implementation ships an honest stub: `GET /{id}/search?similar=...` returns `501 Not Implemented` with an `application/problem+json` body of `type: https://www.opengis.net/spec/ogc-dimensions/1.0/errors/similarity-not-implemented`. The conformance class URI is advertised at `/conformance` so clients can discover the capability surface even when the backing index is absent.

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

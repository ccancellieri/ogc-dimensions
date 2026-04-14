# OGC GeoDataCube SWG — Formal Change Request Submission Package

**Package version:** 1.0.0-rc.1
**Submission target:** OGC GeoDataCube Standards Working Group
**Charter:** OGC 22-052
**Date prepared:** 2026-04-14
**Submitter:** Carlo Cancellieri, Food and Agriculture Organization of the United Nations (FAO)
**Repository:** [github.com/ccancellieri/ogc-dimensions](https://github.com/ccancellieri/ogc-dimensions)

---

## 1. Purpose of this package

This document is the cover sheet for a formal Change Request to the GeoDataCube specification. It bundles the artifacts required by the OGC standardization process into a single submission and provides full traceability from each normative claim to the schema that defines it, the example that demonstrates it, and the reference implementation route that exercises it.

The package addresses the dimension-member scalability gap identified across OGC Testbeds 17–20 ([21-027](https://docs.ogc.org/per/21-027.html), [23-047](https://docs.ogc.org/per/23-047.html), [24-035](https://docs.ogc.org/per/24-035.html), [24-037](https://docs.ogc.org/per/24-037.html)) and aligns with the GDC SWG charter scope (work items: GDC metadata model definition; usability of existing standards).

## 2. Submission artifacts

| # | Artifact | Path | Status |
|---|---|---|---|
| 1 | Change Request brief (the "ask") | `docs/drafts/gdc-swg-brief.md` | Ready |
| 2 | Five OGC Building Blocks (modular adoption units) | `spec/building-blocks/` | Maturity: `candidate` |
| 3 | JSON Schemas (normative dimension + provider + hierarchy) | `spec/schema/` | Stable |
| 4 | Worked collection examples (five) | `spec/examples/` | Stable |
| 5 | Annotated API response examples | `spec/examples/RESPONSES.md` | Stable |
| 6 | Reference implementation (FastAPI, pip-installable) | `reference-implementation/` | v1.0.0-rc.1, 138 tests passing |
| 7 | Live deployment (FAO Agro-Informatics Platform) | https://data.review.fao.org/geospatial/v2/api/tools/docs | Operational |
| 8 | Scientific paper (IMRAD, peer-review-ready) | `paper/manuscript.md` | Final draft |
| 9 | Companion proposals (STAC Datacube, OGC Naming Authority) | `docs/drafts/stac-datacube-pr.md`, `docs/drafts/ogc-naming-authority.md` | Ready |

## 3. Charter alignment (22-052)

| Charter work item | Coverage in this submission |
|---|---|
| Definition of the GDC metadata model | Adds `size`, `provider`, `hierarchy` to `cube:dimensions`; introduces `nominal` / `ordinal` dimension types |
| Usability of existing standards | Profiles **OGC API – Records** (no new top-level standard); reuses Common Part 2 pagination, RFC 5988 link relations, JSON Schema 2020-12 |
| Interoperability across implementations | Five Building Blocks adoptable independently; backwards-compatible (no field removed or modified) |
| Coordination with adjacent SWGs | Coordination requested with Temporal WKT SWG (calendar algorithms) and OGC Naming Authority (provider type URI registration — see `docs/drafts/ogc-naming-authority.md`) |

## 4. Testbed traceability

| Testbed finding | Addressed by |
|---|---|
| TB-17 (21-027) — first GDC API draft, no dimension scalability story | Provider abstraction + paginated `/items` |
| TB-19 (23-047) — "pagination is rarely used in openEO implementations" for dimensions | `dimension-pagination` BB profiling OGC Common Part 2 |
| TB-19 — ECMWF requested support for "irregular or sparse data content" | Algorithmic providers + `/inverse` for ingestion-time validation |
| TB-20 (24-035) — profile-of-existing-standards approach | Submission framed as a **profile of OGC API – Records**, not a new standalone API |
| TB-20 (24-037) — 44% interop, STAC metadata inconsistency #1 pain point | Slim provider in `cube:dimensions` for STAC clients; full provider at the Records collection |

## 5. Conformance class → Building Block → schema → example → route

This is the load-bearing traceability table. Every normative claim in the brief resolves to one row here, and every row resolves to a real file/URL in the repository.

| Conformance class | Building Block | Schema | Example (committed) | Reference impl route |
|---|---|---|---|---|
| `…/conf/dimension-collection` | `ogc.api.dimensions.dimension-collection` | `spec/building-blocks/dimension-collection/schema.json` | `spec/building-blocks/dimension-collection/examples/temporal-dekadal.json` | `GET /dimensions/{id}` and `GET /dimensions/` |
| `…/conf/dimension-member` | `ogc.api.dimensions.dimension-member` | `spec/building-blocks/dimension-member/schema.json` | `spec/building-blocks/dimension-member/examples/dekadal-member.json`; `…/hierarchical-member.json` | Member features inside `GET /dimensions/{id}/items` |
| `…/conf/dimension-pagination` | `ogc.api.dimensions.dimension-pagination` | `spec/building-blocks/dimension-pagination/schema.json` | (envelope demonstrated in every `/items` response) | `GET /dimensions/{id}/items?limit=&offset=` |
| `…/conf/dimension-inverse` | `ogc.api.dimensions.dimension-inverse` | `spec/building-blocks/dimension-inverse/schema.json` | `dimension-inverse/examples/dekadal-inverse-response.json` (success); `dimension-inverse/examples/dekadal-inverse-error.json` (out-of-extent) | `GET /dimensions/{id}/inverse?value=`; `POST /dimensions/{id}/inverse` (batch) |
| `…/conf/dimension-hierarchical` | `ogc.api.dimensions.dimension-hierarchical` | `spec/building-blocks/dimension-hierarchical/schema.json` | `dimension-hierarchical/examples/admin-children.json`; `…/admin-ancestors.json` | `GET /dimensions/{id}/children?parent=`; `GET /dimensions/{id}/ancestors?member=` |

Conformance class URI pattern: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/{building-block-id}`

## 6. Building Block dependency graph

```
ogc.api.records.core
        │
        ▼
ogc.api.dimensions.dimension-collection ◀──── ogc.api.dimensions.dimension-inverse
        │
        ▼
ogc.api.dimensions.dimension-member ◀──────── ogc.api.dimensions.dimension-hierarchical
        │
        ▼
ogc.api.common.part2
        │
        ▼
ogc.api.dimensions.dimension-pagination
```

All five blocks depend on existing OGC standards only; no new top-level dependency is introduced.

## 7. STAC compatibility statement

`cube:dimensions` is extended with:
- `size` — integer cardinality (RECOMMENDED)
- `provider` — slim object `{type, href}` pointing at the dimension Records collection (OPTIONAL)
- `hierarchy` — descriptor for hierarchical dimensions (OPTIONAL)

Existing fields (`type`, `extent`, `values`, `step`, `unit`, `reference_system`) are unchanged. STAC clients that ignore unknown properties continue to work; clients that follow `provider.href` discover paginated members and capability links via the Records collection. The companion STAC Datacube extension PR is drafted at `docs/drafts/stac-datacube-pr.md` and targets `stac-extensions/datacube` issue #31.

## 8. Reference implementation status

- **Version:** `1.0.0-rc.1` (`reference-implementation/pyproject.toml`)
- **Tests:** 138 / 138 passing (`pytest tests/`)
- **Conformance classes wired:** all 5 (Basic, Invertible, Searchable, Hierarchical, Records-profile)
- **Live deployment:** mounted on the FAO Agro-Informatics Platform Cloud Run service alongside the production STAC catalog
- **Pip distribution:** `pip install -e reference-implementation`

## 9. Governance roadmap

| Milestone | Date | Outcome |
|---|---|---|
| Building Blocks formal submission | 2026-Q2 | Blocks accepted into OGC BB register at `candidate` maturity |
| Open Change Request with GDC SWG | 2026-Q2 | "Dimension Providers" added as a work item |
| STAC Datacube extension PR | 2026-Q3 | `size` / `href` / `provider` / `hierarchy` adopted upstream |
| OGC Technical Committee vote | 2026-Q4 – 2027-Q1 | Maturity advanced to `stable`; 1.0.0 final |
| Innovation Program testbed participation | Rolling | Interoperability validation with non-FAO implementers |

## 10. Requested SWG actions

1. Schedule a 30-minute slot at the next GDC SWG meeting to walk the traceability table (Section 5).
2. Add **"Dimension Providers"** to the GDC SWG work-item list as a candidate conformance class for the GDC API profile.
3. Approve the five Building Blocks for ingestion into the OGC BB register at `candidate` maturity.
4. Coordinate with the **Temporal WKT SWG** on calendar algorithm definitions for dekadal and pentadal periods.
5. Coordinate with the **OGC Naming Authority** on registration of well-known provider type URIs (see `docs/drafts/ogc-naming-authority.md`).

## 11. Out of scope (explicitly deferred to future revisions)

- *Similarity-driven navigation* (vector-embedding `/search`) — retained as an informative architectural hook in v1.0; no normative schema, no conformance class URI, no reference implementation in this release. Will be revisited once the underlying AI/ML metadata standards stabilize.
- EDR / Tiles / Styles / Coverages depth integration — out of charter for this CR; tracked separately in the FAO platform OGC compatibility roadmap.

## 12. Contact

- **Submitter:** Carlo Cancellieri — [github.com/ccancellieri](https://github.com/ccancellieri) — [ccancellieri.github.io](https://ccancellieri.github.io/)
- **Affiliation:** Food and Agriculture Organization of the United Nations
- **GDC SWG mailing list:** geodatacube.swg@lists.ogc.org

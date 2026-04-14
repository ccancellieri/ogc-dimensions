# GDC SWG Brief / Change Request Proposal Draft

**Target:** OGC GeoDataCube Standards Working Group
**Contact:** geodatacube.swg@lists.ogc.org
**Charter:** OGC doc 22-052 (Iacopino, Simonis, Meißl)

---

## Subject

Scalable Dimension Member Dissemination and Algorithmic Generation for GeoDataCube API

## Submitter

Carlo Cancellieri, Food and Agriculture Organization of the United Nations (FAO)

## Summary

This Change Request Proposal introduces seven backwards-compatible extensions to the GeoDataCube dimension metadata model that address dimension member scalability, hierarchical vocabulary navigation, and multilingual metadata -- gaps identified across OGC Testbeds 16-20 and the GDC SWG charter scope.

The proposal adds:
1. **`size`** -- dimension member count (integer, RECOMMENDED)
2. **`href`** -- link to paginated member endpoint (URI, OPTIONAL)
3. **`provider`** -- algorithmic member generation with OpenAPI discovery, `config`/`parameters` separation, and `language_support` (object, OPTIONAL)
4. **`hierarchy`** -- tree structure for hierarchical dimensions (object, OPTIONAL); two strategies: recursive (parent reference in member data) and leveled (hierarchy imposed by named level definitions)
5. **`nominal` / `ordinal`** -- two new dimension type values for coded dimensions, more precise than the existing `other` fallback
6. **Multi-language labels** -- `labels` map on members, `language_support` on providers, aligned with STAC Language Extension and OGC API - Records
7. **Sort order** -- `sort_by` / `sort_dir` standard query parameters with locale-aware collation

These properties are applicable to any dimension type (temporal, spatial, thematic) and follow existing OGC API conventions (Common Part 2 pagination, Features numberMatched/numberReturned, RFC 5988 link relations).

## Motivation

### Identified gaps

The GDC SWG charter (22-052) scopes "definition of the GDC metadata model" and "analysis of the usability of existing standards" as core work items. Current standards embed dimension members as monolithic JSON arrays with no pagination, no generation rules, and no validation mechanism.

**Testbed evidence:**
- TB-16 (20-025r1): DAPA -- "mechanism about how to determine available query parameters was not specified"
- TB-19 (23-047): "pagination is rarely used in openEO implementations" for dimension metadata
- TB-19: ECMWF requested support for "irregular or sparse data content" -- acknowledged but unresolved
- TB-20 (24-037): 44% interoperability success across 5 backends; STAC metadata inconsistency = #1 pain point

### Real-world scale

- Dekadal precipitation (FAO ASIS): 36 periods/year x 25 years = 900 members
- Daily time series: 9,131 values for 2000-2025
- Statistical indicator catalogs (FAOSTAT): 10,000+ codes
- Administrative boundaries: 50,000+ members at sub-national level

### Non-Gregorian calendars

Dekadal (36/year) and pentadal (72 or 73/year) calendars are used globally in agricultural drought monitoring and food security early warning. No standard temporal encoding (ISO 8601, CF conventions, OGC temporal models) accommodates these systems. The provider abstraction provides a standard mechanism to define, enumerate, and validate arbitrary temporal systems.

## Proposed conformance class

**"Dimension Providers"** -- a new conformance class for the GDC API profile.

### Conformance levels

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | /items + /extent | All dimensions with `provider` |
| Invertible | + /inverse | When `invertible: true` |
| Searchable | + /search (exact, range, like); `?language=` on search | SHOULD for non-trivial dims |
| Hierarchical | + /children + /ancestors; `has_children` on members | When `hierarchy` is declared |
| *Similarity (informative)* | + /search (vector) | No BB in 1.0; future work |

Standard cross-level query parameters: `language` (RFC 5646), `sort_by`, `sort_dir`.

### Provider object schema

```json
{
  "type": "daily-period",
  "config": {"period_days": 10, "scheme": "monthly"},
  "parameters": {
    "type": "object",
    "properties": {
      "sort_dir": {"type": "string", "enum": ["asc", "desc"]}
    }
  },
  "output": {"type": "object", "properties": {"code": {}, "start": {}, "end": {}}},
  "invertible": true,
  "search": ["exact", "range"],
  "on_invalid": "reject",
  "language_support": [{"code": "en"}, {"code": "fr"}, {"code": "ar", "dir": "rtl"}]
}
```

The provider separates **`config`** (static author-set constants fixed at authoring time, e.g. `period_days`, `scheme`) from **`parameters`** (query-time client parameters per JSON Schema 2020-12). The `language_support` array declares available languages using Language Objects aligned with the STAC Language Extension.

Well-known provider types resolve to registered OGC Definition URIs:

| Type | Config | Use case |
|---|---|---|
| `daily-period` | `period_days`, `scheme` | Dekadal (10-day), pentadal (5-day), any sub-monthly period |
| `integer-range` | `step` | Elevation bands, index ranges |
| `static-tree` | -- | Recursive in-memory hierarchies |
| `leveled-tree` | -- | Named-level hierarchies (admin boundaries) |

Custom providers use a full URI as the type value and provide their own OpenAPI URI via the `api` field.

## OGC Records Profile

The entire specification is framed as a profile of **OGC API - Records**: dimension collections declare `itemType: "record"`, members are served as GeoJSON Features with `geometry: null` and `dimension:*` namespaced properties, and all paginated endpoints return standard FeatureCollection envelopes. This alignment provides immediate interoperability with OGC API tooling and validators.

Worked response examples (conformance, list dimensions, paginated members, hierarchical navigation, search, inverse) are available at https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/RESPONSES.md

## OGC Building Blocks

Five building blocks are packaged for modular adoption:
- `dimension-collection` -- collection-level metadata with `itemType: "record"` and `cube:dimensions`
- `dimension-member` -- GeoJSON Feature schema with `dimension:*` properties
- `dimension-pagination` -- FeatureCollection envelope with OGC API pagination
- `dimension-inverse` -- value-to-member mapping
- `dimension-hierarchical` -- `/children`, `/ancestors` endpoints with tree navigation links

Source: https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/building-blocks

## Multi-language Support

The proposal aligns with the [STAC Language Extension](https://github.com/stac-extensions/language) and [STAC API Language Extension](https://github.com/stac-api-extensions/language) for multilingual dimension member labels:

- **Collection-level:** `language` / `languages` declarations via the STAC Language Extension (no new schema)
- **Member-level:** `labels` map (keys = RFC 5646 Language-Tags, values = translated names) alongside default `label` string
- **Provider-level:** `language_support` array declares available languages; clients use `?language=` or `Accept-Language` header
- **Sort collation:** `sort_by=label` combined with `?language=fr` applies locale-aware collation (Unicode Collation Algorithm)

This enables administrative boundary names, indicator labels, and classification codes to be served in the user's preferred language through standard HTTP content negotiation.

## Alignment with SWG approach

The TB-20 pivot from standalone GDC standard to profile/integration approach directly supports this proposal:
- The provider properties are **additive extensions** to the existing STAC `cube:dimensions` model
- The OGC Records profile ensures structural compatibility with the broader OGC API ecosystem
- No existing properties are modified or removed
- Servers can adopt incrementally (size-only, then href, then providers)
- Legacy clients are unaffected (unknown properties are ignored per JSON processing rules)

## Supporting materials

- **Scientific paper:** Cancellieri, C. (2026). "Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes." https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **JSON Schema:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/schema
- **Worked examples:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/examples
- **Reference implementation:** https://github.com/ccancellieri/ogc-dimensions/tree/main/reference-implementation
- **Live demo (FAO):** https://data.review.fao.org/geospatial/v2/api/tools/docs
- **OGC Building Blocks:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/building-blocks
- **API response examples:** https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/RESPONSES.md
- **Interactive Jupyter notebooks (GeoID platform):**
  - [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb)
  - [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb)

## Hierarchical Dimensions and Controlled Vocabulary Gap

A significant body of geospatial data is organized along hierarchical coded dimensions: GAUL administrative boundaries (Country → ADM1 → ADM2, ~50,000 total members), the FAO FAOSTAT indicator tree (Domain → Group → Indicator → Sub-indicator, ~10,000 members), and land cover classification hierarchies. SDMX 3.0 provides `HierarchicalCodelist` structures for statistical classifications, but SDMX structure endpoints return monolithic responses with no pagination. W3C SKOS `skos:broader`/`skos:narrower` encodes hierarchy semantics in RDF but is not accessible as paginated REST dimension metadata. The STAC API Children Extension defines `GET .../children` with `rel:children`/`rel:parent` link relations for Catalog/Collection trees -- the same endpoint contract applied one level lower to dimension member trees would close this gap.

The proposed `hierarchy` property with recursive and leveled strategies generalizes the operational experience of the FAO geoid system, in which hierarchy rules encode SQL conditions per level alongside `item_code_field` and `parent_code_field` column mappings. The `parameters` object per level is the backend-agnostic form of these SQL conditions, keeping implementation details inside the provider while exposing only the parameter values in the specification. The `/children` endpoint contract mirrors the STAC API Children Extension pagination envelope exactly, allowing clients already consuming collection trees via that extension to reuse the same traversal code for dimension member trees.

## Prior art

The FAO Agricultural Stress Index System (ASIS) has operated a proprietary paginated dimensions API since 2018, demonstrating the practical need in production agricultural monitoring. The FAO geoid catalog system implements production hierarchical dimensions with FIXED and RECURSIVE strategies, SQL-condition-based level filtering, and paginated children queries -- operational experience that directly informs this proposal. The present proposal standardizes this operational experience using OGC API conventions and aligns with the STAC API Children Extension endpoint contract.

## Related specifications

- [STAC Language Extension](https://github.com/stac-extensions/language) -- collection-level language declaration
- [STAC API Language Extension](https://github.com/stac-api-extensions/language) -- `?language=` query parameter, `Accept-Language`/`Content-Language` headers
- [STAC Datacube Extension Issue #36](https://github.com/stac-extensions/datacube/issues/36) -- formal proposal [DRAFT]

## Requested action

1. Review the proposal at the next GDC SWG meeting
2. Consider "Dimension Providers" as a work item / conformance class for the GDC specification
3. Coordinate with the Temporal WKT SWG for calendar algorithm definitions
4. Coordinate with the OGC Naming Authority for provider type URI registration

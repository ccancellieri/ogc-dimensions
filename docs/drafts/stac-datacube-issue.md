# GitHub Issue Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Related issue:** https://github.com/stac-extensions/datacube/issues/31 (size property request)

---

## Title

Scalable dimension members: `size`, `href`, `generator`, `hierarchy`, and `nominal`/`ordinal` types

## Body

### Problem

Current `cube:dimensions` embeds dimension members as inline `values` arrays. This works for small dimensions (spectral bands, ensemble members) but becomes impractical when dimensions scale to thousands or millions of values:

- **Temporal:** Daily time series 2000-2025 = 9,131 values. Dekadal periods across 100 years = 3,636 values.
- **Thematic:** FAO FAOSTAT indicators = 10,000+ codes. Administrative boundaries = 50,000+ members.
- **Non-Gregorian calendars:** Dekadal (36/year), pentadal (72 or 73/year) -- cannot be expressed as ISO 8601 duration, `step: null` provides no mechanism to enumerate actual members.

OGC Testbed 19 ([23-047](https://docs.ogc.org/per/23-047.html)) noted that "pagination is rarely used in openEO implementations" for dimension metadata, while acknowledging unbounded growth. Testbed 20 ([24-037](https://docs.ogc.org/per/24-037.html)) found only 44% interoperability success across 5 backends, with STAC metadata inconsistency as the #1 pain point.

The GeoDataCube SWG (charter [22-052](https://portal.ogc.org/files/?artifact_id=104874)) was formed to address datacube interoperability but dimension member scalability remains unresolved.

### Proposal

Five backwards-compatible additions to the dimension object, framed as a profile of **OGC API - Records**: dimension collections carry `itemType: "record"`, members are GeoJSON Features with `geometry: null` and `dimension:*` namespaced properties, and paginated responses use the standard FeatureCollection envelope.

#### 1. `size` (integer, RECOMMENDED)

Total member count. Allows clients to assess cardinality without downloading values.

```json
"time": {
  "type": "temporal",
  "extent": ["2000-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
  "size": 900
}
```

This directly addresses #31.

#### 2. `href` (string, URI, OPTIONAL)

Link to a paginated endpoint returning dimension values. When present, `values` MAY be omitted. Follows OGC API - Common Part 2 pagination (`limit`/`offset`, `numberMatched`/`numberReturned`, `rel:next`/`rel:prev`).

```json
"time": {
  "type": "temporal",
  "size": 900,
  "href": "https://example.org/dimensions/dekadal/members?limit=100"
}
```

#### 3. `generator` (object, OPTIONAL)

Algorithmic member generation with machine-discoverable OpenAPI definitions. Applicable to any dimension type -- temporal calendars, integer ranges, coded hierarchies.

```json
"time": {
  "type": "temporal",
  "extent": ["2000-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
  "generator": {
    "type": "dekadal",
    "output": {
      "type": "object",
      "properties": {
        "code": {"type": "string"},
        "start": {"type": "string", "format": "date"},
        "end": {"type": "string", "format": "date"}
      }
    },
    "invertible": true,
    "search": ["exact", "range", "like"]
  },
  "size": 900,
  "href": "https://example.org/dimensions/dekadal/members?limit=100"
}
```

Generators expose capabilities through standard OpenAPI interfaces:
- `/members` -- paginated member production (unified with `href`)
- `/extent` -- boundary computation
- `/inverse` (optional) -- value-to-coordinate mapping for ingestion validation
- `/search` (optional) -- query-based member discovery
- `/children` (optional) -- direct children of a hierarchical member
- `/ancestors` (optional) -- ancestor chain from root to member

#### 4. `hierarchy` (object, OPTIONAL)

Tree structure metadata for hierarchical dimensions. The `hierarchy` object is purely descriptive -- the generator type determines how hierarchy operations are implemented. Two patterns are documented:

- **Recursive generators** (e.g., `static-tree`): Each member carries a `parent_code` field (analogous to `skos:broader`). Root members have `parent_code: null`. Clients navigate via `/children?parent=X` and `/ancestors?member=X`.
- **Leveled generators** (e.g., `leveled-tree`): Hierarchy imposed by named level definitions, each with `member_id_property`, `parent_id_property`, `parent_level`, and `parameters` for level-scoped generator filtering. Adds `?level=N` to `/members`.

Adding a new hierarchy strategy means adding a new generator type -- no schema changes required.

```json
"admin": {
  "type": "nominal",
  "hierarchy": {
    "strategy": "leveled",
    "levels": [
      {"id": "L0", "label": "Country", "size": 195,
       "member_id_property": "iso_code", "parameters": {"level": 0}},
      {"id": "L1", "label": "ADM1", "size": 3469,
       "parent_level": "L0", "member_id_property": "adm1_code",
       "parent_id_property": "iso_code", "parameters": {"level": 1}}
    ]
  },
  "generator": {"type": "leveled-tree", "hierarchical": true}
}
```

#### 5. New dimension types: `nominal` and `ordinal` (proposed)

The current `type` enum (`spatial`, `temporal`, `bands`, `other`) lacks precision for coded dimensions:

- **`nominal`**: Unordered coded dimension whose members are named categories (administrative units, indicator codes, land cover classes).
- **`ordinal`**: Ordered coded dimension whose members have inherent rank (quality flags, severity levels, priority classes).

Both are standard statistical terms. Implementations that do not recognise these values treat them as unknown and continue processing -- backwards compatible.

### OGC Records Profile

Dimension endpoints produce standard **OGC API - Records** responses. Members are GeoJSON Features with `geometry: null` and `dimension:*` namespaced properties:

```json
{
  "type": "FeatureCollection",
  "numberMatched": 3636,
  "numberReturned": 3,
  "features": [
    {
      "type": "Feature",
      "id": "2024-K01",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "dimension:type": "temporal",
        "dimension:code": "2024-K01",
        "dimension:index": 0,
        "dimension:start": "2024-01-01",
        "dimension:end": "2024-01-10",
        "time": {"interval": ["2024-01-01", "2024-01-10"]}
      }
    }
  ],
  "links": [
    {"rel": "self", "href": ".../members?limit=3&offset=0", "type": "application/geo+json"},
    {"rel": "next", "href": ".../members?limit=3&offset=3", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../dekadal", "type": "application/json"}
  ]
}
```

This alignment provides three practical benefits:
1. Existing OGC API tooling (validators, client libraries, test suites) works unchanged
2. Dimension collections coexist alongside STAC and other record types in the same catalog
3. The OGC Building Blocks framework provides modular packaging for each conformance class

### Conformance Levels

Five additive conformance levels allow incremental adoption:

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | /members + /extent | MUST support |
| Invertible | + /inverse | Invertible generators only |
| Searchable | + /search (exact, range, like) | SHOULD support |
| Hierarchical | + /children + /ancestors + ?parent= filter | Required when hierarchy is declared |
| Similarity | + /search (vector) | MAY support; future work |

### OGC Building Blocks

Five building blocks are packaged for modular adoption:
- `dimension-collection` -- collection-level metadata with `itemType: "record"` and `cube:dimensions`
- `dimension-member` -- GeoJSON Feature schema with `dimension:*` properties
- `dimension-pagination` -- FeatureCollection envelope with OGC API pagination
- `dimension-inverse` -- value-to-member mapping
- `dimension-hierarchical` -- `/children`, `/ancestors` endpoints with tree navigation links

### Backwards compatibility

- `size`, `href`, `generator`, `hierarchy` are all optional additions
- `nominal` and `ordinal` are new type enum values; unknown values are already tolerated
- Existing clients ignore unknown properties
- `values` still works for small dimensions
- Legacy clients follow `href` and see standard paginated JSON (standard ISO dates when `?format=datetime`)
- Generator-aware clients get additional capabilities (inverse, search, native notation)
- Hierarchical clients navigate trees via `/children` and `/ancestors`

### Resources

- **Formal specification + JSON Schema:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec
- **OGC Building Blocks:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/building-blocks
- **Scientific paper:** https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **Reference implementation (Python/FastAPI):** https://github.com/ccancellieri/ogc-dimensions/tree/main/reference-implementation
- **Live demo (FAO review environment):** https://data.review.fao.org/geospatial/v2/api/tools/docs
- **Interactive Jupyter notebooks (GeoID platform):**
  - [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb) -- dekadal/pentadal generators, hierarchy, inverse lookup
  - [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb) -- real-world ASIS datacube with paginated dimensions
- **Worked examples:**
  - [dekadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/dekadal.json) -- temporal, 36/year
  - [pentadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/pentadal.json) -- two pentadal systems (72 + 73/year)
  - [integer-range.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/integer-range.json) -- elevation bands
  - [legacy-bridge.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/legacy-bridge.json) -- backwards compatibility
  - [admin-hierarchy.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/admin-hierarchy.json) -- leveled hierarchy (GAUL 3-level)
  - [indicator-tree.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/indicator-tree.json) -- recursive hierarchy (FAOSTAT indicators)
- **API response examples:** https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/RESPONSES.md

### OGC testbed evidence

| Testbed | Document | Finding |
|---|---|---|
| TB-16 | [20-025r1](https://docs.ogc.org/per/20-025r1.html) | DAPA: "mechanism about how to determine available query parameters was not specified" |
| TB-17 | [21-027](https://docs.ogc.org/per/21-027.html) | First GDC API draft, dimensions via STAC cube:dimensions |
| TB-19 | [23-047](https://docs.ogc.org/per/23-047.html) | "pagination is rarely used" for dimension metadata |
| TB-19 | [23-048](https://docs.ogc.org/per/23-048.html) | Draft API submitted to GDC SWG |
| TB-20 | [24-035](https://docs.ogc.org/per/24-035.html) | Profiles approach |
| TB-20 | [24-037](https://docs.ogc.org/per/24-037.html) | 44% interop success, STAC metadata inconsistency |

### Author

Carlo Cancellieri -- FAO, OGC Member

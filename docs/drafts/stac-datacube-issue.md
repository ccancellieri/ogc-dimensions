# GitHub Issue Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Related issue:** https://github.com/stac-extensions/datacube/issues/31 (size property request)

---

## Title

Scalable dimension members: `size`, `values_href`, and `generator` properties

## Body

### Problem

Current `cube:dimensions` embeds dimension members as inline `values` arrays. This works for small dimensions (spectral bands, ensemble members) but becomes impractical when dimensions scale to thousands or millions of values:

- **Temporal:** Daily time series 2000-2025 = 9,131 values. Dekadal periods across 25 years = 900 values.
- **Thematic:** FAO FAOSTAT indicators = 10,000+ codes. Administrative boundaries = 50,000+ members.
- **Non-Gregorian calendars:** Dekadal (36/year), pentadal (72 or 73/year) -- cannot be expressed as ISO 8601 duration, `step: null` provides no mechanism to enumerate actual members.

OGC Testbed 19 ([23-047](https://docs.ogc.org/per/23-047.html)) noted that "pagination is rarely used in openEO implementations" for dimension metadata, while acknowledging unbounded growth. Testbed 20 ([24-037](https://docs.ogc.org/per/24-037.html)) found only 44% interoperability success across 5 backends, with STAC metadata inconsistency as the #1 pain point.

The GeoDataCube SWG (charter [22-052](https://portal.ogc.org/files/?artifact_id=104874)) was formed to address datacube interoperability but dimension member scalability remains unresolved.

### Proposal

Three backwards-compatible additions to the dimension object:

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

#### 2. `values_href` (string, URI, OPTIONAL)

Link to a paginated endpoint returning dimension values. When present, `values` MAY be omitted. Follows OGC API - Common Part 2 pagination (`limit`/`offset`, `numberMatched`/`numberReturned`, `rel:next`/`rel:prev`).

```json
"time": {
  "type": "temporal",
  "size": 900,
  "values_href": "https://example.org/dimensions/dekadal/generate?limit=100"
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
    "bijective": true,
    "search": ["exact", "range", "like"]
  },
  "size": 900,
  "values_href": "https://example.org/dimensions/dekadal/generate?limit=100"
}
```

Generators expose capabilities through standard OpenAPI interfaces:
- `/generate` -- paginated member production (unified with `values_href`)
- `/extent` -- boundary computation
- `/inverse` (optional) -- value-to-coordinate mapping for ingestion validation
- `/search` (optional) -- query-based member discovery

### Backwards compatibility

- `size`, `values_href`, `generator` are all optional additions
- Existing clients ignore unknown properties
- `values` still works for small dimensions
- Legacy clients follow `values_href` and see standard paginated JSON (standard ISO dates when `?format=datetime`)
- Generator-aware clients get additional capabilities (inverse, search, native notation)

### Resources

- **Formal specification + JSON Schema:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec
- **Scientific paper:** https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **Reference implementation (Python/FastAPI):** https://github.com/ccancellieri/ogc-dimensions/tree/main/reference-implementation
- **Live demo (FAO review environment):** https://data.review.fao.org/geospatial/v2/api/tools/docs
- **Worked examples:**
  - [dekadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/dekadal.json) -- temporal, 36/year
  - [pentadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/pentadal.json) -- two pentadal systems (72 + 73/year)
  - [integer-range.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/integer-range.json) -- elevation bands
  - [legacy-bridge.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/legacy-bridge.json) -- backwards compatibility

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

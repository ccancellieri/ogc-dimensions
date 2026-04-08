# GitHub Issue Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Live issue:** https://github.com/stac-extensions/datacube/issues/36 [DRAFT]
**Related issue:** https://github.com/stac-extensions/datacube/issues/31 (size property request)

---

## Title

[DRAFT] Scalable dimension members: size, href, generator, hierarchy, and nominal/ordinal types

## Body

### Problem

Current `cube:dimensions` embeds dimension members as inline `values` arrays. This works for small dimensions (spectral bands, ensemble members) but fails at scale:

- **Temporal:** Daily time series 2000-2025 = 9,131 values. Dekadal periods across 25 years = 900 values.
- **Thematic:** FAO FAOSTAT indicators = 10,000+ codes. Administrative boundaries = 50,000+ members.
- **Non-Gregorian calendars:** Dekadal (36/year), pentadal (72 or 73/year) -- cannot be expressed as ISO 8601 duration; `step: null` provides no mechanism to enumerate actual members.
- **Multi-lingual catalogs:** Administrative unit names, indicator labels, and classification descriptions are needed in multiple languages. No current mechanism exists for multilingual member labels.

OGC Testbed 19 ([23-047](https://docs.ogc.org/per/23-047.html)) noted "pagination is rarely used in openEO implementations" for dimension metadata while acknowledging unbounded growth. Testbed 20 ([24-037](https://docs.ogc.org/per/24-037.html)) found only 44% interoperability success across 5 backends, with STAC metadata inconsistency as the #1 pain point.

### Proposal

Seven backwards-compatible additions to the dimension object:

#### 1. `size` (integer, RECOMMENDED)

Total member count. Resolves #31.

```json
{
  "time": {
    "type": "temporal",
    "extent": ["2000-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
    "size": 900
  }
}
```

#### 2. `href` (URI, OPTIONAL)

Link to a paginated endpoint returning dimension members. When present, `values` MAY be omitted. Follows OGC API - Common Part 2 pagination (`limit`/`offset`, `numberMatched`/`numberReturned`, `rel:next`/`rel:prev`).

#### 3. `generator` (object, OPTIONAL)

Machine-discoverable OpenAPI definition describing how to enumerate this dimension's members. Applicable to any dimension type -- temporal calendars, integer ranges, static codelists, administrative hierarchies.

```json
{
  "time": {
    "type": "temporal",
    "generator": {
      "type": "daily-period",
      "config": {
        "period_days": 10,
        "scheme": "monthly"
      },
      "parameters": {
        "type": "object",
        "properties": {
          "sort_dir": {
            "type": "string",
            "enum": ["asc", "desc"],
            "default": "asc",
            "description": "Sort direction. 'asc' = oldest first (default), 'desc' = newest first."
          }
        }
      },
      "output": {
        "type": "object",
        "required": ["code", "start", "end"],
        "properties": {
          "code":  {"type": "string", "description": "YYYY-Knn (nn=01..36). 'K' prefix denotes dekadal."},
          "start": {"type": "string", "format": "date", "description": "First day of the period (inclusive)."},
          "end":   {"type": "string", "format": "date", "description": "Last day of the period (inclusive). D3 absorbs remaining days."}
        }
      },
      "invertible": true,
      "search": ["exact", "range"],
      "on_invalid": "reject"
    },
    "step": null,
    "unit": "dekad",
    "size": 900,
    "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5"
  }
}
```

**`config` vs `parameters`:** The generator object separates two concerns:
- **`config`** -- static constants fixed at collection-authoring time, not overridable by clients per-request. They configure the generator algorithm itself (e.g., `period_days`, `scheme` for temporal periods; `step` for integer ranges). Well-known generators with no author-configurable constants SHOULD omit this field or set it to `{}`.
- **`parameters`** -- a JSON Schema 2020-12 document describing query-time parameters that clients may pass per request to `/members`, `/children`, and `/search`. These are NOT static configuration values.

**Well-known generator types:**

| Type | Config | Use case |
|---|---|---|
| `daily-period` | `period_days`, `scheme` | Dekadal (10-day), pentadal (5-day), any fixed sub-monthly period |
| `integer-range` | `step` | Elevation bands, index ranges |
| `static-tree` | -- | Recursive in-memory hierarchies |
| `leveled-tree` | -- | Named-level hierarchies (admin boundaries) |

Custom generators use a full URI as the `type` value and MUST provide an `api` field pointing to their OpenAPI definition.

The `generator` object's OpenAPI definition exposes up to four standard endpoints:
- `/members` -- paginated member listing (unified with `href`)
- `/extent` -- boundary computation
- `/inverse` (optional) -- value-to-coordinate mapping for ingestion validation
- `/search` (optional) -- query-based member discovery

> **On the endpoint name `/members`:** An earlier draft used `/generate`, which makes intuitive sense for algorithmic dimensions (dekadal, integer-range) but is semantically wrong for static codelists (FAOSTAT indicators, GAUL administrative boundaries) where nothing is generated at runtime. `/members` names what the endpoint *returns* rather than *how* it is produced, making it neutral across both cases. It also aligns with OGC API - Common's established use of "members" for paginated resource collections, and sits consistently alongside `/children` and `/ancestors` for hierarchical dimensions -- all endpoint names are resource-oriented plural nouns.

#### 4. `hierarchy` (object, OPTIONAL)

Tree structure metadata for hierarchical coded dimensions. The `generator.type` determines behaviour; `hierarchy` is descriptive metadata for clients. Two patterns:

- **Recursive** (`static-tree`): each member carries a `parent_code` field (analogous to `skos:broader`). Navigate via `/children?parent=X` and `/ancestors?member=X`.
- **Leveled** (`leveled-tree`): hierarchy imposed by named level definitions with `member_id_property`, `parent_id_property`, and `parameters` per level. Adds `?level=N` to `/members`.

Each level MAY declare a `labels` map (see section 6) for multilingual level names alongside the default `label` string.

Each member response includes `has_children: bool` -- a lightweight flag indicating whether the member has children, allowing tree-rendering clients to show expand controls without an additional `/children` round-trip.

```json
{
  "admin": {
    "type": "nominal",
    "hierarchy": {
      "strategy": "leveled",
      "levels": [
        {"id": "L0", "label": "Country", "labels": {"en": "Country", "fr": "Pays", "ar": "دولة"}, "size": 195,   "member_id_property": "iso_code",  "parameters": {"level": 0}, "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/world-admin/members?level=0&limit=5"},
        {"id": "L1", "label": "ADM1",    "labels": {"en": "ADM1",    "fr": "Région / État"},      "size": 3469,  "parent_level": "L0", "member_id_property": "adm1_code", "parent_id_property": "iso_code",  "parameters": {"level": 1}, "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/world-admin/members?level=1&limit=5"},
        {"id": "L2", "label": "ADM2",    "labels": {"en": "ADM2",    "fr": "District"},            "size": 46031, "parent_level": "L1", "member_id_property": "adm2_code", "parent_id_property": "adm1_code", "parameters": {"level": 2}, "href": "https://data.review.fao.org/geospatial/v2/api/tools/dimensions/world-admin/members?level=2&limit=5"}
      ]
    },
    "generator": {"type": "leveled-tree", "hierarchical": true, "navigable": true}
  }
}
```

The `/children` endpoint mirrors the [STAC API Children Extension](https://api.stacspec.org/v1.0.0-rc.2/children) pagination contract applied to dimension members rather than collections.

#### 5. `nominal` and `ordinal` dimension types

The current type enum (`spatial`, `temporal`, `bands`, `other`) lacks precision for coded dimensions:

- **`nominal`**: unordered coded dimension (administrative units, indicator codes, land cover classes)
- **`ordinal`**: ordered coded dimension with inherent rank (quality flags, severity levels)

Both are standard statistical terms. Unknown type values are already tolerated by existing implementations -- backwards compatible.

#### 6. Multi-language member labels (aligned with STAC Language Extension)

Administrative unit names, indicator labels, and classification codes are needed in multiple languages. This proposal aligns with the [STAC Language Extension](https://stac-extensions.github.io/language/v1.0.0/schema.json) and [STAC API Language Extension](https://api.stacspec.org/v1.0.0-rc.2/language), which themselves align with OGC API - Records and RFC 5646.

**Three additions:**

**a) `language` / `languages` on the Collection** -- declared via the STAC Language Extension (no new schema needed); declares the document language and available languages using Language Objects (RFC 5646 `code`, `name`, `alternate`, `dir: ltr|rtl`).

```json
{
  "language":  {"code": "en", "name": "English"},
  "languages": [
    {"code": "fr", "name": "Français",  "alternate": "French"},
    {"code": "ar", "name": "العربية",   "alternate": "Arabic", "dir": "rtl"},
    {"code": "es", "name": "Español",   "alternate": "Spanish"},
    {"code": "zh", "name": "中文",       "alternate": "Chinese"}
  ]
}
```

**b) `labels` on member output** -- each generated member MAY include a `labels` map alongside the default `label` string. Keys are RFC 5646 Language-Tags; values are the member name in that language. Clients SHOULD prefer `labels[negotiated_lang]` over `label`.

```json
{"code": "FRA", "label": "France", "labels": {"en": "France", "fr": "France", "ar": "فرنسا", "es": "Francia", "zh": "法国"}}
```

**c) `language_support` on `generator`** -- declares the languages the generator can serve, using the same Language Object structure as the STAC Language Extension. When present, clients MAY use the `language` query parameter (RFC 5646; mirrors the STAC API Language Extension `?language=` parameter) or the `Accept-Language` HTTP header; query parameter takes precedence.

```json
{
  "generator": {
    "type": "leveled-tree",
    "language_support": [
      {"code": "en", "name": "English"},
      {"code": "fr", "name": "Français",  "alternate": "French"},
      {"code": "ar", "name": "العربية",   "alternate": "Arabic", "dir": "rtl"}
    ]
  }
}
```

When `?language=fr` is requested, the server SHOULD return `label` in French and SHOULD use locale-aware collation (Unicode Collation Algorithm) when `sort_by=label` is also present. The server MUST return a `Content-Language` response header indicating the served language (per STAC API Language Extension).

#### 7. Sort order

Members are currently returned in generator-defined order. Two new standard query parameters on `/members`, `/children`, and `/search`:

- **`sort_by`** -- output field name to sort by (`code`, `label`, `rank`, or any declared output field)
- **`sort_dir`** -- `asc` (default) or `desc`

For `ordinal` dimensions, members SHOULD include a `rank` integer field (0-based) encoding their explicit sort position. This makes the ordinal ordering machine-readable rather than relying on response order.

When `sort_by=label` is combined with `?language=fr`, the sort uses locale-aware collation for the requested language -- diacritics in French, RTL ordering for Arabic, radical-stroke for Chinese. This composes cleanly with the `language` parameter defined in section 6.

These parameters SHOULD be declared in the generator's `parameters` schema so clients can discover sort capabilities without trial-and-error.

### Conformance levels

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | `/members` + `/extent` | All dimensions with `generator` |
| Invertible | + `/inverse` | When `invertible: true` |
| Searchable | + `/search` (exact, range, like); `?language=` on search | SHOULD for non-trivial dims |
| Hierarchical | + `/children` + `/ancestors`; `has_children` on members | When `hierarchy` is declared |
| Similarity | + `/search` (vector) | MAY (future) |

Standard cross-level query parameters (SHOULD be supported when the relevant capability is present): `language` (RFC 5646, overrides `Accept-Language`), `sort_by`, `sort_dir`.

### Backwards compatibility

All additions are optional. Existing collections remain valid. Clients that don't recognise new properties ignore them. Legacy clients following `href` see standard paginated JSON (ISO dates with `?format=datetime`). Clients that recognise `generator` gain access to inverse, search, and native notation capabilities. Clients that recognise `labels` gain multilingual display; those that don't fall back to the `label` string.

### Worked examples

All examples validate against the extended schema and are backed by the live reference implementation:

| Example | Dimension type | Demonstrates |
|---|---|---|
| [dekadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/dekadal.json) | `temporal` | `size`, `href`, `generator` with invertible dekadal calendar (`daily-period` + `config`) |
| [pentadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/pentadal.json) | `temporal` | Two competing pentadal systems (72/yr vs 73/yr) |
| [integer-range.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/integer-range.json) | `other` | Non-temporal integer-range dimension (elevation bands) |
| [legacy-bridge.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/legacy-bridge.json) | `temporal` | ISO date output for legacy client compatibility |
| [admin-hierarchy.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/admin-hierarchy.json) | **`nominal`** | `hierarchy` leveled (Country -> ADM1 -> ADM2) with multilingual `labels`, `language_support`, `sort_by`/`sort_dir` |
| [indicator-tree.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/indicator-tree.json) | **`nominal`** | `hierarchy` recursive (FAOSTAT indicator tree) |

### Live reference implementation

Deployed on the FAO Agro-Informatics Platform review environment:

- **Dimension listing:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/
- **Swagger UI:** https://data.review.fao.org/geospatial/v2/api/tools/docs
- **Members (dekadal):** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5
- **Inverse example:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-15
- **Search example:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?like=2024-K*
- **Multilingual + sort (admin):** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/admin-boundaries/members?level=1&language=fr&sort_by=label

### Full specification

- **Repo + JSON Schema:** https://github.com/ccancellieri/ogc-dimensions
- **Scientific paper:** https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **OGC Building Blocks:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/building-blocks
- **API response examples:** https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/RESPONSES.md
- **Interactive Jupyter notebooks (GeoID platform):**
  - [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb)
  - [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb)

### OGC testbed evidence

| Testbed | Doc | Finding |
|---|---|---|
| TB-16 | [20-025r1](https://docs.ogc.org/per/20-025r1.html) | DAPA: "mechanism about how to determine available query parameters was not specified" |
| TB-19 | [23-047](https://docs.ogc.org/per/23-047.html) | "pagination is rarely used" for dimension metadata |
| TB-20 | [24-037](https://docs.ogc.org/per/24-037.html) | 44% interop success; STAC metadata inconsistency = #1 pain point |

### Related specifications

- [STAC Language Extension](https://github.com/stac-extensions/language) -- Collection-level language declaration (`language`, `languages`); `hreflang` on links
- [STAC API Language Extension](https://github.com/stac-api-extensions/language) -- `?language=` query param; `Accept-Language`/`Content-Language` headers; aligns with OGC API - Features i18n and RFC 8288

---

*Carlo Cancellieri -- FAO*

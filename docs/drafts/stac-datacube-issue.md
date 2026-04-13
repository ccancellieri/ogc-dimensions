# GitHub Issue Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Live issue:** https://github.com/stac-extensions/datacube/issues/36
**Related issue:** https://github.com/stac-extensions/datacube/issues/31 (size property request)

---

## Title

[PROPOSAL] OGC API – Dimensions: scalable, multilingual dimension members as an OGC API – Records profile

---

## Body

Hi everyone 👋

I'd like to share a proposal developed at [FAO](https://data.review.fao.org) through several years of operational experience with large, irregular, and multilingual datacube dimensions. The core observation is simple: the current `values` array doesn't scale, and no existing standard fills the gap. I'm posting this here because `cube:dimensions` is the natural extension point, and I'd love feedback before moving this toward a formal OGC Change Request.

Happy to split into separate issues or PRs if the community prefers a more incremental approach.

---

## Background and Motivation

### The scalability problem

`cube:dimensions` embeds members as inline `values` arrays. This works well for small dimensions (spectral bands, model ensemble members) but breaks down at operational scale:

| Dimension | Member count | Problem |
|---|---|---|
| Daily time series 2000–2025 | 9,131 | Response too large; no pagination |
| FAO FAOSTAT indicators | 10,000+ | No standard mechanism to browse or search |
| GAUL administrative boundaries | 50,000+ | Cannot fit in a collection document |
| Dekadal periods (36/year, 100yr extent) | 3,600 | Cannot use `step` — not ISO 8601 expressible |
| Pentadal periods (72–73/year) | 7,200–7,300 | Two incompatible systems; clients can't distinguish |

The non-Gregorian calendar problem deserves special attention: **dekadal** (10-day, 36/year) and **pentadal** (5-day, 72 or 73/year) periods are in operational use by FAO ASIS, FEWS NET, CHIRPS, GPCP, and others. They cannot be expressed as ISO 8601 durations; `step: null` provides no mechanism to enumerate actual members. Combining datasets across producers requires knowing which calendar encoding was used — a gap that currently has no standard solution.

### Multilingual catalogs

Administrative unit names, indicator labels, and classification codes are needed in Arabic, French, Spanish, Chinese, and dozens of other languages. The STAC ecosystem has the [Language Extension](https://github.com/stac-extensions/language) and [API Language Extension](https://github.com/stac-api-extensions/language) for collection-level declarations, but no mechanism exists for multilingual dimension member labels.

### Evidence from OGC Testbeds

| Testbed | Document | Relevant finding |
|---|---|---|
| TB-16 | [20-025r1](https://docs.ogc.org/per/20-025r1.html) | DAPA: "mechanism about how to determine available query parameters was not specified" |
| TB-19 | [23-047](https://docs.ogc.org/per/23-047.html) | "pagination is rarely used in openEO implementations" for dimension metadata |
| TB-20 | [24-037](https://docs.ogc.org/per/24-037.html) | 44% interop success across 5 backends; STAC metadata inconsistency was the #1 pain point |

### Standards gap

I surveyed nine existing OGC/W3C standards for paginated dimension member support:

| Standard | Paginates members? | Non-Gregorian? | Multilingual? |
|---|---|---|---|
| OGC API – Features | ✗ | ✗ | ✗ |
| OGC API – Records | ✓ (via /items) | ✓ | ✓ |
| OGC API – Coverages | ✗ | ✗ | ✗ |
| OGC API – EDR | ✗ | ✗ | ✗ |
| STAC Datacube Extension | ✗ | ✗ | ✗ |
| openEO | ✗ | ✗ | ✗ |
| OGC WCS 2.x | ✗ | ✗ | ✗ |
| ISO 19123 (Coverage) | ✗ | ✗ | ✗ |
| SKOS / SKOS-XL | ✓ (via RDF) | ✗ | ✓ |

**OGC API – Records is the only standard that natively supports all three.** This proposal profiles Records for dimension member dissemination.

---

## Proposed Solution: OGC API – Records Profile

The key insight is that dimension collections and their members map cleanly onto the OGC API – Records model:

| Records concept | Dimension concept |
|---|---|
| Catalogue (`itemType: "record"`) | Dimension collection descriptor |
| `GET /collections/{id}` | Dimension metadata (with provider details) |
| `GET /collections/{id}/items` | Paginated dimension members |
| Record (GeoJSON Feature, `geometry: null`) | Single dimension member |
| OGC Common Part 2 pagination | `limit` / `offset` / `next` / `prev` |
| `language` / `languages` | Available member label languages |

Members are GeoJSON Features with `geometry: null` — first-class in OGC Records — and `dimension:*` namespaced properties. The `/items` endpoint is the OGC Records-mandated path (inherited from OGC API – Features Core) and requires no new endpoint name.

This proposal defines five OGC Building Blocks on top of this profile:

| Building Block | Depends on | Adds |
|---|---|---|
| `dimension-collection` | `ogc.api.records.core` | `cube:dimensions` with `size`, `href`, slim `provider` |
| `dimension-member` | `ogc.api.records.record-core` | `dimension:*` properties, `labels`, link relations |
| `dimension-pagination` | `ogc.api.common.part2` | `numberMatched` semantics for generated sequences |
| `dimension-inverse` | `dimension-collection` | `/inverse` endpoint — value → member mapping |
| `dimension-hierarchical` | `dimension-member` | `/children`, `/ancestors`, `?parent=` filter |

---

## Proposed `cube:dimensions` Additions

All additions are **optional and backwards-compatible**. Existing collections remain valid; clients that don't recognise new properties ignore them.

### 1. `size` (integer, RECOMMENDED)

Total member count. Resolves [#31](https://github.com/stac-extensions/datacube/issues/31).

```json
{
  "time": {
    "type": "temporal",
    "extent": ["2000-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
    "size": 900
  }
}
```

### 2. `href` (URI, OPTIONAL)

Link to the paginated `/items` endpoint returning dimension members in OGC Records format. When present, `values` MAY be omitted. Pagination follows OGC API – Common Part 2 (`limit`/`offset`, `numberMatched`/`numberReturned`, `rel:next`/`rel:prev`).

### 3. `provider` (object, OPTIONAL)

A slim reference identifying the dimension's backing provider and linking to its full definition at the OGC API – Dimensions collection endpoint. This keeps the STAC `cube:dimensions` compact while allowing provider-aware clients to discover all capabilities by following `provider.href`.

```json
{
  "time": {
    "type": "temporal",
    "step": null,
    "unit": "dekad",
    "size": 900,
    "href": "https://example.org/dimensions/temporal-dekadal/items",
    "provider": {
      "type": "daily-period",
      "href": "https://example.org/dimensions/temporal-dekadal"
    }
  }
}
```

The full provider definition — config, parameters, output schema, invertibility, search capabilities, conformance URIs, language support — is served at the collection endpoint referenced by `provider.href`:

```json
{
  "id": "temporal-dekadal",
  "title": "Dekadal Temporal Dimension",
  "itemType": "record",
  "provider": {
    "type": "daily-period",
    "config": {"period_days": 10, "scheme": "monthly"},
    "invertible": true,
    "search": ["exact", "range", "like"],
    "on_invalid": "reject",
    "language_support": [
      {"code": "en", "name": "English"},
      {"code": "fr", "name": "Français", "alternate": "French"},
      {"code": "ar", "name": "العربية",  "alternate": "Arabic", "dir": "rtl"}
    ]
  },
  "conformsTo": [
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-inverse"
  ]
}
```

**Provider `config` vs query `parameters`:** The provider separates two concerns:
- **`config`** — static constants fixed at collection-authoring time; configure the algorithm itself (e.g., `period_days`, `scheme`). Not overridable by clients per-request.
- **`parameters`** — a JSON Schema 2020-12 document declaring query-time inputs clients may pass to `/items`, `/children`, and `/search` (e.g., `language`, `sort_by`, `sort_dir`).

**Well-known provider types:**

| Type | Config | Use case |
|---|---|---|
| `daily-period` | `period_days`, `scheme` | Dekadal (10-day), pentadal (5-day), any fixed sub-monthly calendar |
| `integer-range` | `step` | Elevation bands, index ranges, percentile bins |
| `static-tree` | — | Recursive in-memory hierarchies (indicator catalogs) |
| `leveled-tree` | — | Named-level hierarchies (administrative boundaries) |

Custom providers use a full URI as the `type` value and MUST provide an `api` field pointing to their OpenAPI definition.

### 4. `hierarchy` (object, OPTIONAL)

Tree structure metadata for hierarchical coded dimensions. The `provider.type` determines navigation behaviour; `hierarchy` is descriptive metadata for clients (and thus stable across provider changes).

Two strategies are supported:

- **Recursive** (`static-tree`): each member carries a `parent_code` field (analogous to `skos:broader`). Navigate via `/children?parent=X` and `/ancestors?member=X`.
- **Leveled** (`leveled-tree`): hierarchy imposed by named level definitions, each with `member_id_property`, `parent_id_property`, and a `parameters` object encoding the level filter. The `?level=N` parameter on `/items` selects members at a specific level.

The `/children` endpoint follows the pagination contract of the [STAC API Children Extension](https://api.stacspec.org/v1.0.0-rc.2/children), applied to dimension members rather than catalogue nodes. The `?parent=` filter on `/items` aligns with [OGC API – Common issue #298](https://github.com/opengeospatial/ogcapi-common/issues/298). The `/ancestors` endpoint (full chain from root to a given member, inclusive) is a novel contribution with no direct equivalent in existing standards.

Each hierarchy level MAY declare a `labels` map for multilingual level names alongside the default `label` string. Each member response includes a `dimension:has_children` boolean, allowing tree-rendering clients to show expand controls without an additional `/children` round-trip.

```json
{
  "admin": {
    "type": "nominal",
    "hierarchy": {
      "strategy": "leveled",
      "levels": [
        {
          "id": "L0", "label": "Country",
          "labels": {"en": "Country", "fr": "Pays", "ar": "دولة", "es": "País"},
          "size": 195, "member_id_property": "iso_code",
          "parameters": {"level": 0},
          "href": "https://example.org/dimensions/world-admin/items?level=0&limit=5"
        },
        {
          "id": "L1", "label": "ADM1",
          "labels": {"en": "ADM1", "fr": "Région / État", "ar": "المستوى 1"},
          "size": 3469, "parent_level": "L0",
          "member_id_property": "adm1_code", "parent_id_property": "iso_code",
          "parameters": {"level": 1},
          "href": "https://example.org/dimensions/world-admin/items?level=1&limit=5"
        },
        {
          "id": "L2", "label": "ADM2",
          "labels": {"en": "ADM2", "fr": "District / Département"},
          "size": 46031, "parent_level": "L1",
          "member_id_property": "adm2_code", "parent_id_property": "adm1_code",
          "parameters": {"level": 2},
          "href": "https://example.org/dimensions/world-admin/items?level=2&limit=5"
        }
      ]
    },
    "provider": {"type": "leveled-tree", "href": "https://example.org/dimensions/world-admin"}
  }
}
```

### 5. `nominal` and `ordinal` dimension types

The current type enum (`spatial`, `temporal`, `bands`, `other`) lacks precision for coded dimensions:

- **`nominal`** — unordered coded dimension (administrative units, indicator codes, land cover classes, species taxonomies)
- **`ordinal`** — ordered coded dimension with inherent rank (quality flags, severity levels, alert categories)

Both are standard measurement-scale terms (Stevens, 1946). Unknown type values are already tolerated by existing implementations — fully backwards compatible.

For `ordinal` dimensions, members SHOULD include a `rank` integer field (0-based) encoding explicit sort position, making the ordering machine-readable rather than response-order-dependent.

---

## Multi-Language Member Labels

Aligned with the [STAC Language Extension](https://github.com/stac-extensions/language) and [STAC API Language Extension](https://github.com/stac-api-extensions/language), which themselves align with OGC API – Records and RFC 5646.

**Three additions work together:**

**a) Collection-level language declaration** — via the existing STAC Language Extension (no new schema needed):

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

**b) `labels` on member output** — each member MAY include a `labels` map alongside the default `label` string. Clients SHOULD prefer `labels[negotiated_lang]` over `label`:

```json
{"code": "FRA", "label": "France", "labels": {"en": "France", "fr": "France", "ar": "فرنسا", "es": "Francia", "zh": "法国"}}
```

**c) `language_support` on the provider** — declares the languages the provider can serve, using the same Language Object structure as the STAC Language Extension. Clients MAY request a language via the `language` query parameter (RFC 5646) or `Accept-Language` header; query parameter takes precedence. The server MUST return a `Content-Language` response header (per STAC API Language Extension).

When `?language=fr` is combined with `sort_by=label`, sorting uses locale-aware collation (Unicode Collation Algorithm) for the requested language — diacritics for French, RTL ordering for Arabic, radical-stroke for Chinese.

---

## Sort Order

Two new standard query parameters on `/items`, `/children`, and `/search`:

- **`sort_by`** — output field name to sort by (`code`, `label`, `rank`, or any declared output field)
- **`sort_dir`** — `asc` (default) or `desc`

These SHOULD be declared in the provider's `parameters` schema so clients can discover sort capabilities without trial and error.

---

## Extension Endpoints (on Records Collections)

All endpoints extend the standard OGC Records collection at `GET /collections/{dim_id}`:

| Endpoint | Conformance level | Description |
|---|---|---|
| `GET /collections/{dim}/items` | Basic | Paginated members (OGC Records `/items`) |
| `GET /collections/{dim}/items/{id}` | Basic | Single member |
| `GET /collections/{dim}/queryables` | Basic | JSON Schema of queryable / sortable member fields |
| `GET /collections/{dim}/inverse` | Invertible | Value → member mapping (single) |
| `POST /collections/{dim}/inverse` | Invertible | Batch value → member mapping |
| `GET /collections/{dim}/children` | Hierarchical | Direct children of a node (`?parent=`) |
| `GET /collections/{dim}/ancestors` | Hierarchical | Ancestor chain from root to member |
| `GET /collections/{dim}/search` | Searchable | Member search: `exact=`, `min=`/`max=`, `like=` |

---

## Conformance Levels

Designed for incremental adoption — each level is independent and additive:

| Level | Capabilities | Who needs it |
|---|---|---|
| **Basic** | `/items` + `/queryables` + pagination | All dimensions with a `provider` |
| **Invertible** | + `/inverse` (GET + POST batch) | Dimensions used for ingestion-time validation |
| **Searchable** | + `/search` (exact, range, like) + `?language=`, `sort_by`, `sort_dir` | Non-trivial catalogues |
| **Hierarchical** | + `/children` + `/ancestors` + `?parent=` on `/items` | Tree-structured dimensions (admin, taxonomy) |
| *Similarity (informative)* | + `/search` (vector embedding, k-NN) | AI/ML navigation; no Building Block in 1.0, future work |

Standard cross-level query parameters (SHOULD be supported when the relevant capability is declared): `language` (RFC 5646, overrides `Accept-Language`), `sort_by`, `sort_dir`.

---

## Backwards Compatibility

All additions are optional. Existing collections remain valid. The only change to existing behaviour is that `values` becomes OPTIONAL when `href` is present — collections that already omit `values` (or set it to `[]`) are unaffected.

- Legacy clients following `href` receive standard paginated JSON — indistinguishable from a traditional `values` array.
- Clients that recognise `provider.href` can navigate to the OGC API – Dimensions collection to discover capabilities.
- Clients that recognise `labels` gain multilingual display; those that don't fall back to the `label` string.

---

## Worked Examples

All examples validate against the extended schema and are backed by a live reference implementation:

| Example | Type | Demonstrates |
|---|---|---|
| [dekadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/dekadal.json) | `temporal` | `size`, `href`, slim `provider`, dekadal calendar (36/year), invertible |
| [pentadal.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/pentadal.json) | `temporal` | Two competing pentadal systems (72/yr monthly vs 73/yr annual) |
| [integer-range.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/integer-range.json) | `other` | Non-temporal integer-range dimension (100 m elevation bands, 0–5000 m) |
| [legacy-bridge.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/legacy-bridge.json) | `temporal` | ISO date output for legacy client compatibility |
| [admin-hierarchy.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/admin-hierarchy.json) | **`nominal`** | Leveled hierarchy (Country → ADM1 → ADM2), multilingual `labels`, `language_support`, sort |
| [indicator-tree.json](https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/indicator-tree.json) | **`nominal`** | Recursive hierarchy (FAOSTAT indicator tree, depth 4) |

---

## Live Reference Implementation

Deployed on the FAO Agro-Informatics Platform review environment as an extension of the [GeoID](https://github.com/un-fao/geoid) catalog platform:

- **Swagger UI:** https://data.review.fao.org/geospatial/v2/api/tools/docs
- **Dimension listing:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/
- **Paginated members (dekadal):** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/items?limit=5
- **Inverse:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-15
- **Search:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?like=2024-K*
- **Multilingual + sort:** https://data.review.fao.org/geospatial/v2/api/tools/dimensions/admin-boundaries/items?level=1&language=fr&sort_by=label

Source code, JSON Schema, OGC Building Blocks, API response examples, and interactive notebooks:

- **Spec + schema:** https://github.com/ccancellieri/ogc-dimensions
- **OGC Building Blocks:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/building-blocks
- **API response examples:** https://github.com/ccancellieri/ogc-dimensions/blob/main/spec/examples/RESPONSES.md
- **Scientific paper (preprint):** https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **Notebooks:**
  - [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb)
  - [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb)

---

## Standardization Pathway

This proposal is intended to progress through the OGC formal process:

1. **Community review** — this issue; feedback welcome on scope, naming, and design
2. **STAC Community Extension** — JSON Schema changes to `stac-extensions/datacube`
3. **OGC GeoDataCube SWG** — Change Request Proposal ([charter 22-052](https://portal.ogc.org/files/?artifact_id=104874))
4. **OGC Naming Authority** — URI registration for well-known provider types
5. **OGC Innovation Program** — testbed participation for interoperability validation
6. **OGC RFC + formal vote** — candidate specification through the OGC Technical Committee

---

## Related Work

- [STAC Language Extension](https://github.com/stac-extensions/language) — collection-level `language`/`languages` declarations; this proposal's multilingual labels align with its Language Object schema
- [STAC API Language Extension](https://github.com/stac-api-extensions/language) — `?language=`, `Accept-Language`/`Content-Language`; this proposal's per-request language negotiation follows the same contract
- [STAC API Children Extension](https://api.stacspec.org/v1.0.0-rc.2/children) — `/children` endpoint pattern; this proposal adopts the same pagination contract for dimension members
- [OGC API – Common issue #298](https://github.com/opengeospatial/ogcapi-common/issues/298) — `?parent=` filter on collections; this proposal's `/items?parent=X` filter follows the same convention
- [STAC discussion #1374](https://github.com/radiantearth/stac-spec/discussions/1374) — hierarchical STAC collections; `parent`/`child` link relation types from OGC Records are reused here
- [cadati](https://github.com/TUW-GEO/cadati) (TU Wien, MIT) — dekadal date arithmetic; the `daily-period` provider type formalises the same calendar conventions

---

*Proposed by [Carlo Cancellieri](https://ccancellieri.github.io) — [FAO AgroInformatics Platform](https://data.review.fao.org)*

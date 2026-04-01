# Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes

**Carlo Cancellieri**
[https://ccancellieri.github.io/](https://ccancellieri.github.io/)

## Abstract

Geospatial datacube standards define dimension metadata as inline arrays embedded in collection descriptions. This approach becomes impractical when dimensions scale to thousands or millions of values, as commonly occurs with non-Gregorian temporal calendars, statistical indicator catalogs, and administrative boundary hierarchies. We identify three gaps across STAC, OGC GeoDataCube API, SDMX, openEO, and nine other surveyed standards: no pagination for dimension members, no algorithmic generation rules for deterministic dimensions, and no inverse validation mechanism for data integrity enforcement.

We present a backwards-compatible extension to the STAC Datacube specification introducing three properties: `size` and `href` for paginated access following OGC API conventions, and a `generator` object that encapsulates algorithmic member generation with machine-discoverable OpenAPI definitions. The generator abstraction applies uniformly to temporal calendars, integer ranges, and coded hierarchies. For hierarchical dimensions, a `hierarchy` property provides tree metadata while the generator type determines the navigation strategy -- adding new strategies requires only new generator types, not schema changes. Five conformance levels (Basic, Invertible, Searchable, Hierarchical, Similarity) allow incremental adoption.

We validate the approach through six generator types deployed as twelve dimensions on the FAO Agro-Informatics Platform, covering calendar interoperability, hierarchical vocabulary navigation, and cross-collection alignment. Source code, JSON Schema, and worked examples are available as open-source software.

## 1. Introduction

The proliferation of analysis-ready geospatial data has driven the adoption of datacube abstractions across Earth observation, climate science, and agricultural monitoring. A datacube organizes data along named dimensions -- typically two spatial axes, a temporal axis, and one or more thematic axes (spectral bands, statistical indicators, administrative units). Metadata standards describe these dimensions so that clients can discover, subset, and process cube contents without downloading entire datasets.

The SpatioTemporal Asset Catalog (STAC) has emerged as the dominant metadata standard for cloud-native geospatial data, adopted as an OGC Community Standard in October 2025 (OGC docs 25-004, 25-005). The STAC Datacube Extension (v2.2.0+) adds `cube:dimensions` to collection metadata, defining each dimension's type, extent, step interval, and an optional `values` array enumerating all discrete members. The OGC GeoDataCube API profile, developed through Testbed 19 (doc 23-047) and Testbed 20 (doc 24-035), builds on this same STAC dimension model.

This inline enumeration works well for small dimensions -- a Sentinel-2 collection has 13 spectral bands, a climate ensemble might have 50 members. However, the approach fails when dimensions scale beyond what is practical to embed in a JSON document. Real-world examples abound: the FAO Agricultural Stress Index System (ASIS) catalogs data across 36 dekadal periods per year spanning multiple decades; the FAO FAOSTAT database contains over 10,000 statistical indicators; national statistical offices publish data across 50,000+ administrative boundary units at sub-national levels. A daily time series from 2000 to 2025 alone produces 9,131 dimension values.

The problem is compounded by the existence of non-Gregorian temporal systems that resist standard encoding. The dekadal calendar, used globally in agricultural drought monitoring and food security early warning, divides each month into three periods (days 1-10, 11-20, and 21 to month-end), producing 36 periods per year with variable-length third periods. Two distinct pentadal systems exist: a month-based variant (72 periods/year, used by CHIRPS, CDT, and FAO) and a year-based variant (73 periods/year, used by GPCP and CPC/NOAA). Neither system can be expressed as an ISO 8601 duration, and setting `step: null` to signal irregular spacing provides no mechanism to enumerate the actual members.

OGC Testbed 19 (doc 23-047) and Testbed 20 (doc 24-035) both explicitly identified these limitations. The Testbed 19 GeoDataCubes Engineering Report notes that "pagination is rarely used in openEO implementations" for dimension metadata, while simultaneously acknowledging that dimension value arrays can grow unboundedly. The European Centre for Medium-Range Weather Forecasts (ECMWF), participating in Testbed 19, specifically requested support for "irregular or sparse data content" -- a request acknowledged but not resolved by the testbed specification.

No existing standard addresses these gaps comprehensively. SDMX 3.0 provides structural decoupling through codelists but offers no pagination on structure endpoints. OGC API - Environmental Data Retrieval (EDR) supports custom dimension parameters but provides no mechanism for large-scale enumeration or algorithmic generation. The RDF Data Cube Vocabulary encodes dimension members as URIs in SKOS concept schemes but operates at a different architectural level than RESTful collection metadata.

This paper presents a unified solution through three backwards-compatible additions to the STAC Datacube dimension model:

1. **Paginated access** via `size` (member count) and `href` (link to a paginated endpoint) following OGC API - Common Part 2 conventions.

2. **Algorithmic generation** via a `generator` object that encapsulates deterministic rules for producing dimension members, with machine-discoverable OpenAPI definitions enabling both client-side computation and server-side API calls.

3. **Bijective inversion** enabling the reverse mapping from raw values to dimension coordinates, supporting data validation at ingestion time, cross-collection consistency enforcement, and data quality monitoring.

We further describe how the generator pattern, combined with vector similarity search on dimension spaces, opens an architectural pathway from traditional exact-coordinate datacube access to concept-proximity navigation -- positioning STAC collections as approximate multidimensional vector indices.

## 2. Background and Related Work

### 2.1 STAC Datacube Extension

The STAC Datacube Extension defines dimension metadata within `cube:dimensions` at the collection level. Each dimension specifies a `type` (spatial, temporal, bands, or other), an optional `extent` (minimum and maximum bounds), an optional `values` array for explicit member enumeration, a `step` for regular spacing (or null for irregular), and a `unit`. The extension serves as the dimension metadata standard for both STAC API implementations and the OGC GeoDataCube API profile.

The `values` array is the sole mechanism for communicating discrete dimension members to clients. For temporal dimensions with regular spacing, clients can derive members from `extent` and `step`. For irregular dimensions or non-temporal dimensions (indicator codes, administrative units, land cover classes), `values` is the only option. The extension provides no pagination, no external reference for large arrays, and no mechanism to express generation rules.

### 2.2 OGC API - GeoDataCube

The GeoDataCube API has evolved through four OGC Innovation Program testbeds. Testbed 16 (docs 20-016, 20-025r1) introduced the Data Access and Processing API (DAPA) with implicit dimensions (spatial, temporal, variables) but no mechanism to enumerate dimension members; the companion API report explicitly noted that "a mechanism about how to determine the available query parameters in the API was not specified." Testbed 17 (doc 21-027) produced the first draft API specification, defining dimensions via STAC `cube:dimensions` within collection metadata accessed through `GET /collections/{id}` and the Coverages domain set at `GET /collections/{id}/coverage/domainset`. Testbed 19 (docs 23-047, 23-048) refined this into a formal draft submitted to the GeoDataCube Standards Working Group as a work item. Testbed 20 (docs 24-035, 24-037) conducted usability testing across five independent backends, finding only 44% interoperability success and identifying STAC metadata inconsistency as the primary pain point.

The GDC SWG was chartered in May 2023 (OGC doc 22-052, authors: Iacopino, Simonis, Meißl) with the mandate to define a GDC API standard, metadata model, and exchange format recommendations. The charter explicitly scopes "definition of the GDC metadata model" and "analysis of the usability of existing standards" as core work items. The SWG adopts an agile methodology, building from existing OGC Building Blocks (OGC API - Common, Coverages, Processes, STAC, openEO) with minimal extension.

Across all four testbeds and the SWG charter, no specification addresses dimension member pagination. The Testbed 19 Engineering Report (doc 23-047) notes that "pagination is rarely used in openEO implementations" for dimension metadata while acknowledging unbounded growth. The Testbed 20 usability report (doc 24-037) recommends standardized STAC metadata practices but does not address the scalability of dimension value arrays. The ECMWF, participating in both Testbed 19 and the SWG use case development, specifically requested support for "irregular or sparse data content" -- a request acknowledged but not resolved by any testbed specification.

openEO defines its own dimension model through a closed `DimensionType` enum (`spatial`, `temporal`, `bands`, `geometry`, `other`) and exposes dimension metadata via `GET /collections/{id}` using the same `cube:dimensions` structure as STAC. Dimension members appear as inline `values` arrays or are derived from `extent` and `step`. The openEO process graph model treats dimensions as named references within chained operations (e.g., `filter_temporal`, `reduce_dimension`) but never retrieves or paginates members independently -- the backend resolves member sets at execution time. This design works well when backends know their own dimensions, but it means that openEO metadata responses share the same scalability limitation as STAC: large or algorithmically defined dimensions cannot be communicated to clients without embedding the full member list. The generator extension is compatible with openEO's `cube:dimensions` structure because it adds optional properties (`size`, `href`, `generator`) that openEO clients can ignore per standard JSON processing. An openEO backend could expose generator endpoints alongside its existing collection metadata, allowing advanced clients to paginate or invert dimension members while standard openEO clients continue to function unchanged.

### 2.3 SDMX and Statistical Standards

The Statistical Data and Metadata eXchange (SDMX) 3.0 provides the most mature structural metadata model through Data Structure Definitions (DSDs) and Codelists. SDMX achieves complete decoupling of dimension structure from data payload. However, SDMX structure endpoints do not support pagination -- codelists are returned as monolithic responses. SDMX 3.0 adds GeoCodelist and GeoGridCodelist for spatial dimensions, acknowledging the need for geospatial integration, but these additions address type expressiveness rather than scalability.

### 2.4 Non-Gregorian Temporal Systems

The dekadal calendar, formally documented by the FAO and widely used in agricultural applications, divides each Gregorian month into three periods. The first dekad covers days 1-10, the second covers days 11-20, and the third covers day 21 through the end of the month. This third dekad varies from 8 days (February in non-leap years) to 11 days (months with 31 days). Two distinct pentadal systems exist: the month-based system used by CHIRPS and FAO divides each month into six 5-day periods with the sixth absorbing remaining days (26 to month-end), while the year-based system used by GPCP and CPC/NOAA counts consecutive 5-day periods from January 1, with period 73 absorbing the remaining 5 or 6 days (leap year).

No standard temporal encoding -- ISO 8601, CF conventions, or OGC temporal models -- accommodates these systems natively. ISO 8601 defines no dekad or pentad duration designator. CF conventions use `time_bnds` pairs without semantic identifiers. The cadati Python package (TU Wien, MIT license) provides reference algorithms for dekadal date arithmetic.

### 2.5 Hierarchical Controlled Vocabularies in Geospatial Standards

Hierarchical classification systems are pervasive in both statistical and geospatial domains, yet no existing standard integrates their tree structure with paginated REST dimension metadata. SDMX 3.0 provides the most mature approach through its `HierarchicalCodelist` construct, which defines tree relationships between codelist members using explicit parent-child associations. SDMX hierarchical codelists are widely used by national statistical offices and international organizations to represent dimensions such as classification of individual consumption by purpose (COICOP), international standard industrial classification (ISIC), and administrative geography hierarchies. The fundamental limitation of the SDMX approach is that hierarchical codelist responses are monolithic -- the entire tree is returned in a single structure endpoint call. For classifications with tens of thousands of codes, such as the FAO FAOSTAT indicator system with over 10,000 entries, this produces responses of impractical size, defeating the scalability benefits that motivated the paginated access mechanisms described in Section 3.1.

The W3C Simple Knowledge Organization System (SKOS) provides a widely adopted RDF vocabulary for representing hierarchical concept schemes. SKOS properties `skos:broader` and `skos:narrower` encode parent-child relationships between concepts, while `skos:inScheme` associates concepts with their containing vocabulary. SKOS is the structural basis for major geospatial and agricultural ontologies: AGROVOC (FAO, 40,000+ concepts covering agriculture, food, and natural resources), GEMET (European Environment Agency), and the OGC Feature Type Catalogue. However, SKOS operates at the RDF/linked-data layer, not as paginated REST dimension metadata. Converting a SKOS concept scheme to a series of REST endpoints that a STAC client can navigate by following `rel:children` links requires architectural bridging that no current standard provides.

The STAC API Children Extension (`https://api.stacspec.org/v1.0.0-rc.2/children`) represents the closest existing REST prior art. It defines a `GET .../children` endpoint that returns immediate children of a STAC Catalog or Collection, using the same pagination envelope (`numberMatched`, `numberReturned`, `links`) and link relation types (`rel:children`, `rel:parent`, `rel:self`) as the broader STAC API. This endpoint contract is already implemented by multiple STAC API servers and consumed by clients such as PySTAC and QGIS. The architectural gap is that the Children Extension operates at the collection level -- it navigates trees of STAC Catalogs and Collections -- but provides no analogous mechanism for navigating trees of dimension members within a collection. The present work applies the same endpoint contract and pagination semantics one level lower in the resource hierarchy, from collection trees to dimension member trees.

### 2.6 Prior Art: FAO ASIS API

The FAO Agricultural Stress Index System (ASIS) implements a proprietary dimensions API at `https://data.apps.fao.org/gismgr/api/v2/catalog`. This API provides paginated dimension listing and paginated member enumeration through a 4-level resource hierarchy (workspaces, dimensions, members, member detail). The ASIS API demonstrates the practical need for paginated dimension access in production agricultural monitoring systems. However, it uses a non-standard pagination model (page-based rather than offset-based), wraps responses in a custom envelope, and models dekadal periods as categorical ("WHAT" type) rather than temporal. The present work draws on this operational experience while aligning with OGC API conventions.

### 2.7 Comparative Summary

Table 1 summarizes the capabilities surveyed across existing standards and this proposal. No existing standard addresses all four requirements simultaneously.

| Standard / System | Paginated members | Algorithmic generation | Inverse validation | Hierarchical navigation |
|---|---|---|---|---|
| STAC Datacube Ext. (v2.2) | No (`values` inline) | No | No | No |
| OGC GDC API (TB-17–20) | No (inherits STAC) | No | No | No |
| OGC API - EDR | No (custom params) | No | No | No |
| SDMX 3.0 | No (monolithic) | No | No | Yes (HierarchicalCodelist) |
| W3C SKOS | N/A (RDF layer) | No | No | Yes (broader/narrower) |
| RDF Data Cube Vocabulary | N/A (RDF layer) | No | No | No |
| openEO | No (inline arrays) | No | No | No |
| CF Conventions | No (file-level) | No | No | No |
| FAO ASIS API | Yes (proprietary) | No | No | No |
| **This proposal** | **Yes** (OGC API) | **Yes** (OpenAPI) | **Yes** (`/inverse`) | **Yes** (`/children`, `/ancestors`) |

## 3. Specification

### 3.1 Paginated Dimension Members

We propose two new properties on the STAC Datacube Extension dimension object:

**`size`** (integer, RECOMMENDED): The total number of discrete members in the dimension. This allows clients to assess cardinality without downloading any values. The property aligns with the existing community request in STAC Datacube Extension issue #31.

**`href`** (string, URI, OPTIONAL): A link to a paginated endpoint returning dimension values. When present, the `values` array MAY be omitted. The endpoint follows OGC API - Common Part 2 pagination conventions with `limit` and `offset` query parameters. Responses include `numberMatched` and `numberReturned` fields following the OGC API - Features convention, and `rel:next`/`rel:prev` link relations per RFC 5988.

Both properties are backwards-compatible additions. Existing clients that read only the `values` array continue to work for small dimensions. Servers may provide inline `values` for dimensions below an implementation-defined threshold (recommended: 1000 members) while using `href` for larger dimensions.

A paginated response follows OGC API - Features conventions:

```json
{
  "dimension": "dekadal",
  "numberMatched": 900,
  "numberReturned": 5,
  "values": ["2024-K01", "2024-K02", "2024-K03", "2024-K04", "2024-K05"],
  "links": [
    {"rel": "self",  "href": ".../members?limit=5&offset=0"},
    {"rel": "next",  "href": ".../members?limit=5&offset=5"}
  ]
}
```

Clients follow `rel:next` links to retrieve subsequent pages. The `numberMatched` field communicates total cardinality without downloading all values, while `numberReturned` indicates the current page size.

### 3.2 The Generator Object

Many dimensions follow deterministic rules that make explicit enumeration wasteful. We introduce a `generator` property on any dimension object, applicable to temporal, spatial, and thematic dimensions alike.

The generator object contains the following fields:

- **`type`** (string or URI, REQUIRED): A short identifier for well-known algorithms (`dekadal`, `pentadal-monthly`, `pentadal-annual`, `iso-week`, `integer-range`, `grid-index`) or a full URI for custom generators. Well-known types resolve to registered OGC Definition URIs.

- **`api`** (string, URI, CONDITIONAL): An OpenAPI definition URI. Required for custom generators; implicit for well-known types. Machine clients fetch this specification to discover the generation endpoint and its parameters.

- **`parameters`** (JSON Schema, OPTIONAL): Input parameters for the algorithm, defined per JSON Schema 2020-12. This avoids inventing a new type system and leverages existing tooling and developer familiarity.

- **`output`** (JSON Schema, REQUIRED): The type and structure of each generated member, also defined per JSON Schema 2020-12. Supports simple types (`string` with `format: "date-time"`), integers, and structured objects with multiple fields.

- **`invertible`** (boolean, OPTIONAL, default false): Whether the generator exposes `/inverse` — a well-defined, deterministic lookup from any domain value to exactly one dimension member. See Section 3.3 for the mathematical semantics.

- **`search`** (array of strings, OPTIONAL): Supported search protocols (`exact`, `range`, `like`, `vector`).

- **`on_invalid`** (string, OPTIONAL): Item ingestion behavior when inverse validation fails (`reject`, `accept`, `warn`).

- **`hierarchical`** (boolean, OPTIONAL, default false): Whether the generator supports Hierarchical conformance level -- `/children`, `/ancestors`, and the `?parent=` filter on `/members`. This property should be `true` when the dimension declares a `hierarchy` property. See Section 3.6.

- **`navigable`** (boolean, OPTIONAL, default false): Whether the generator supports per-member navigation links (`rel:children`, `rel:ancestors`) when clients request them via `?links=true`. Requires `hierarchical: true`. By default, member-level links are suppressed to minimize response size; response-level pagination links (`self`, `next`, `prev`) are always included.

Each generator's OpenAPI specification exposes up to four capabilities: `/members` for paginated member production, `/extent` for boundary computation, `/search` for query-based member discovery, and `/inverse` for value-to-coordinate mapping. The `/members` endpoint is unified with `href` -- both point to the same paginated interface.

Content negotiation through the `format` parameter enables backwards compatibility: `format=datetime` (default) produces standard ISO timestamps that legacy clients understand; `format=native` produces custom notation (e.g., `YYYY-Knn` for dekadal codes); `format=structured` produces full objects with code, start date, end date, and additional metadata.

The following example shows a STAC collection with a dekadal temporal dimension using all three proposed properties:

```json
{
  "cube:dimensions": {
    "time": {
      "type": "temporal",
      "extent": ["2000-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
      "generator": {
        "type": "dekadal",
        "api": "http://www.opengis.net/def/generator/ogc/0/dekadal/openapi.json",
        "parameters": {},
        "output": {
          "type": "object",
          "properties": {
            "code": {"type": "string", "description": "YYYY-Knn (nn=01..36)"},
            "start": {"type": "string", "format": "date"},
            "end": {"type": "string", "format": "date"},
            "days": {"type": "integer", "minimum": 8, "maximum": 11}
          },
          "required": ["code", "start", "end"]
        },
        "invertible": true,
        "search": ["exact", "range", "like"],
        "on_invalid": "reject"
      },
      "step": null,
      "unit": "dekad",
      "size": 900,
      "href": ".../dimensions/dekadal/members?limit=100"
    }
  }
}
```

Legacy clients that do not recognize `generator`, `size`, or `href` ignore these properties per standard JSON processing rules. Clients that do recognize `href` can follow it to retrieve paginated members without any knowledge of the generation algorithm. For example, a legacy client requesting `?format=datetime` receives standard ISO dates (`["2024-01-01", "2024-01-11", "2024-01-21", ...]`) -- a valid irregular temporal dimension indistinguishable from a traditional `values` array. Generator-aware clients can additionally use `/inverse`, `/search`, and native format negotiation.

### 3.3 Generator Invertibility and Dimension Integrity

A generator defines a forward function *f* from the value domain *V* (e.g., all calendar dates) to the set of dimension members *M* (e.g., all dekads). This function is *total* — every element of *V* maps to exactly one member — and *surjective* — every member has at least one preimage in *V*. It is not, in general, injective: many dates belong to the same dekad, and many elevation values fall within the same band. The generator therefore induces an equivalence relation on *V*, partitioning the domain into disjoint intervals, each corresponding to one dimension member. This partition is precisely the *quantization function* of information theory and the *partitioning predicate* of distributed storage systems (Hive, Iceberg, Delta Lake).

We refer to generators that support this partition semantics as *invertible* generators, using the conformance level name Invertible (Section 3.5). In the `generator` object, these generators set `invertible: true`. The generator's forward function is a total surjection from domain values to members, and its `/inverse` endpoint computes the unique member *m* such that *v* falls within the interval defined by *m*. Inverse lookup is thus well-defined and O(1) for all generators implemented here.

When a value falls outside the generator's declared extent — for example, an elevation of 9,000 m in a dimension bounded by 0–8,848 m — the generator reports `valid: false` and, where applicable, identifies the nearest valid member to assist data repair workflows. This failure mode is analogous to a foreign key constraint violation in relational databases: the value exists syntactically but cannot be placed within any dimension member.

```
GET /dimensions/dekadal/inverse?value=2024-01-15
→ {"valid": true, "member": "2024-K02",
   "range": {"start": "2024-01-11", "end": "2024-01-20"}}

GET /dimensions/dekadal/inverse?value=2024-01-32
→ {"valid": false, "reason": "Cannot parse '2024-01-32' as a date."}
```

The invertibility property serves three purposes in datacube management. First, it enables *ingestion validation*: when a new item is inserted, its dimension values are submitted to `/inverse`, and the `on_invalid` policy governs the outcome — `reject` enforces strict referential integrity, `accept` allows schema-on-read expansion, and `warn` flags anomalies without blocking ingestion. Second, it enforces *cross-collection consistency*: multiple collections sharing the same `generator.type` and endpoint are guaranteed to use identical member boundaries, eliminating the off-by-one errors that arise when independent systems compute period boundaries from shared but under-specified conventions. Third, it supports *data quality monitoring*: the ratio of valid to invalid inverse results across an ETL pipeline is a direct measure of alignment between incoming data and the declared dimension structure. For invertible generators, the `/inverse` endpoint supports both single-value queries (GET) and batch operations (POST) for efficient pipeline integration.

### 3.4 Search and Similarity

Generators may optionally expose a search capability supporting multiple protocols. Deterministic protocols (`exact`, `range`, `like`) enable traditional filtering on generated or stored dimension members. The `vector` protocol opens an architectural pathway to AI-powered dimension navigation: when dimension members are associated with embedding vectors, clients can search by similarity rather than exact coordinates, effectively navigating the datacube by concept proximity.

This positions STAC collections as approximate multidimensional vector indices. Each dimension with a searchable generator contributes one axis of a multi-dimensional index. A client searching across N dimensions receives items ranked by combined similarity across all axes -- a fundamentally different access pattern from traditional exact-coordinate subsetting.

### 3.5 Conformance Levels

We define five conformance levels as an additive hierarchy:

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | /members + /extent | MUST support |
| Invertible | + /inverse | Invertible generators only |
| Searchable | + /search (exact, range, like) | SHOULD support |
| Hierarchical | + /children + /ancestors + ?parent= filter | Required when hierarchy is declared |
| Similarity | + /search (vector) | MAY support; future work |

Basic constitutes the minimum requirement for any generator implementation. Invertible applies to generators that implement the partition semantics described in Section 3.3 — that is, generators for which every domain value maps deterministically to exactly one member. Temporal calendars (dekadal, pentadal) and integer ranges satisfy this property; the generator field `invertible: true` signals this capability. Its concrete use cases are ingestion validation (rejecting items whose dimension values fall outside any valid member interval), cross-collection consistency (guaranteeing identical member boundaries across collections sharing the same generator type), and data quality monitoring (tracking the valid-to-invalid ratio of incoming values as a pipeline health metric). Searchable is recommended for any non-trivial dimension. Hierarchical is required when the dimension declares a `hierarchy` property and is orthogonal to Invertible — a hierarchical nominal dimension may independently be invertible if its member codes are canonical identifiers (for example, ISO 3166-1 alpha-3 country codes, where the forward function maps an incoming code to its matching member or reports an error). Similarity documents the architectural runway toward embedding-based dimension navigation without imposing immediate implementation requirements.

### 3.6 Hierarchical Dimension Members

Many dimension types in geospatial datacubes are inherently hierarchical. Administrative boundaries follow a well-defined tree: countries subdivide into regions, regions into districts, districts into localities. The FAO Global Administrative Unit Layers (GAUL) organizes 195 countries into 3,469 first-level administrative units and 46,031 second-level units across three hierarchy levels. Statistical indicator catalogs are similarly organized: the FAO FAOSTAT database groups over 10,000 indicators into domains, groups, and subgroups across four levels. Land cover classifications, OGC feature type hierarchies, and SDMX-coded dimensions exhibit comparable structures. For dimensions of this kind, enumeration via a flat `values` array or a single `href` is insufficient -- clients must navigate the tree to discover relevant members, and embedding the entire hierarchy in a single paginated stream discards structural information that enables efficient subsetting and display.

We introduce a `hierarchy` property on the dimension object that describes the tree structure and the strategy used to encode it. Two strategies are defined. The recursive strategy is used when the hierarchy is encoded directly inside the data: each member's generator output includes a field whose value is the code of its parent, or null for root members. This mirrors the semantics of W3C SKOS `skos:broader`, where each concept declares its broader (parent) concept. Clients navigate the tree by requesting root members (those whose parent field is null) and then following `/children` links for each node of interest. For the FAOSTAT indicator tree, a generator output object carries a `parent_code` field typed as `string | null`, and the `hierarchy.parent_property` field names this field so that clients and servers can identify it without prior knowledge of the domain-specific schema.

The leveled strategy is used when the hierarchy is not encoded in the data itself but is imposed by named level definitions. This pattern arises when the underlying data store is a flat table with multiple columns representing different hierarchical levels: a row might carry `iso_code`, `adm1_code`, and `adm2_code` simultaneously, and the tree structure is derived by grouping rows by level rather than read from a parent reference field. Each level in the `levels` array specifies: `id` (a unique level identifier), `label` (a human-readable name), `parent_level` (the `id` of the parent level, absent on the root), `member_id_property` (which output field uniquely identifies members at this level), `parent_id_property` (which output field identifies the parent member at the parent level), and a `parameters` object encoding the generator parameters needed to filter members to this level. The `parameters` object is the backend-agnostic generalization of a SQL `WHERE` clause or CQL filter: the implementation details of how the filter is applied remain inside the generator, while the specification exposes only the parameter values. This design generalizes the operational experience of the geoid system, in which hierarchy rules encode SQL conditions per level alongside `item_code_field` and `parent_code_field` column mappings.

Two generator endpoints implement tree navigation at the Hierarchical conformance level. The `GET /{dimension_id}/children?parent=X` endpoint returns the direct children of member X, using the same pagination envelope (`numberMatched`, `numberReturned`, `links`) as the `/members` endpoint. The response additionally includes the parent code and a `rel:parent` link relation pointing to the parent member, mirroring the STAC API Children Extension's link relation conventions. The `GET /{dimension_id}/ancestors?member=X` endpoint returns the complete ancestor chain from root to member X inclusive, ordered from coarsest to finest granularity. For backwards compatibility, the existing `/members` endpoint accepts an optional `?parent=X` query parameter as an alias for `/children?parent=X`, allowing clients that already use `href` for pagination to navigate the hierarchy without learning a new endpoint pattern.

The distinction between the two navigation endpoints reflects distinct client use cases. A mapping application rendering a country selector first calls `/children` with no parent (obtaining root members) to populate a continent dropdown, then calls `/children?parent=Africa` on user selection to populate a country dropdown. A data pipeline that receives an incoming observation labeled with a sub-national code calls `/ancestors?member=ETH-TIG` to resolve the full administrative path, validating the code against the dimension hierarchy and obtaining the ancestor codes needed for regional aggregation. Both operations are analogous to standard tree operations in relational systems (adjacency list queries) and graph databases (breadth-first traversal), expressed as a RESTful paginated API that requires no query language.

The STAC Datacube Extension currently defines dimension types as `spatial`, `temporal`, `bands`, and `other`. Administrative boundaries, indicator codes, land cover classes, and similar dimensions fall into `other` by default, which provides no semantic information. We propose two new type values: `nominal` for unordered coded dimensions whose members are named categories without inherent rank (administrative units, indicator codes, species classifications), and `ordinal` for ordered coded dimensions whose members have an inherent rank or severity order (quality flags, data confidence levels, hazard severity classes). Both terms are established in statistical taxonomy and dimensional analytics, are already used in the geoid system's `DatacubeDimensionType` enumeration, and are backwards-compatible additions -- implementations that do not recognise `nominal` or `ordinal` treat them as unknown type values and continue processing the dimension using its other standard properties.

The Hierarchical conformance level is orthogonal to all other conformance levels. A generator that declares `hierarchical: true` exposes `/children`, `/ancestors`, and the `?parent=` filter; it may independently be invertible (declaring `invertible: true` to also expose `/inverse`), searchable, or both. The world-admin demo dimension in the reference implementation illustrates this independence: the static tree generator is hierarchical and searchable but not invertible, because continent and country codes are not deterministically derivable from spatial coordinates without additional metadata. A dimension of ISO 3166-1 alpha-3 country codes with a lookup-table generator would be both hierarchical and invertible if the lookup function is surjective.

## 4. Implementation and Validation

### 4.1 Reference Implementation

We provide an open-source reference implementation as a Python package (`ogc-dimensions`) with a FastAPI REST API. The source code, JSON Schema specification, and worked examples are available at https://github.com/ccancellieri/ogc-dimensions under the Apache-2.0 license.

A live deployment is available on the FAO Agro-Informatics Platform review environment, integrated as an extension of the GeoID catalog platform (https://github.com/un-fao/geoid). The deployment demonstrates all generator endpoints with full pagination, inverse mapping, and search capabilities. The Swagger UI is accessible at https://data.review.fao.org/geospatial/v2/api/tools/docs, and the `href` links in the worked examples point directly to these live endpoints.

The implementation includes six generator types:

- **DekadalGenerator**: 36 periods/year, invertible, searchable (exact, range, like)
- **PentadalMonthlyGenerator**: 72 periods/year (month-aligned variant used by CHIRPS/FAO), invertible, searchable
- **PentadalAnnualGenerator**: 73 periods/year (year-aligned variant used by GPCP/CPC/NOAA), invertible, searchable
- **IntegerRangeGenerator**: configurable step, invertible, searchable (exact, range)
- **StaticTreeGenerator**: in-memory recursive tree; Hierarchical and Searchable conformance; not invertible
- **LeveledTreeGenerator**: extends `StaticTreeGenerator` with a `?level=` filter parameter, supporting condition-based level queries (`?level=0` for root members, `?level=1&parent=X` for children at a specific level)

The temporal and integer-range generators implement the Basic, Invertible, and Searchable conformance levels. The `StaticTreeGenerator` implements the Basic, Searchable, and Hierarchical conformance levels. The `LeveledTreeGenerator` extends these with level-based filtering, demonstrating the leveled hierarchy strategy: clients may query by level (obtaining all members at a given depth) or by parent (navigating the tree), or combine both.

The live deployment at https://data.review.fao.org/geospatial/v2/api/tools/docs exposes twelve named dimensions through the geoid DimensionsExtension. Five originate from the ogc-dimensions package defaults (`dekadal`, `pentadal-monthly`, `pentadal-annual`, `integer-range`, `world-admin`). Seven additional dimensions are registered by the DimensionsExtension at startup to illustrate the full capability surface: `temporal-dekadal`, `temporal-pentadal-monthly`, `temporal-pentadal-annual`, `indicator-tree`, `admin-boundaries`, `forestry-species`, and `elevation-bands`. These dimensions are described in detail in Section 5.

The hierarchical demo dimensions use small datasets (30–67 nodes) designed to demonstrate the API contract and endpoint semantics. Production-scale validation against full hierarchies — GAUL L0–L2 (49,695 administrative units), FAOSTAT (10,000+ indicators) — is planned through the GeoID integration, where the DimensionsExtension can back the same API contract with database-driven generators rather than in-memory trees. The temporal generators, by contrast, are algorithmically unbounded: the 100-year extents in the demo (3,636–7,373 members) exercise pagination at realistic scale.

### 4.2 Validation Results

We validate correctness of the dekadal generator against known edge cases:

| Test Case | Input | Expected | Result |
|---|---|---|---|
| D3 February non-leap | 2023-02-21 | K06: Feb 21-28 (8 days) | Correct |
| D3 February leap | 2024-02-21 | K06: Feb 21-29 (9 days) | Correct |
| D3 month with 30 days | 2024-06-21 | K18: Jun 21-30 (10 days) | Correct |
| D3 month with 31 days | 2024-01-21 | K03: Jan 21-31 (11 days) | Correct |
| Inverse mid-dekad | 2024-01-15 | K02 (Jan 11-20) | Correct |
| Inverse last day of D3 | 2024-06-30 | K18 (Jun 21-30) | Correct |
| Year boundary | 2024-12-31 | K36 (Dec 21-31) | Correct |
| Invalid date | 2024-01-32 | valid: false | Correct |

The pentadal generators are validated against CHIRPS (monthly variant) and GPCP (annual variant) period definitions. The integer-range generator is validated against standard binning operations.

### 4.3 Performance Characteristics

Table 2 reports latency measurements from the reference implementation running locally (Python 3.12, FastAPI/Uvicorn, Apple M2, single worker). All measurements are averages over 10 HTTP requests or 10,000 function calls.

| Operation | Extent | Latency |
|---|---|---|
| `/members` (dekadal, 100-year, page=100) | 3,636 members | < 1 ms HTTP |
| `/members` (dekadal, page at offset 1800) | mid-range page | < 1 ms HTTP |
| `/inverse` (single value) | — | 1.9 us/call |
| `/inverse` batch (1,200 values) | — | 3.2 ms |
| `/children` (tree, 13 children) | 54 nodes | < 1 ms HTTP |

Inverse computation is O(1) per value for temporal generators (direct arithmetic from date components). Batch inverse processes 1,200 values in 3.2 ms, making ingestion validation of millions of records practical within ETL pipeline latency budgets.

The current reference implementation materializes the full member list before slicing to the requested page. This is adequate for the intended demonstration scale (hundreds to low thousands of members) but would benefit from lazy iteration for production deployments spanning millions of members. Database-backed generator implementations — such as the GeoID DimensionsExtension, which delegates to PostgreSQL or Elasticsearch — avoid this limitation entirely by pushing pagination to the query layer.

## 5. Use Cases

The six use-case dimensions deployed on the live endpoint collectively demonstrate every conformance level defined in Section 3.5. Each subsection below describes the operational problem, the specific capability gap in current standards, and how the generator specification resolves it. All examples reference the live endpoints at https://data.review.fao.org/geospatial/v2/api/tools/docs.

### 5.1 Temporal Calendar Interoperability — Competing Pentadal Systems

**Story.** The global meteorological and agricultural monitoring community uses three non-Gregorian temporal calendars operationally: the dekadal (10-day, 36 periods/year), the month-aligned pentadal (5-day, 72 periods/year), and the year-aligned pentadal (5-day, 73 periods/year). The first is standard in early warning systems and drought monitoring (see Section 2.4 and reference [13]). The latter two represent two incompatible encodings of the same conceptual unit — a five-day observation window — adopted independently by different producer communities. Month-aligned pentads are used by rainfall estimation products that align period boundaries to month-end (e.g., CHIRPS [14], CDT, and FAO products); year-aligned pentads are used by global precipitation climatology products that count periods continuously from 1 January without regard for month boundaries (e.g., GPCP, CPC/NOAA).

The critical interoperability problem is that pentad code `P12` in the month-aligned system and pentad code `P12` in the year-aligned system refer to different calendar intervals. In the month-aligned system, P12 falls within February (the second period of the second month); in the year-aligned system, P12 corresponds to 1–5 March (the twelfth consecutive five-day block from 1 January). A client that joins two collections sharing the label `P12` without knowing which pentadal convention each collection uses will silently produce misaligned results — the kind of systematic error that is difficult to detect because the data values themselves are valid.

**Gap.** No current standard provides a mechanism to declare the calendar convention alongside the dimension metadata. The STAC Datacube Extension `step` field allows `null` for irregular dimensions but provides no way to name the calendar algorithm. Two collections could both declare `"type": "temporal", "step": null` and appear structurally identical while using incompatible period boundaries.

**Solution.** Three temporal dimensions are deployed on the reference endpoint to demonstrate this contrast side by side:

- `temporal-dekadal` — `DekadalGenerator`, 36 periods/year, extent 1950-01-01 to 2050-12-31 (3,636 members across 100 years)
- `temporal-pentadal-monthly` — `PentadalMonthlyGenerator`, 72 periods/year, month-aligned (7,272 members)
- `temporal-pentadal-annual` — `PentadalAnnualGenerator`, 73 periods/year, year-aligned (7,373 members)

Each dimension's `generator.type` is a distinct identifier (`dekadal`, `pentadal-monthly`, `pentadal-annual`), enabling clients to detect calendar system mismatches before joining data. The invertible generator's `/inverse` endpoint makes the incompatibility explicit and machine-checkable: `GET /dimensions/temporal-pentadal-monthly/inverse?value=1950-P12` and `GET /dimensions/temporal-pentadal-annual/inverse?value=1950-A12` return different date ranges, demonstrating that the same numeric position maps to different calendar intervals in the two systems.

The 100-year extents are intentional: they produce member counts (3,636 to 7,373) that are impractical to embed in a collection JSON document, directly motivating the `size` + `href` pagination mechanism. With `limit=10`, a client retrieves only the first ten periods of any dimension and follows `rel:next` links to advance through the archive. The `numberMatched` field communicates total cardinality in the first response, enabling progress indicators and pre-allocation.

```
GET /dimensions/temporal-dekadal/members?limit=10
→ {"numberMatched": 3636, "numberReturned": 10,
   "values": [{"code": "1950-K01", "start": "1950-01-01", "end": "1950-01-10"}, ...],
   "links": [{"rel": "next", "href": "...?limit=10&offset=10"}]}

GET /dimensions/temporal-pentadal-monthly/members?limit=10
→ {"numberMatched": 7272, "numberReturned": 10,
   "values": [{"code": "1950-P01", "start": "1950-01-01", "end": "1950-01-05"}, ...]}

GET /dimensions/temporal-pentadal-annual/members?limit=10
→ {"numberMatched": 7373, "numberReturned": 10,
   "values": [{"code": "1950-A01", "start": "1950-01-01", "end": "1950-01-05"}, ...]}
```

The first period of both pentadal systems happens to coincide (1–5 January). The divergence becomes visible from period 6 onward, and is most acute in February. By deploying all three systems on the same endpoint with the same extent, the reference implementation provides a concrete demonstration that can be used in conformance testing and interoperability workshops.

### 5.2 Statistical Indicator Tree — Recursive Hierarchy

**Story.** International statistical databases organize thousands of indicators into multi-level thematic hierarchies. A food security datacube, for example, structures its indicator dimension across three levels: domain (broad thematic area such as Food Security, Production, or Trade), group (thematic cluster within a domain), and indicator (individual measure with a unit of observation). Clients building analytical dashboards need to navigate this tree progressively — starting from the domains visible in a menu, drilling into groups on user selection, and reaching specific indicators only when needed — rather than loading all 10,000+ codes at startup.

**Gap.** The STAC Datacube `values` array provides a flat enumeration with no parent-child relationships. SDMX hierarchical codelists carry tree structure but return monolithic responses. Neither model supports progressive tree navigation over a paginated REST interface.

**Solution.** The `indicator-tree` dimension uses `StaticTreeGenerator` with a three-level recursive hierarchy: six thematic domains (Food Security, Production, Trade, Environment, Land Use, Employment) as roots; thematic groups as level-1 members with `parent_code` pointing to their domain; and specific indicators as level-2 leaves carrying measurement units. The dimension declares `hierarchy.strategy: "recursive"` with `parent_property: "parent_code"`.

```
GET /dimensions/indicator-tree/members
→ [FS, PROD, TRD, ENV, LND, EMP]   ← 6 root domains

GET /dimensions/indicator-tree/children?parent=FS
→ [FS-AVL, FS-ACC, FS-UTL, FS-STB]   ← 4 Food Security groups

GET /dimensions/indicator-tree/ancestors?member=FS-AVL-DES
→ [FS, FS-AVL, FS-AVL-DES]   ← full path: domain → group → indicator
```

The ancestor chain returned by `/ancestors` enables breadcrumb navigation in user interfaces and resolves partial codes to their full context in automated pipelines. A data ingestion process that receives a batch of values tagged with indicator code `FS-AVL-DES` can call `/ancestors` to verify the full classification path and extract parent-level aggregation keys (`FS-AVL`, `FS`) in a single round-trip.

### 5.3 Administrative Boundaries — Leveled Hierarchy with Condition-Based Filtering

**Story.** Global administrative boundary datasets (such as GAUL [28], GADM, and national NSDIs) provide territorial reference frames for food security, health, and climate analyses. These datasets are organized as strict level hierarchies: continents contain countries, countries contain first-level administrative units (provinces, states, oblasts), and first-level units contain second-level units (districts, counties, woredas). A client building a geographic filter needs to populate a cascade of dropdowns — selecting a continent to narrow the country list, then a country to narrow the region list — without downloading all 50,000+ administrative codes upfront.

**Gap.** The recursive strategy is adequate when each record carries an explicit `parent_code` field. However, many real-world administrative datasets are stored as flat tables with multiple columns (`iso_country`, `adm1_code`, `adm2_code`) rather than an adjacency list. In this case the hierarchy is imposed by level definitions, not encoded as a parent reference in the data itself. The leveled strategy addresses this pattern: each level is defined by the parameters that select its members from the underlying data store, without exposing the internal column structure to the client.

**Solution.** The `admin-boundaries` dimension uses `LeveledTreeGenerator` with 67 nodes across three levels (5 continents at level 0, 33 countries at level 1, 29 sub-national regions for selected countries at level 2). It adds `?level=` parameter support to the `/members` endpoint, enabling condition-based queries independent of tree navigation:

```
GET /dimensions/admin-boundaries/members?level=0
→ [AFR, AMR, ASI, EUR, OCE]   ← all 5 continents

GET /dimensions/admin-boundaries/members?level=1
→ 33 countries   ← all countries, regardless of continent

GET /dimensions/admin-boundaries/members?level=1&parent=EUR
→ [DEU, ESP, FRA, GBR, ITA, POL, ROU]   ← European countries only

GET /dimensions/admin-boundaries/members?level=2&parent=ITA
→ [ITA-LOM, ITA-LAZ, ITA-CAM, ITA-SIC, ITA-VEN, ITA-PIE, ITA-EMR, ITA-TOS]

GET /dimensions/admin-boundaries/ancestors?member=ITA-LOM
→ [EUR, ITA, ITA-LOM]   ← full ancestry chain
```

The `?level=` filter implements the condition-based navigation pattern described in Section 3.6: a client that knows the desired level (e.g., "all countries") retrieves a flat list without tree traversal, while a client performing drill-down navigation combines `level` with `parent` to stay within a subtree. Both patterns use the same endpoint with the same pagination envelope; no separate endpoint or special query language is required.

The region codes follow a natural `{COUNTRY}-{REGION}` structure (e.g., `ITA-LOM`, `ETH-TIG`) that makes pattern-based search directly useful. A client calling `GET /dimensions/admin-boundaries/search?like=ITA*` retrieves Italy and all its regions in a single response, demonstrating that the Searchable and Hierarchical conformance levels complement each other: tree navigation and pattern search are orthogonal capabilities on the same dimension.

### 5.4 Forestry Species Classification — Search on Hierarchical Vocabulary

**Story.** Species classification trees (taxonomies) are a widespread hierarchical dimension in biodiversity, forestry, and land cover datacubes. A forest inventory system might organize its species dimension across three levels: order, family, and species. Clients need two complementary navigation modes: tree traversal (what species belong to family Pinaceae?) and vocabulary search (find all species whose name starts with "Pinus"). Neither mode alone is sufficient — field data often arrives with partial codes or common names that require both searching the vocabulary and resolving the full classification path.

**Gap.** No standard supports combining Hierarchical and Searchable conformance on the same dimension endpoint. Existing tree APIs (SKOS, SDMX) support traversal but not fuzzy name search. Full-text search engines support pattern matching but not tree structure.

**Solution.** The `forestry-species` dimension uses `StaticTreeGenerator` with 29 nodes across three levels: four botanical orders (Pinales, Fagales, Sapindales, Myrtales) as roots; six families; and nineteen species as leaves. Both `exact` and `like` search protocols are enabled alongside `/children` and `/ancestors` navigation.

```
GET /dimensions/forestry-species/search?like=Pinus*
→ 4 pine species: Pinus sylvestris, Pinus pinaster, Pinus halepensis, Pinus nigra

GET /dimensions/forestry-species/search?exact=Quercus robur
→ 1 match: {code: "Quercus robur", label: "Pedunculate Oak", parent_code: "FAGACEAE"}

GET /dimensions/forestry-species/children?parent=FAGACEAE
→ [Quercus robur, Quercus ilex, Quercus suber, Fagus sylvatica, Castanea sativa]

GET /dimensions/forestry-species/ancestors?member=Pinus sylvestris
→ [PINALES, PINACEAE, Pinus sylvestris]
```

This use case corresponds architecturally to vocabulary services such as AGROVOC [29] (FAO agricultural thesaurus, 40,000+ concepts) and GEMET, which combine hierarchical SKOS concept schemes with full-text search. The generator API bridges these vocabulary systems to the STAC dimension model: any SKOS concept scheme can be exposed as a hierarchical, searchable dimension generator through an adaptor that maps `skos:narrower` to `/children` and `skos:prefLabel` pattern queries to `/search?like=`. Clients need not learn SPARQL or the SKOS data model; they use the same dimension API they already know.

### 5.5 Elevation Bands — Bijective Generator and Ingestion Validation

**Story.** Elevation-indexed datasets (terrain analysis products, land cover stratifications, hydrological models) partition the vertical dimension into fixed-size bands. An elevation band dimension with 50 m step from 0 to 8,848 m (the summit of Everest) produces 177 members. When a new raster file is ingested with an elevation tag of `4500`, the system must verify that `4500` maps to a valid band boundary, determine the band index for partitioning, and reject values that fall outside the declared extent.

**Gap.** Integer range dimensions are currently expressed as `"type": "other"` with a `values` array that must be materialized in full. A 50 m step elevation dimension across the full topographic range requires a 177-element array in every collection response. The inverse operation — mapping a raw elevation value to its band — must be reimplemented by every ingestion pipeline.

**Solution.** The `elevation-bands` dimension uses `IntegerRangeGenerator(step=50)` with extent 0–8848 m. It implements the Invertible conformance level: `/inverse` accepts a raw elevation value and returns the enclosing band, its index, and the band's boundary range.

```
GET /dimensions/elevation-bands/extent
→ {"native": {"min": 0, "max": 8848}, "size": 177}

GET /dimensions/elevation-bands/inverse?value=4500
→ {"valid": true, "member": 4500, "index": 90,
   "range": {"start": 4500, "end": 4550}}

GET /dimensions/elevation-bands/inverse?value=9000
→ {"valid": false, "reason": "9000 is outside extent [0, 8848]",
   "nearest": {"member": 8800, "index": 176}}

POST /dimensions/elevation-bands/inverse
{"values": ["100", "4500", "8800", "9000"], "on_invalid": "reject"}
→ {"count": 4, "results": [
    {"valid": true,  "member": 100,  "index": 2},
    {"valid": true,  "member": 4500, "index": 90},
    {"valid": true,  "member": 8800, "index": 176},
    {"valid": false, "reason": "9000 is outside extent [0, 8848]"}
  ]}
```

The batch inverse endpoint (POST) is designed for ETL pipeline integration: a process ingesting thousands of elevation-tagged items submits all values in a single request and receives a per-value validity report. The `on_invalid: "reject"` policy causes the entire batch to be flagged when any value falls outside the dimension domain, enforcing strict referential integrity. The `nearest` field in invalid responses assists data repair workflows by suggesting the closest valid band.

### 5.6 Cross-Collection Temporal Alignment

Multiple collections sharing the same temporal cadence — NDVI composites, precipitation estimates, and soil moisture indicators, all at dekadal frequency — must use identical temporal coordinates to be jointly queryable. Without a shared generator definition, independent systems compute period boundaries separately and may introduce off-by-one errors at month boundaries (particularly for the third dekad, which varies between 8 and 11 days depending on the month). By referencing the same `generator.type: "dekadal"` with the same endpoint, all collections in the same platform are guaranteed to use coordinates produced by the same algorithm. The `/inverse` endpoint makes this guarantee enforceable at ingestion time: when a new item is inserted into any collection in the system, its temporal value is submitted to `/inverse`, and a mismatch with the expected dekadal boundary produces a hard rejection rather than a silent data quality issue.

The three temporal dimensions deployed on the reference endpoint (`temporal-dekadal`, `temporal-pentadal-monthly`, `temporal-pentadal-annual`) can also be used to demonstrate cross-system misalignment: a test harness can submit the same date to all three `/inverse` endpoints and observe that each returns a different `member` code, making the incompatibility explicit, machine-detectable, and auditable.

## 6. Standardization Pathway

We propose a phased approach to standardization:

1. **Community publication**: This paper and the companion GitHub repository (specification, reference implementation, worked examples) serve as the initial community contribution.

2. **STAC Community Extension**: Submit JSON Schema changes (`size`, `href`, `generator`) to `stac-extensions/datacube`, referencing Testbed 19/20 findings.

3. **OGC GeoDataCube SWG**: Submit as a Change Request Proposal to the GeoDataCube specification, proposing `generator` as a new conformance class.

4. **OGC Naming Authority**: Register generator algorithm definitions (dekadal, pentadal-monthly, pentadal-annual) as OGC Definition URIs with SKOS RDF descriptions.

5. **OGC Innovation Program**: Propose "Scalable Dimension Members" as a thread topic for a future OGC Testbed, with the reference implementation as a testbed component.

A natural objection is that extending STAC's datacube schema is "too opinionated" -- that dimension pagination and generation should be addressed at a higher abstraction level, such as a standalone OGC Building Block or a separate API profile. We argue that the STAC Datacube Extension is the correct integration point for three reasons. First, the GeoDataCube SWG charter explicitly adopts STAC `cube:dimensions` as its metadata model; any solution not expressed in that schema requires consumers to reconcile two independent dimension metadata sources. Second, the properties we add (`size`, `href`, `generator`, `hierarchy`) are strictly optional and backwards-compatible: existing clients and validators ignore unknown properties per JSON processing rules, so the extension imposes zero cost on implementations that do not need it. Third, the STAC community extension ecosystem already provides a proven governance model for domain-specific additions (e.g., `eo`, `sar`, `pointcloud`), with clear promotion paths from community extension to official extension. A standalone profile would require separate discovery, separate tooling, and separate governance -- precisely the fragmentation that the GDC SWG was created to reduce.

## 7. Discussion

The generator pattern addresses a genuine gap confirmed by OGC's own testbed program. The approach is deliberately minimal: three new properties on an existing schema, each optional and backwards-compatible. Existing clients and servers are unaffected. Adoption can be incremental -- a server might initially support only `size` and `href` (pagination without generation), then add generators for specific dimension types as needed.

The decision to use JSON Schema 2020-12 for both `parameters` and `output` fields avoids introducing a new type system. OpenAPI specifications already use JSON Schema internally, creating a natural alignment between the generator metadata in collection descriptions and the actual API contracts of generator endpoints.

The conformance level hierarchy provides a clear adoption path. Most implementations will need only Basic (pagination) and Invertible (validation). Searchable adds significant value for large non-temporal dimensions. The Similarity level documents an architectural possibility without imposing requirements, allowing the specification to evolve as AI/ML integration with geospatial standards matures.

The reference implementation has been deployed on the FAO Agro-Informatics Platform review environment, where it serves as a Dynastore extension alongside production STAC catalog services. This deployment validates the integration model: the generator API operates behind a reverse proxy with path prefixes, demonstrating that the HATEOAS link generation and pagination mechanics work correctly in a real infrastructure environment with TLS termination and path-based routing.

A limitation of this work is that the similarity-driven navigation concept remains theoretical. While the architectural extension points are well-defined, production-scale validation of vector search across datacube dimensions requires further research and implementation experience. We intentionally document this as future work rather than normative specification. Similarly, capabilities for embedding dimension members into vector spaces (`/embed`) and projecting between dimension coordinate systems (`/project`) represent natural extensions to the generator protocol but lack concrete production use cases at this time; they are noted as directions for future specification work rather than included in any conformance level.

The hierarchical dimension extension opens a pathway toward formal alignment with established vocabulary standards. SKOS concept schemes such as AGROVOC and GEMET, and SDMX hierarchical codelists maintained by statistical offices, could be exposed as hierarchical dimension generators through adaptor implementations that bridge their RDF or structural metadata APIs to the `/children` and `/ancestors` endpoint contract defined here. Such alignment would allow STAC clients to navigate FAO agricultural ontologies and national statistical classifications using the same protocol as administrative boundary trees, without any change to the client code.

## 8. Conclusion

We have presented a backwards-compatible extension to the STAC Datacube dimension model that addresses three fundamental gaps in current geospatial metadata standards. The first is scalable pagination of dimension members via `size` and `href`, resolving the practical impossibility of embedding thousands of dimension values in collection metadata. The second is algorithmic generation of deterministic dimensions via the `generator` object, enabling both server-side API access and client-side computation from machine-discoverable OpenAPI definitions. The third is formal invertibility for dimension integrity enforcement: invertible generators define a total surjective function from any domain value to exactly one dimension member, enabling ingestion validation, cross-collection consistency, and ETL quality monitoring through the `/inverse` endpoint.

Beyond the core three properties, we have introduced two additional contributions. The `hierarchy` property with recursive and leveled strategies extends the model to tree-structured nominal and ordinal dimensions, providing a standard REST interface for progressive tree navigation that is aligned with the STAC API Children Extension and directly applicable to administrative boundary datasets, statistical indicator catalogs, and species classification systems. Two new dimension types, `nominal` and `ordinal`, improve expressiveness beyond the existing `other` fallback.

The approach is validated through a reference implementation of six generator types deployed as twelve named dimensions on the FAO Agro-Informatics Platform, demonstrating all five conformance levels across six operationally motivated use cases: calendar interoperability between competing pentadal systems, recursive indicator hierarchies, leveled administrative boundary navigation, forestry species search, elevation band integrity, and cross-collection temporal alignment. The specification, JSON Schema, and reference implementation are available as open-source artifacts at https://github.com/ccancellieri/ogc-dimensions under the Apache-2.0 license, and are designed to support the OGC GeoDataCube Standards Working Group and the STAC community extension ecosystem.

## References

1. Radiant Earth Foundation. SpatioTemporal Asset Catalog Specification. https://github.com/radiantearth/stac-spec

2. STAC Datacube Extension v2.2.0. https://github.com/stac-extensions/datacube

3. OGC. STAC as OGC Community Standard, October 2025. OGC docs 25-004, 25-005. https://docs.ogc.org/cs/25-004/25-004.html

4. OGC. Testbed 19 GeoDataCubes Engineering Report. OGC doc 23-047. https://docs.ogc.org/per/23-047.html

5. OGC. Testbed 19 Draft API -- GeoDataCubes. OGC doc 23-048. https://docs.ogc.org/per/23-048.html

6. OGC. Testbed 20 GDC API Profile Report. OGC doc 24-035. https://docs.ogc.org/per/24-035.html

7. OGC. GeoDataCube Standards Working Group, formed January 2025. https://www.ogc.org/press-release/ogc-forms-new-geodatacube-standards-working-group/

8. OGC. OGC API - Common Part 2: Geospatial Data. OGC doc 20-024. https://docs.ogc.org/is/20-024/20-024.html

9. SDMX Technical Working Group. SDMX 3.0 Information Model. https://sdmx.org/wp-content/uploads/SDMX_3-0-0_SECTION_2_FINAL-1_0.pdf

10. JSON Schema. JSON Schema 2020-12 Core Specification. https://json-schema.org/draft/2020-12/json-schema-core

11. OpenAPI Initiative. OpenAPI Specification 3.1.0. https://spec.openapis.org/oas/v3.1.0

12. Paulik, C. et al. cadati: Calendar date utilities for dekadal date arithmetic. https://github.com/TUW-GEO/cadati

13. FAO. Agricultural Stress Index System (ASIS). https://www.fao.org/giews/earthobservation/

14. Funk, C. et al. (2015). The climate hazards infrared precipitation with stations -- a new environmental record for monitoring extremes. Scientific Data, 2, 150066.

15. OGC. Temporal WKT for Calendars SWG. https://external.ogc.org/twiki_public/TemporalDWG/TemporalSWG

16. OGC. Naming Authority Policies and Procedures. OGC doc 09-046r6. https://docs.ogc.org/pol/09-046r6.html

17. OGC. Testbed 17: Geo Data Cube API Engineering Report. OGC doc 21-027. https://docs.ogc.org/per/21-027.html

18. OGC. Testbed 16: Data Access and Processing Engineering Report. OGC doc 20-016. https://docs.ogc.org/per/20-016.html

19. OGC. Testbed 16: Data Access and Processing API Engineering Report. OGC doc 20-025r1. Editor: Panagiotis (Peter) A. Vretanos. https://docs.ogc.org/per/20-025r1.html

20. OGC. GeoDataCube Standard Working Group Charter. OGC doc 22-052. Authors: Claudio Iacopino, Ingo Simonis, Stephan Meißl. Approved 2023-05-03.

21. OGC. Testbed 20 GDC Usability Testing Report. OGC doc 24-037. https://docs.ogc.org/per/24-037.html

22. Iacopino, C. et al. (2023). Introduction to the OGC Geodatacube Standard Working Group. IEEE International Geoscience and Remote Sensing Symposium (IGARSS). https://ieeexplore.ieee.org/document/10282998

23. Cancellieri, C. (2026). OGC Dimensions: Reference Implementation. https://github.com/ccancellieri/ogc-dimensions

24. W3C. RDF Data Cube Vocabulary. https://www.w3.org/TR/vocab-data-cube/

25. OGC. OGC API - Environmental Data Retrieval. OGC doc 19-086r6. https://docs.ogc.org/is/19-086r6/19-086r6.html

26. Miles, A. and Bechhofer, S. SKOS Simple Knowledge Organization System Reference. W3C Recommendation, August 2009. https://www.w3.org/TR/skos-reference/

27. STAC API Extensions Contributors. STAC API Children Extension. https://github.com/stac-api-extensions/children

28. FAO. Global Administrative Unit Layers (GAUL). https://www.fao.org/geonetwork/srv/en/metadata.show?id=12691

29. FAO. AGROVOC Multilingual Thesaurus. https://www.fao.org/agrovoc/

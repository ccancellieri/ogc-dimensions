# Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes

**Carlo Cancellieri**
Food and Agriculture Organization of the United Nations (FAO), Rome, Italy
OGC Member

## Abstract

Geospatial datacubes organize Earth observation, climate, and socioeconomic data along multiple dimensions -- spatial coordinates, time, spectral bands, and thematic indicators. Standards such as the STAC Datacube Extension, OGC API - Coverages, and openEO define dimension metadata as inline arrays embedded in collection descriptions. This approach works for dimensions with tens to hundreds of members but becomes impractical when dimensions scale to thousands or millions of values, as commonly occurs in agricultural monitoring systems, long-duration climate records, and statistical indicator catalogs.

This paper identifies three fundamental gaps in current OGC and STAC standards: (1) no pagination mechanism for dimension member arrays, (2) no algorithmic generation rules for deterministic dimensions such as non-Gregorian calendars, and (3) no formal inversion mechanism to validate data against dimension definitions at ingestion time. We present a backwards-compatible extension to the STAC Datacube specification introducing three new properties: `size` and `values_href` for paginated access following OGC API - Common conventions, and a `generator` object that encapsulates algorithmic member generation with machine-discoverable OpenAPI definitions.

The generator abstraction is not limited to temporal dimensions. It applies uniformly to any dimension type -- temporal calendars (dekadal, pentadal, ISO week), spatial grid indices, integer ranges, and coded hierarchies. For hierarchical dimensions such as administrative boundary trees and statistical indicator catalogs, we extend the model with a `hierarchy` property supporting two strategies: recursive (each member carries a parent reference) and leveled (hierarchy imposed by named level definitions). We additionally propose two new dimension types, `nominal` and `ordinal`, to express coded dimensions more precisely than the existing `other` fallback. Each generator exposes capabilities through a standard OpenAPI interface: paginated generation, extent computation, optional inverse mapping for bijective generators, optional search across multiple protocols including vector similarity, and optional hierarchical navigation via dedicated `/children` and `/ancestors` endpoints. We define five conformance levels (Basic, Invertible, Searchable, Hierarchical, Similarity) that allow incremental adoption from simple pagination to hierarchical vocabulary navigation.

We validate the approach through a reference implementation demonstrating dekadal, pentadal, integer-range, and hierarchical static-tree generators with full pagination, inverse mapping, search capabilities, and hierarchical navigation. The reference implementation is available as open-source software alongside the formal JSON Schema specification and worked examples for common use cases in agricultural drought monitoring, food security early warning, and administrative boundary management.

## 1. Introduction

The proliferation of analysis-ready geospatial data has driven the adoption of datacube abstractions across Earth observation, climate science, and agricultural monitoring. A datacube organizes data along named dimensions -- typically two spatial axes, a temporal axis, and one or more thematic axes (spectral bands, statistical indicators, administrative units). Metadata standards describe these dimensions so that clients can discover, subset, and process cube contents without downloading entire datasets.

The SpatioTemporal Asset Catalog (STAC) has emerged as the dominant metadata standard for cloud-native geospatial data, adopted as an OGC Community Standard in October 2025 (OGC docs 25-004, 25-005). The STAC Datacube Extension (v2.2.0+) adds `cube:dimensions` to collection metadata, defining each dimension's type, extent, step interval, and an optional `values` array enumerating all discrete members. The OGC GeoDataCube API profile, developed through Testbed 19 (doc 23-047) and Testbed 20 (doc 24-035), builds on this same STAC dimension model.

This inline enumeration works well for small dimensions -- a Sentinel-2 collection has 13 spectral bands, a climate ensemble might have 50 members. However, the approach fails when dimensions scale beyond what is practical to embed in a JSON document. Real-world examples abound: the FAO Agricultural Stress Index System (ASIS) catalogs data across 36 dekadal periods per year spanning multiple decades; the FAO FAOSTAT database contains over 10,000 statistical indicators; national statistical offices publish data across 50,000+ administrative boundary units at sub-national levels. A daily time series from 2000 to 2025 alone produces 9,131 dimension values.

The problem is compounded by the existence of non-Gregorian temporal systems that resist standard encoding. The dekadal calendar, used globally in agricultural drought monitoring and food security early warning, divides each month into three periods (days 1-10, 11-20, and 21 to month-end), producing 36 periods per year with variable-length third periods. Two distinct pentadal systems exist: a month-based variant (72 periods/year, used by CHIRPS, CDT, and FAO) and a year-based variant (73 periods/year, used by GPCP and CPC/NOAA). Neither system can be expressed as an ISO 8601 duration, and setting `step: null` to signal irregular spacing provides no mechanism to enumerate the actual members.

OGC Testbed 19 (doc 23-047) and Testbed 20 (doc 24-035) both explicitly identified these limitations. The Testbed 19 GeoDataCubes Engineering Report notes that "pagination is rarely used in openEO implementations" for dimension metadata, while simultaneously acknowledging that dimension value arrays can grow unboundedly. The European Centre for Medium-Range Weather Forecasts (ECMWF), participating in Testbed 19, specifically requested support for "irregular or sparse data content" -- a request acknowledged but not resolved by the testbed specification.

No existing standard addresses these gaps comprehensively. SDMX 3.0 provides structural decoupling through codelists but offers no pagination on structure endpoints. OGC API - Environmental Data Retrieval (EDR) supports custom dimension parameters but provides no mechanism for large-scale enumeration or algorithmic generation. The RDF Data Cube Vocabulary encodes dimension members as URIs in SKOS concept schemes but operates at a different architectural level than RESTful collection metadata.

This paper presents a unified solution through three backwards-compatible additions to the STAC Datacube dimension model:

1. **Paginated access** via `size` (member count) and `values_href` (link to a paginated endpoint) following OGC API - Common Part 2 conventions.

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

## 3. Specification

### 3.1 Paginated Dimension Members

We propose two new properties on the STAC Datacube Extension dimension object:

**`size`** (integer, RECOMMENDED): The total number of discrete members in the dimension. This allows clients to assess cardinality without downloading any values. The property aligns with the existing community request in STAC Datacube Extension issue #31.

**`values_href`** (string, URI, OPTIONAL): A link to a paginated endpoint returning dimension values. When present, the `values` array MAY be omitted. The endpoint follows OGC API - Common Part 2 pagination conventions with `limit` and `offset` query parameters. Responses include `numberMatched` and `numberReturned` fields following the OGC API - Features convention, and `rel:next`/`rel:prev` link relations per RFC 5988.

Both properties are backwards-compatible additions. Existing clients that read only the `values` array continue to work for small dimensions. Servers may provide inline `values` for dimensions below an implementation-defined threshold (recommended: 1000 members) while using `values_href` for larger dimensions.

A paginated response follows OGC API - Features conventions:

```json
{
  "dimension": "dekadal",
  "numberMatched": 900,
  "numberReturned": 5,
  "values": ["2024-K01", "2024-K02", "2024-K03", "2024-K04", "2024-K05"],
  "links": [
    {"rel": "self",  "href": ".../generate?limit=5&offset=0"},
    {"rel": "next",  "href": ".../generate?limit=5&offset=5"}
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

- **`bijective`** (boolean, OPTIONAL, default false): Whether the generator supports inverse operations. See Section 3.3.

- **`search`** (array of strings, OPTIONAL): Supported search protocols (`exact`, `range`, `like`, `vector`).

- **`on_invalid`** (string, OPTIONAL): Item ingestion behavior when inverse validation fails (`reject`, `accept`, `warn`).

- **`hierarchical`** (boolean, OPTIONAL, default false): Whether the generator supports Hierarchical conformance level -- `/children`, `/ancestors`, and the `?parent=` filter on `/generate`. This property should be `true` when the dimension declares a `hierarchy` property. See Section 3.6.

Each generator's OpenAPI specification exposes up to four capabilities: `/generate` for paginated member production, `/extent` for boundary computation, `/search` for query-based member discovery, and `/inverse` for value-to-coordinate mapping. The `/generate` endpoint is unified with `values_href` -- both point to the same paginated interface.

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
        "bijective": true,
        "search": ["exact", "range", "like"],
        "on_invalid": "reject"
      },
      "step": "1K",
      "unit": "dekad",
      "size": 900,
      "values_href": ".../dimensions/dekadal/generate?limit=100"
    }
  }
}
```

Legacy clients that do not recognize `generator`, `size`, or `values_href` ignore these properties per standard JSON processing rules. Clients that do recognize `values_href` can follow it to retrieve paginated members without any knowledge of the generation algorithm. For example, a legacy client requesting `?format=datetime` receives standard ISO dates (`["2024-01-01", "2024-01-11", "2024-01-21", ...]`) -- a valid irregular temporal dimension indistinguishable from a traditional `values` array. Generator-aware clients can additionally use `/inverse`, `/search`, and native format negotiation.

### 3.3 Generator Bijectivity and Dimension Integrity

A generator defines a forward function from parameter space to value space. When a generator is bijective (or more precisely, surjective with deterministic totality), it also defines an inverse function: given an arbitrary value, compute which dimension member it belongs to and its coordinates in parameter space.

For example, the dekadal generator's inverse maps any date to its enclosing dekad:

```
GET /dimensions/dekadal/inverse?value=2024-01-15
→ {"valid": true, "member": "2024-K02",
   "range": {"start": "2024-01-11", "end": "2024-01-20"}}

GET /dimensions/dekadal/inverse?value=2024-01-32
→ {"valid": false, "reason": "Cannot parse '2024-01-32' as a date."}
```

The inverse function serves three purposes in datacube management:

1. **Ingestion validation**: When a new item is inserted, the system can verify that its dimension values map to valid members. The `on_invalid` policy determines behavior for values outside the dimension's domain: `reject` returns an error (strict referential integrity), `accept` allows the dimension to grow (schema-on-read), and `warn` accepts the item while flagging the anomaly.

2. **Cross-collection consistency**: Multiple collections sharing the same temporal dimension (e.g., NDVI and precipitation, both dekadal) are guaranteed to have aligned coordinates when validated by the same generator.

3. **Data quality metrics**: The ratio of valid to invalid inverse results across a data pipeline is itself a quality metric, measuring what percentage of incoming observations map to valid dimension coordinates.

The inverse operation maps naturally to data engineering concepts: it is analogous to a partitioning function (Hive, Iceberg, Delta Lake), a referential integrity check (foreign key constraints), and a quantization function (information theory). For bijective generators, the `/inverse` endpoint supports both single-value queries (GET) and batch operations (POST) for efficient pipeline processing.

### 3.4 Search and Similarity

Generators may optionally expose a search capability supporting multiple protocols. Deterministic protocols (`exact`, `range`, `like`) enable traditional filtering on generated or stored dimension members. The `vector` protocol opens an architectural pathway to AI-powered dimension navigation: when dimension members are associated with embedding vectors, clients can search by similarity rather than exact coordinates, effectively navigating the datacube by concept proximity.

This positions STAC collections as approximate multidimensional vector indices. Each dimension with a searchable generator contributes one axis of a multi-dimensional index. A client searching across N dimensions receives items ranked by combined similarity across all axes -- a fundamentally different access pattern from traditional exact-coordinate subsetting.

### 3.5 Conformance Levels

We define five conformance levels as an additive hierarchy:

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | /generate + /extent | MUST support |
| Invertible | + /inverse | Bijective generators only |
| Searchable | + /search (exact, range, like) | SHOULD support |
| Hierarchical | + /children + /ancestors + ?parent= filter | Required when hierarchy is declared |
| Similarity | + /search (vector) | MAY support; future work |

Basic constitutes the minimum requirement for any generator implementation. Invertible applies specifically to bijective generators such as temporal calendars and integer ranges, for which the inverse function is deterministic; its concrete use cases are ingestion validation (rejecting items whose dimension values map to no valid member), cross-collection consistency (guaranteeing that collections sharing the same generator type use identical temporal coordinates), and data quality monitoring (tracking the ratio of valid to invalid inverse results across an ETL pipeline). Searchable is recommended for any non-trivial dimension. Hierarchical is required when the dimension declares a `hierarchy` property and is orthogonal to Invertible -- a hierarchical nominal dimension may independently be bijective if its member codes are canonical identifiers (for example, ISO 3166-1 alpha-3 country codes). Similarity documents the architectural runway toward embedding-based dimension navigation without imposing immediate implementation requirements.

### 3.6 Hierarchical Dimension Members

Many dimension types in geospatial datacubes are inherently hierarchical. Administrative boundaries follow a well-defined tree: countries subdivide into regions, regions into districts, districts into localities. The FAO Global Administrative Unit Layers (GAUL) organizes 195 countries into 3,469 first-level administrative units and 46,031 second-level units across three hierarchy levels. Statistical indicator catalogs are similarly organized: the FAO FAOSTAT database groups over 10,000 indicators into domains, groups, and subgroups across four levels. Land cover classifications, OGC feature type hierarchies, and SDMX-coded dimensions exhibit comparable structures. For dimensions of this kind, enumeration via a flat `values` array or a single `values_href` is insufficient -- clients must navigate the tree to discover relevant members, and embedding the entire hierarchy in a single paginated stream discards structural information that enables efficient subsetting and display.

We introduce a `hierarchy` property on the dimension object that describes the tree structure and the strategy used to encode it. Two strategies are defined. The recursive strategy is used when the hierarchy is encoded directly inside the data: each member's generator output includes a field whose value is the code of its parent, or null for root members. This mirrors the semantics of W3C SKOS `skos:broader`, where each concept declares its broader (parent) concept. Clients navigate the tree by requesting root members (those whose parent field is null) and then following `/children` links for each node of interest. For the FAOSTAT indicator tree, a generator output object carries a `parent_code` field typed as `string | null`, and the `hierarchy.parent_property` field names this field so that clients and servers can identify it without prior knowledge of the domain-specific schema.

The leveled strategy is used when the hierarchy is not encoded in the data itself but is imposed by named level definitions. This pattern arises when the underlying data store is a flat table with multiple columns representing different hierarchical levels: a row might carry `iso_code`, `adm1_code`, and `adm2_code` simultaneously, and the tree structure is derived by grouping rows by level rather than read from a parent reference field. Each level in the `levels` array specifies: `id` (a unique level identifier), `label` (a human-readable name), `parent_level` (the `id` of the parent level, absent on the root), `member_id_property` (which output field uniquely identifies members at this level), `parent_id_property` (which output field identifies the parent member at the parent level), and a `parameters` object encoding the generator parameters needed to filter members to this level. The `parameters` object is the backend-agnostic generalization of a SQL `WHERE` clause or CQL filter: the implementation details of how the filter is applied remain inside the generator, while the specification exposes only the parameter values. This design generalizes the operational experience of the geoid system, in which hierarchy rules encode SQL conditions per level alongside `item_code_field` and `parent_code_field` column mappings.

Two generator endpoints implement tree navigation at the Hierarchical conformance level. The `GET /{dimension_id}/children?parent=X` endpoint returns the direct children of member X, using the same pagination envelope (`numberMatched`, `numberReturned`, `links`) as the `/generate` endpoint. The response additionally includes the parent code and a `rel:parent` link relation pointing to the parent member, mirroring the STAC API Children Extension's link relation conventions. The `GET /{dimension_id}/ancestors?member=X` endpoint returns the complete ancestor chain from root to member X inclusive, ordered from coarsest to finest granularity. For backwards compatibility, the existing `/generate` endpoint accepts an optional `?parent=X` query parameter as an alias for `/children?parent=X`, allowing clients that already use `values_href` for pagination to navigate the hierarchy without learning a new endpoint pattern.

The distinction between the two navigation endpoints reflects distinct client use cases. A mapping application rendering a country selector first calls `/children` with no parent (obtaining root members) to populate a continent dropdown, then calls `/children?parent=Africa` on user selection to populate a country dropdown. A data pipeline that receives an incoming observation labeled with a sub-national code calls `/ancestors?member=ETH-TIG` to resolve the full administrative path, validating the code against the dimension hierarchy and obtaining the ancestor codes needed for regional aggregation. Both operations are analogous to standard tree operations in relational systems (adjacency list queries) and graph databases (breadth-first traversal), expressed as a RESTful paginated API that requires no query language.

The STAC Datacube Extension currently defines dimension types as `spatial`, `temporal`, `bands`, and `other`. Administrative boundaries, indicator codes, land cover classes, and similar dimensions fall into `other` by default, which provides no semantic information. We propose two new type values: `nominal` for unordered coded dimensions whose members are named categories without inherent rank (administrative units, indicator codes, species classifications), and `ordinal` for ordered coded dimensions whose members have an inherent rank or severity order (quality flags, data confidence levels, hazard severity classes). Both terms are established in statistical taxonomy and dimensional analytics, are already used in the geoid system's `DatacubeDimensionType` enumeration, and are backwards-compatible additions -- implementations that do not recognise `nominal` or `ordinal` treat them as unknown type values and continue processing the dimension using its other standard properties.

The Hierarchical conformance level is orthogonal to all other conformance levels. A generator that declares `hierarchical: true` exposes `/children`, `/ancestors`, and the `?parent=` filter; it may independently be bijective (declaring `bijective: true` to also expose `/inverse`), searchable, or both. The world-admin demo dimension in the reference implementation illustrates this independence: the static tree generator is hierarchical and searchable but not bijective, because continent and country codes are not deterministically derivable from spatial coordinates without additional metadata. A dimension of ISO 3166-1 alpha-3 country codes with a lookup-table generator would be both hierarchical and bijective if the lookup function is surjective.

## 4. Implementation and Validation

### 4.1 Reference Implementation

We provide an open-source reference implementation as a Python package (`ogc-dimensions`) with a FastAPI REST API. The source code, JSON Schema specification, and worked examples are available at https://github.com/ccancellieri/ogc-dimensions under the Apache-2.0 license.

A live deployment is available on the FAO Agro-Informatics Platform review environment, integrated as an extension of the GeoID catalog platform (https://github.com/un-fao/geoid). The deployment demonstrates all generator endpoints with full pagination, inverse mapping, and search capabilities. The Swagger UI is accessible at https://data.review.fao.org/geospatial/v2/api/tools/docs, and the `values_href` links in the worked examples point directly to these live endpoints.

The implementation includes five generator types:

- **DekadalGenerator**: 36 periods/year, bijective, searchable (exact, range, like)
- **PentadalMonthlyGenerator**: 72 periods/year (CHIRPS/FAO variant), bijective, searchable
- **PentadalAnnualGenerator**: 73 periods/year (GPCP/NOAA variant), bijective, searchable
- **IntegerRangeGenerator**: configurable step, bijective, searchable (exact, range)
- **StaticTreeGenerator**: in-memory hierarchical tree (5 continents, 49 countries); Hierarchical and Searchable conformance; not bijective

The temporal and integer-range generators implement the Basic, Invertible, and Searchable conformance levels. The `StaticTreeGenerator` implements the Basic, Searchable, and Hierarchical conformance levels, exposing the `world-admin` demo dimension with `/children`, `/ancestors`, and `?parent=` filter endpoints. Querying `GET /dimensions/world-admin/generate` returns the five root continents; `GET /dimensions/world-admin/children?parent=Africa` returns the 13 African countries in the dataset; `GET /dimensions/world-admin/ancestors?member=ETH` returns the chain `[{code: "Africa", level: 0}, {code: "ETH", level: 1}]`.

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

Paginated generation enables constant-memory serving of arbitrarily large dimensions. A dekadal dimension spanning 100 years (3,600 members) is served in 36 pages of 100 members each, with each page generated in constant time through the deterministic algorithm. No database query or pre-materialized array is required.

Batch inverse operations process lists of values in a single HTTP request, enabling efficient ETL pipeline integration. The inverse computation for temporal generators is O(1) per value (direct arithmetic from date components), making batch processing of millions of records practical.

## 5. Use Cases

### 5.1 FAO Agricultural Drought Monitoring

The FAO ASIS system monitors agricultural drought using dekadal NDVI composites, precipitation estimates, and soil moisture indicators. The system currently maintains a proprietary dimension API with paginated access. Adopting the generator specification would replace this custom implementation with a standards-compliant interface, enabling interoperability with any STAC-compliant client.

A CHIRPS dekadal precipitation collection spanning 2000-2025 would declare a temporal dimension with `generator.type: "dekadal"`, `size: 900`, and `values_href` pointing to the generator's paginated endpoint. Legacy clients hitting `values_href` would receive standard ISO date strings, while advanced clients could use the native dekadal notation and inverse mapping for coordinate computation.

### 5.2 Large Indicator Catalogs

FAO maintains statistical indicator catalogs with over 10,000 codes spanning agriculture, nutrition, trade, and environmental domains. These indicators serve as dimension members in datacubes combining geospatial layers with statistical data. Without pagination, embedding 10,000 indicator codes in collection metadata is impractical and degrades API performance.

With `values_href`, clients retrieve indicator codes incrementally with filtering support (`?filter=wheat*`). A non-bijective generator with `on_invalid: "accept"` allows the indicator dimension to grow as new codes are introduced, modeling the real-world evolution of statistical classification systems.

### 5.3 Administrative Boundary Dimensions

National and sub-national administrative boundaries represent one of the most widespread hierarchical dimensions in geospatial datacubes. Food security analyses at FAO, for example, require subsetting datasets to country, region, or district level -- operations that presuppose a navigable administrative hierarchy in the dimension metadata. With the GAUL dataset organized as three levels (195 countries, 3,469 ADM1 units, 46,031 ADM2 districts), encoding all 50,000+ administrative codes in a flat `values` array is impractical. The leveled hierarchy strategy encodes this structure efficiently: the dimension metadata declares three levels with `member_id_property`, `parent_id_property`, and level-specific `values_href` endpoints. A client application building a geographic filter begins by fetching `/generate` (root countries), then navigating to `/children?parent=ETH` (Ethiopian ADM1 regions) and `/children?parent=ETH-TIG` (Tigray districts) in response to user selections. Each step retrieves only the members needed, keeping page sizes small and response times predictable regardless of total administrative unit count.

### 5.4 FAO FAOSTAT Indicator Tree

The FAO FAOSTAT database organizes over 10,000 statistical indicators into a four-level recursive hierarchy: domain (12 top-level areas such as Food Security and Production), group (28 thematic groups), indicator (approximately 900 named measures), and sub-indicator (individual time series variants). Prior to the generator approach, making this classification system available as dimension metadata required either a monolithic response listing all 10,000+ codes or a custom API that clients had to learn independently. The recursive hierarchy strategy provides a standard solution: the indicator dimension declares `hierarchy.strategy: "recursive"` with `parent_property: "parent_code"`, and the generator output schema declares `parent_code` as a nullable string field. Clients begin at the root by calling `GET /dimensions/faostat-indicators/generate`, which returns the 12 top-level domains with `parent_code: null`. Following `GET /dimensions/faostat-indicators/children?parent=QC` returns the 28 child indicators of the Food Security domain, paginated at any client-chosen page size. The `/ancestors?member=QC001` endpoint resolves the full path for any indicator code, enabling breadcrumb navigation and regional drill-down in analytical applications. The depth field in the hierarchy metadata (`depth: 4`) informs clients of the maximum tree depth without requiring them to discover it through traversal.

### 5.5 Cross-Collection Temporal Alignment

Multiple collections sharing the same temporal cadence (e.g., NDVI, precipitation, and soil moisture, all dekadal) can reference the same generator type. The bijective inverse guarantees that all collections use identical temporal coordinates, preventing alignment errors that arise when different systems independently compute period boundaries.

## 6. Standardization Pathway

We propose a phased approach to standardization:

1. **Community publication**: This paper and the companion GitHub repository (specification, reference implementation, worked examples) serve as the initial community contribution.

2. **STAC Community Extension**: Submit JSON Schema changes (`size`, `values_href`, `generator`) to `stac-extensions/datacube`, referencing Testbed 19/20 findings.

3. **OGC GeoDataCube SWG**: Submit as a Change Request Proposal to the GeoDataCube specification, proposing `generator` as a new conformance class.

4. **OGC Naming Authority**: Register generator algorithm definitions (dekadal, pentadal-monthly, pentadal-annual) as OGC Definition URIs with SKOS RDF descriptions.

5. **OGC Innovation Program**: Propose "Scalable Dimension Members" as a thread topic for a future OGC Testbed, with the reference implementation as a testbed component.

## 7. Discussion

The generator pattern addresses a genuine gap confirmed by OGC's own testbed program. The approach is deliberately minimal: three new properties on an existing schema, each optional and backwards-compatible. Existing clients and servers are unaffected. Adoption can be incremental -- a server might initially support only `size` and `values_href` (pagination without generation), then add generators for specific dimension types as needed.

The decision to use JSON Schema 2020-12 for both `parameters` and `output` fields avoids introducing a new type system. OpenAPI specifications already use JSON Schema internally, creating a natural alignment between the generator metadata in collection descriptions and the actual API contracts of generator endpoints.

The conformance level hierarchy provides a clear adoption path. Most implementations will need only Basic (pagination) and Invertible (validation). Searchable adds significant value for large non-temporal dimensions. Similarity and Intelligent levels document architectural possibilities without imposing requirements, allowing the specification to evolve as AI/ML integration with geospatial standards matures.

The reference implementation has been deployed on the FAO Agro-Informatics Platform review environment, where it serves as a Dynastore extension alongside production STAC catalog services. This deployment validates the integration model: the generator API operates behind a reverse proxy with path prefixes, demonstrating that the HATEOAS link generation and pagination mechanics work correctly in a real infrastructure environment with TLS termination and path-based routing.

A limitation of this work is that the similarity-driven navigation concept remains theoretical. While the architectural extension points are well-defined, production-scale validation of vector search across datacube dimensions requires further research and implementation experience. We intentionally document this as future work rather than normative specification. Similarly, capabilities for embedding dimension members into vector spaces (`/embed`) and projecting between dimension coordinate systems (`/project`) represent natural extensions to the generator protocol but lack concrete production use cases at this time; they are noted as directions for future specification work rather than included in any conformance level.

The hierarchical dimension extension opens a pathway toward formal alignment with established vocabulary standards. SKOS concept schemes such as AGROVOC and GEMET, and SDMX hierarchical codelists maintained by statistical offices, could be exposed as hierarchical dimension generators through adaptor implementations that bridge their RDF or structural metadata APIs to the `/children` and `/ancestors` endpoint contract defined here. Such alignment would allow STAC clients to navigate FAO agricultural ontologies and national statistical classifications using the same protocol as administrative boundary trees, without any change to the client code.

## 8. Conclusion

We have presented a backwards-compatible extension to the STAC Datacube dimension model that addresses three fundamental gaps in current geospatial metadata standards: scalable pagination of dimension members, algorithmic generation of deterministic dimensions, and formal inversion for dimension integrity enforcement. The generator abstraction applies uniformly across dimension types and is validated through a reference implementation covering dekadal, pentadal, and integer-range generators with full pagination, inverse mapping, and search capabilities.

The specification is available as open-source JSON Schema with worked examples. The reference implementation demonstrates the complete generator API as a FastAPI application. Both artifacts are designed to support the OGC standardization process through the GeoDataCube Standards Working Group and the STAC community extension ecosystem.

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

28. Food and Agriculture Organization of the United Nations. AGROVOC Multilingual Thesaurus. https://agrovoc.fao.org/

# Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes

**Carlo Cancellieri**
Food and Agriculture Organization of the United Nations (FAO), Rome, Italy
OGC Member

## Abstract

Geospatial datacubes organize Earth observation, climate, and socioeconomic data along multiple dimensions -- spatial coordinates, time, spectral bands, and thematic indicators. Standards such as the STAC Datacube Extension, OGC API - Coverages, and openEO define dimension metadata as inline arrays embedded in collection descriptions. This approach works for dimensions with tens to hundreds of members but becomes impractical when dimensions scale to thousands or millions of values, as commonly occurs in agricultural monitoring systems, long-duration climate records, and statistical indicator catalogs.

This paper identifies three fundamental gaps in current OGC and STAC standards: (1) no pagination mechanism for dimension member arrays, (2) no algorithmic generation rules for deterministic dimensions such as non-Gregorian calendars, and (3) no formal inversion mechanism to validate data against dimension definitions at ingestion time. We present a backwards-compatible extension to the STAC Datacube specification introducing three new properties: `size` and `values_href` for paginated access following OGC API - Common conventions, and a `generator` object that encapsulates algorithmic member generation with machine-discoverable OpenAPI definitions.

The generator abstraction is not limited to temporal dimensions. It applies uniformly to any dimension type -- temporal calendars (dekadal, pentadal, ISO week), spatial grid indices, integer ranges, and coded hierarchies. Each generator exposes capabilities through a standard OpenAPI interface: paginated generation, extent computation, optional inverse mapping for bijective generators, and optional search across multiple protocols including vector similarity. We define five conformance levels (Basic, Invertible, Searchable, Similarity, Intelligent) that allow incremental adoption from simple pagination to AI-powered dimension navigation.

We validate the approach through a reference implementation demonstrating dekadal, pentadal, and integer-range generators with full pagination, inverse mapping, and search capabilities. The reference implementation is available as open-source software alongside the formal JSON Schema specification and worked examples for common use cases in agricultural drought monitoring and food security early warning systems.

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

The GeoDataCube API, developed through OGC Testbed 17-20, defines a profile layering datacube semantics onto OGC API - Coverages. It adopts STAC `cube:dimensions` verbatim for dimension description. The Testbed 19 Engineering Report (doc 23-047) documents the API architecture and identifies several open gaps directly relevant to this work: no pagination for dimension values within collection metadata, no enumeration of irregular temporal values beyond `step: null`, and no non-Gregorian calendar support.

### 2.3 SDMX and Statistical Standards

The Statistical Data and Metadata eXchange (SDMX) 3.0 provides the most mature structural metadata model through Data Structure Definitions (DSDs) and Codelists. SDMX achieves complete decoupling of dimension structure from data payload. However, SDMX structure endpoints do not support pagination -- codelists are returned as monolithic responses. SDMX 3.0 adds GeoCodelist and GeoGridCodelist for spatial dimensions, acknowledging the need for geospatial integration, but these additions address type expressiveness rather than scalability.

### 2.4 Non-Gregorian Temporal Systems

The dekadal calendar, formally documented by the FAO and widely used in agricultural applications, divides each Gregorian month into three periods. The first dekad covers days 1-10, the second covers days 11-20, and the third covers day 21 through the end of the month. This third dekad varies from 8 days (February in non-leap years) to 11 days (months with 31 days). Two distinct pentadal systems exist: the month-based system used by CHIRPS and FAO divides each month into six 5-day periods with the sixth absorbing remaining days (26 to month-end), while the year-based system used by GPCP and CPC/NOAA counts consecutive 5-day periods from January 1, with period 73 absorbing the remaining 5 or 6 days (leap year).

No standard temporal encoding -- ISO 8601, CF conventions, or OGC temporal models -- accommodates these systems natively. ISO 8601 defines no dekad or pentad duration designator. CF conventions use `time_bnds` pairs without semantic identifiers. The cadati Python package (TU Wien, MIT license) provides reference algorithms for dekadal date arithmetic.

### 2.5 Prior Art: FAO ASIS API

The FAO Agricultural Stress Index System (ASIS) implements a proprietary dimensions API at `https://data.apps.fao.org/gismgr/api/v2/catalog`. This API provides paginated dimension listing and paginated member enumeration through a 4-level resource hierarchy (workspaces, dimensions, members, member detail). The ASIS API demonstrates the practical need for paginated dimension access in production agricultural monitoring systems. However, it uses a non-standard pagination model (page-based rather than offset-based), wraps responses in a custom envelope, and models dekadal periods as categorical ("WHAT" type) rather than temporal. The present work draws on this operational experience while aligning with OGC API conventions.

## 3. Specification

### 3.1 Paginated Dimension Members

We propose two new properties on the STAC Datacube Extension dimension object:

**`size`** (integer, RECOMMENDED): The total number of discrete members in the dimension. This allows clients to assess cardinality without downloading any values. The property aligns with the existing community request in STAC Datacube Extension issue #31.

**`values_href`** (string, URI, OPTIONAL): A link to a paginated endpoint returning dimension values. When present, the `values` array MAY be omitted. The endpoint follows OGC API - Common Part 2 pagination conventions with `limit` and `offset` query parameters. Responses include `numberMatched` and `numberReturned` fields following the OGC API - Features convention, and `rel:next`/`rel:prev` link relations per RFC 5988.

Both properties are backwards-compatible additions. Existing clients that read only the `values` array continue to work for small dimensions. Servers may provide inline `values` for dimensions below an implementation-defined threshold (recommended: 1000 members) while using `values_href` for larger dimensions.

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

Each generator's OpenAPI specification exposes up to four capabilities: `/generate` for paginated member production, `/extent` for boundary computation, `/search` for query-based member discovery, and `/inverse` for value-to-coordinate mapping. The `/generate` endpoint is unified with `values_href` -- both point to the same paginated interface.

Content negotiation through the `format` parameter enables backwards compatibility: `format=datetime` (default) produces standard ISO timestamps that legacy clients understand; `format=native` produces custom notation (e.g., `YYYY-Knn` for dekadal codes); `format=structured` produces full objects with code, start date, end date, and additional metadata.

### 3.3 Generator Bijectivity and Dimension Integrity

A generator defines a forward function from parameter space to value space. When a generator is bijective (or more precisely, surjective with deterministic totality), it also defines an inverse function: given an arbitrary value, compute which dimension member it belongs to and its coordinates in parameter space.

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
| Invertible | + /inverse | Enables ingestion validation |
| Searchable | + /search (exact, range, like) | SHOULD support |
| Similarity | + /search (vector) | MAY support |
| Intelligent | + /embed, /project | Future extension |

Basic and Invertible constitute this proposal's core scope. Searchable is recommended for non-trivial dimensions. Similarity and Intelligent document the architectural runway without requiring immediate implementation.

## 4. Implementation and Validation

### 4.1 Reference Implementation

We provide an open-source reference implementation as a Python package with a FastAPI REST API. The implementation includes four generator types:

- **DekadalGenerator**: 36 periods/year, bijective, searchable (exact, range, like)
- **PentadalMonthlyGenerator**: 72 periods/year (CHIRPS/FAO variant), bijective, searchable
- **PentadalAnnualGenerator**: 73 periods/year (GPCP/NOAA variant), bijective, searchable
- **IntegerRangeGenerator**: configurable step, bijective, searchable (exact, range)

All generators implement the Basic and Invertible conformance levels. The temporal generators additionally implement Searchable conformance with exact, range, and pattern matching protocols.

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

FAO maintains statistical indicator catalogs with over 10,000 codes spanning agriculture, nutrition, trade, and environmental domains. These indicators serve as dimension members in datacubes combining geospatial layers with statistical data. Without pagination, embedding 10,000 indicator codes in collection metadata is impractical and degrads API performance.

With `values_href`, clients retrieve indicator codes incrementally with filtering support (`?filter=wheat*`). A non-bijective generator with `on_invalid: "accept"` allows the indicator dimension to grow as new codes are introduced, modeling the real-world evolution of statistical classification systems.

### 5.3 Cross-Collection Temporal Alignment

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

A limitation of this work is that the similarity-driven navigation concept remains theoretical. While the architectural extension points are well-defined, production-scale validation of vector search across datacube dimensions requires further research and implementation experience. We intentionally document this as future work rather than normative specification.

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

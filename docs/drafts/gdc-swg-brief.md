# GDC SWG Brief / Change Request Proposal Draft

**Target:** OGC GeoDataCube Standards Working Group
**Contact:** geodatacube.swg@lists.ogc.org
**Charter:** OGC doc 22-052 (Iacopino, Simonis, Meißl)

---

## Subject

Scalable Dimension Member Dissemination and Algorithmic Generation for GeoDataCube API

## Submitter

Carlo Cancellieri, Food and Agriculture Organization of the United Nations (FAO), OGC Member

## Summary

This Change Request Proposal introduces five backwards-compatible extensions to the GeoDataCube dimension metadata model that address dimension member scalability and hierarchical vocabulary navigation -- gaps identified across OGC Testbeds 16-20 and the GDC SWG charter scope.

The proposal adds:
1. **`size`** -- dimension member count (integer, RECOMMENDED)
2. **`href`** -- link to paginated member endpoint (URI, OPTIONAL)
3. **`generator`** -- algorithmic member generation with OpenAPI discovery (object, OPTIONAL)
4. **`hierarchy`** -- tree structure for hierarchical dimensions (object, OPTIONAL); two strategies: recursive (parent reference in member data) and leveled (hierarchy imposed by named level definitions)
5. **`nominal` / `ordinal`** -- two new dimension type values for coded dimensions, more precise than the existing `other` fallback

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

Dekadal (36/year) and pentadal (72 or 73/year) calendars are used globally in agricultural drought monitoring and food security early warning. No standard temporal encoding (ISO 8601, CF conventions, OGC temporal models) accommodates these systems. The generator abstraction provides a standard mechanism to define, enumerate, and validate arbitrary temporal systems.

## Proposed conformance class

**"Dimension Generators"** -- a new conformance class for the GDC API profile.

### Conformance levels

| Level | Capabilities | Requirement |
|---|---|---|
| Basic | /generate + /extent | MUST support |
| Invertible | + /inverse | Invertible generators only |
| Searchable | + /search (exact, range, like) | SHOULD support |
| Hierarchical | + /children + /ancestors + ?parent= filter | Required when hierarchy is declared |
| Similarity | + /search (vector) | MAY support (future) |

### Generator object schema

```json
{
  "type": "dekadal",
  "api": "http://www.opengis.net/def/generator/ogc/0/dekadal/openapi.json",
  "parameters": {},
  "output": {"type": "object", "properties": {...}},
  "invertible": true,
  "search": ["exact", "range", "like"],
  "on_invalid": "reject"
}
```

Well-known generator types (`dekadal`, `pentadal-monthly`, `pentadal-annual`, `integer-range`) resolve to registered OGC Definition URIs. Custom generators provide their own OpenAPI URI.

## Alignment with SWG approach

The TB-20 pivot from standalone GDC standard to profile/integration approach directly supports this proposal:
- The generator properties are **additive extensions** to the existing STAC `cube:dimensions` model
- No existing properties are modified or removed
- Servers can adopt incrementally (size-only, then href, then generators)
- Legacy clients are unaffected (unknown properties are ignored per JSON processing rules)

## Supporting materials

- **Scientific paper:** Cancellieri, C. (2026). "Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes." https://github.com/ccancellieri/ogc-dimensions/tree/main/paper
- **JSON Schema:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/schema
- **Worked examples:** https://github.com/ccancellieri/ogc-dimensions/tree/main/spec/examples
- **Reference implementation:** https://github.com/ccancellieri/ogc-dimensions/tree/main/reference-implementation
- **Live demo (FAO):** https://data.review.fao.org/geospatial/v2/api/tools/docs

## Hierarchical Dimensions and Controlled Vocabulary Gap

A significant body of geospatial data is organized along hierarchical coded dimensions: GAUL administrative boundaries (Country → ADM1 → ADM2, ~50,000 total members), the FAO FAOSTAT indicator tree (Domain → Group → Indicator → Sub-indicator, ~10,000 members), and land cover classification hierarchies. SDMX 3.0 provides `HierarchicalCodelist` structures for statistical classifications, but SDMX structure endpoints return monolithic responses with no pagination. W3C SKOS `skos:broader`/`skos:narrower` encodes hierarchy semantics in RDF but is not accessible as paginated REST dimension metadata. The STAC API Children Extension defines `GET .../children` with `rel:children`/`rel:parent` link relations for Catalog/Collection trees -- the same endpoint contract applied one level lower to dimension member trees would close this gap.

The proposed `hierarchy` property with recursive and leveled strategies generalizes the operational experience of the FAO geoid system, in which hierarchy rules encode SQL conditions per level alongside `item_code_field` and `parent_code_field` column mappings. The `parameters` object per level is the backend-agnostic form of these SQL conditions, keeping implementation details inside the generator while exposing only the parameter values in the specification. The `/children` endpoint contract mirrors the STAC API Children Extension pagination envelope exactly, allowing clients already consuming collection trees via that extension to reuse the same traversal code for dimension member trees.

## Prior art

The FAO Agricultural Stress Index System (ASIS) has operated a proprietary paginated dimensions API since 2018, demonstrating the practical need in production agricultural monitoring. The FAO geoid catalog system implements production hierarchical dimensions with FIXED and RECURSIVE strategies, SQL-condition-based level filtering, and paginated children queries -- operational experience that directly informs this proposal. The present proposal standardizes this operational experience using OGC API conventions and aligns with the STAC API Children Extension endpoint contract.

## Requested action

1. Review the proposal at the next GDC SWG meeting
2. Consider "Dimension Generators" as a work item / conformance class for the GDC specification
3. Coordinate with the Temporal WKT SWG for calendar algorithm definitions
4. Coordinate with the OGC Naming Authority for generator type URI registration

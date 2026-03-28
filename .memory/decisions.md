# Architecture Decision Records

## 2026-03-27 Repository Structure: Mono-repo with spec + paper + testbed
Context: Need a single repo serving multiple purposes (OGC spec, scientific publication, reference implementation).
Decision: Three top-level directories: `spec/`, `paper/`, `testbed/` in a single `ogc-dimensions` repo.
Rationale: Everything versioned together -- spec change = testbed update = paper revision. Single citeable URL.

## 2026-03-27 Generator as Generalized Object (not temporal-specific)
Context: Initial design was a `calendar` property on temporal dimensions only.
Decision: Generalized `generator` object applicable to ANY dimension type (temporal, spatial, integer, coded).
Rationale: The pattern (algorithmic generation + inverse + search) applies equally to grid indices, elevation bands, and coded hierarchies.

## 2026-03-27 JSON Schema 2020-12 for parameters and output
Context: Needed a type system for generator inputs/outputs.
Decision: Use JSON Schema standard rather than inventing a custom type declaration.
Rationale: OpenAPI already uses JSON Schema internally; no reinvention, existing tooling and developer familiarity.

## 2026-03-27 Hybrid shorthand + OpenAPI URI for generator type resolution
Context: Well-known generators (dekadal) need simple declaration; custom generators need full discoverability.
Decision: Short string identifiers resolve to OGC Definition URIs; custom generators provide OpenAPI URI directly.
Rationale: Clean schema for common cases, fully extensible for custom generators.

## 2026-03-27 Standardization pathway: preprint first, then OGC formal
Context: User is OGC member wanting to standardize the proposal.
Decision: Publication -> STAC community extension -> GeoDataCube SWG -> OGC Temporal SWG + Naming Authority.
Rationale: Publication establishes date priority and is immediately citeable.

## 2026-03-28 GDC SWG Charter analysis confirms alignment
Context: Analyzed GDC SWG Charter (22-052, approved 2023-05-03, authors: Iacopino, Simonis, Meißl).
Finding: Charter mandates "definition of the GDC metadata model" and "analysis of usability of existing standards" — both directly addressed by our generator proposal.
Key details:
- Charter lists EDR, CIS, Coverages, ZARR, GeoTIFF, HDF5 as standards to analyze — none have dimension pagination
- SWG builds from existing OGC Building Blocks with minimal extension (matches our backwards-compatible approach)
- Initial deliverables: GeoDataCube API standard (OGC API-Geodatacubes) + GDC metadata model
- IPR: RAND-Royalty Free; persistent SWG
- TB-20 usability report (24-037) found only 44% interop success across 5 backends; STAC metadata inconsistency = #1 pain point
- No official opengeospatial GitHub repo for GDC SWG yet; m-mohr/geodatacube-api is OUTDATED (last commit Sep 2023)
- TB-21 includes GeoDataCubes thread (sponsorship responses due Mar 2025)

## 2026-03-28 Full testbed lineage mapped (TB-16 through TB-21)
Context: Traced GDC API evolution across all testbeds.
Finding: No testbed has ever addressed dimension member pagination or algorithmic generation.
- TB-16 (20-016): Data access foundations
- TB-17 (21-027): First GDC API draft; dimensions via cube:dimensions in collection metadata
- TB-19 (23-047, 23-048): Draft API submitted to SWG; identified pagination gap explicitly
- TB-20 (24-035, 24-037): Profiles approach + usability testing; recommends bridges over unified standard
- TB-21: GeoDataCubes thread planned; focus on vendor/provider feedback
ECMWF ogc-gdc-usecase repo demonstrates scale problem: 340GB+ datasets, "large requests can be slow"

## 2026-03-28 TB-20 pivot strengthens our positioning
Context: TB-20 concluded that integrating existing standards is more promising than a standalone GDC API.
Finding: This pivot STRENGTHENS our proposal because:
- Our generator is an extension to STAC cube:dimensions, not a new standalone standard
- It works within the existing building blocks approach the SWG now favors
- The SWG's shift from "new standard" to "profile/integration" means lightweight, backwards-compatible extensions like ours are exactly the type of contribution they want
- No formal draft standard has been published at docs.ogc.org/DRAFTS — SWG is still formative
- SWG mailing list: https://lists.ogc.org/mailman/listinfo/geodatacube.swg

## 2026-03-28 Renamed testbed → reference-implementation
Context: "Testbed" is an OGC formal program name; using it for our code would be misleading.
Decision: Renamed `testbed/` to `reference-implementation/` with proper `src/ogc_dimensions/` package layout.
Rationale: Correct terminology; pip-installable as `ogc-dimensions`; import as `ogc_dimensions`.

## 2026-03-28 Generalized API from /generators/{type} to /dimensions/{dimension_id}
Context: Generator type was the path key, but dimensions are the user-facing concept.
Decision: Routes now use `/dimensions/{dimension_id}/...`. A `DimensionConfig` maps each named dimension to a generator instance + default extent.
Rationale: Multiple dimensions can share the same generator type with different configs (e.g., `chirps-time` and `ndvi-time` both using dekadal). Dimensions are the addressable resource; generators are the implementation.

## 2026-03-28 Dynastore integration as isolated extension
Context: Need to showcase on a live FAO system without coupling to STAC.
Decision: Thin `DimensionsExtension` (ExtensionProtocol) in geoid wraps the ogc-dimensions pip package. Deployed on `geospatial-tools` Cloud Run service (SCOPE: core,template,dimensions). No STAC interaction.
Rationale: Prototype isolation; ogc-dimensions stays independent; Dynastore just mounts the router.

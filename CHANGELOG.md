# Changelog

## Unreleased

### Paper / deployment notes
- Paper §4.1 updated to note that the integrating GeoID catalog platform
  now publishes a broader OGC API surface on the same service stack —
  Records, Features, Coverages, Styles, Maps, Processes, the OGC Joins
  draft, and a 3D GeoVolumes route shell — with the DimensionsExtension
  coexisting as one more extension under the platform's
  `ExtensionProtocol` / `OGCServiceMixin` seam. This strengthens the
  building-block narrative: dimensions compose with the rest of the
  OGC portfolio under a single `/conformance` aggregate rather than
  standing alone.
- No spec or reference-implementation code change. The `ogc-dimensions`
  package continues to be a dependency of the GeoID `DimensionsExtension`;
  the coexisting OGC extensions live in GeoID itself and are out of
  scope for this repository.

## 1.0.0-rc.1 (2026-04-14)

Release candidate aligned with OGC Building Blocks formal submission track.

### Specification
- Normative JSON examples added for every Building Block:
  - `dimension-inverse/examples/dekadal-inverse-response.json` (success)
  - `dimension-inverse/examples/dekadal-inverse-error.json` (value outside extent)
  - `dimension-hierarchical/examples/admin-ancestors.json` (root-to-member chain)
  - `dimension-hierarchical/examples/admin-children.json` (already present)
- Building Block maturity bumped from `proposal` to `candidate` for all five blocks:
  `dimension-collection`, `dimension-member`, `dimension-pagination`,
  `dimension-inverse`, `dimension-hierarchical`.
- Registry status (`bblocks.json#status`) remains `under-development` pending SWG adoption.

### Reference implementation
- `OGC API - Records` FeatureCollection responses on `/items`, `/inverse`, `/children`, `/ancestors`.
- Invertible + hierarchical conformance classes wired end-to-end.
- `/inverse` reconciled with the normative schema: `GET` returns a bare Record `Feature` on success and `{code, description}` (HTTP 404) on failure; `POST` returns `{type: FeatureCollection, numberMatched, numberReturned, features, errors}` where `errors[]` carries `{value, code, description}` entries.
- Producer rename: `DimensionGenerator → DimensionProvider`, `GeneratedMember → ProducedMember`, `InverseResult` removed in favour of raising `InverseError`. The term *provider* (producer of members) replaces *generator* throughout.

### Governance roadmap
- **2026-Q2:** Formal Building Blocks submission; open Change Request with GeoDataCube SWG.
- **2026-Q3:** STAC Datacube extension PR for the `size` / `href` / `provider` / `hierarchy` fields.
- **2026-Q4 – 2027-Q1:** Target OGC Technical Committee vote; move maturity `candidate → stable`.

## 0.2.0 (2026-04-02)

Renames and provider-model refactors.

- `/generate` endpoint renamed to `/members` across spec, implementation, examples, and paper.
- Hierarchy strategy absorbed into provider type; `bijective` renamed to `invertible`.
- `provider.type` opened to third-party extensions.
- Added `LeveledTreeProvider` and `level` parameter on `/members`.

## 0.1.0 (2026-03-27)

Initial release.

### Specification
- JSON Schema for extended dimension object (`size`, `href`, `provider`)
- JSON Schema for provider object (`type`, `api`, `parameters`, `output`, `invertible`, `search`, `on_invalid`)
- Worked examples: dekadal, pentadal (monthly + annual), integer-range, legacy bridge

### Testbed
- Reference implementation: DekadalProvider, PentadalMonthlyProvider, PentadalAnnualProvider, IntegerRangeProvider
- FastAPI API with /members, /extent, /inverse, /search endpoints
- Docker support

### Paper
- Draft manuscript: "Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes"

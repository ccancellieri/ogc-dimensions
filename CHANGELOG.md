# Changelog

## 0.1.0 (2026-03-27)

Initial release.

### Specification
- JSON Schema for extended dimension object (`size`, `href`, `generator`)
- JSON Schema for generator object (`type`, `api`, `parameters`, `output`, `invertible`, `search`, `on_invalid`)
- Worked examples: dekadal, pentadal (monthly + annual), integer-range, legacy bridge

### Testbed
- Reference implementation: DekadalGenerator, PentadalMonthlyGenerator, PentadalAnnualGenerator, IntegerRangeGenerator
- FastAPI API with /generate, /extent, /inverse, /search endpoints
- Docker support

### Paper
- Draft manuscript: "Scalable Dimension Member Dissemination and Algorithmic Generation for Geospatial Datacubes"

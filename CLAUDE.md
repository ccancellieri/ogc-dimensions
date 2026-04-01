# OGC Dimensions

Spec + paper + reference implementation for scalable datacube dimension generators. Apache-2.0, Python 3.11+.

## Context Routing

-> spec/schema: JSON Schema definitions (dimension.json, generator.json)
-> spec/examples: Worked collection JSON examples (dekadal, pentadal, integer-range, legacy bridge)
-> paper: Scientific manuscript (IMRAD, Markdown)
-> reference-implementation/src/ogc_dimensions/generators: Python generator implementations (base protocol, dekadal, pentadal, integer-range)
-> reference-implementation/src/ogc_dimensions/api: FastAPI app exposing /generate, /extent, /inverse, /search

## Key Concepts

- `size` + `href`: paginated dimension members (OGC API - Common Part 2)
- `generator` object: algorithmic member generation with OpenAPI discovery
- Bijective inversion: value-to-coordinate mapping for ingestion validation
- Five conformance levels: Basic > Invertible > Searchable > Similarity > Intelligent

## Conventions

- No AI attribution in commits or code
- JSON Schema 2020-12 for generator parameters/output
- OGC API - Features pagination (numberMatched/numberReturned + rel:next/prev)
- Generator tests must cover edge cases: Feb leap/non-leap D3, year boundaries

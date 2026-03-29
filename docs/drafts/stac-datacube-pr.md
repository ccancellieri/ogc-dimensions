# Pull Request Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Depends on:** Issue (see stac-datacube-issue.md)
**Branch name:** `feature/scalable-dimensions`

---

## Title

feat: add `size`, `values_href`, and `generator` properties for scalable dimension members

## Description

### Summary

Adds three optional, backwards-compatible properties to the dimension object schema to support dimensions with thousands to millions of members:

- **`size`** (integer): total member count -- resolves #31
- **`values_href`** (URI): link to paginated endpoint returning dimension values
- **`generator`** (object): algorithmic member generation with OpenAPI discovery

### Changes

#### Schema changes (`json-schema/`)

**`schema.json`** (or equivalent dimension definition):

Add to `properties`:

```json
"size": {
  "type": "integer",
  "minimum": 0,
  "description": "Total number of discrete members in this dimension."
},
"values_href": {
  "type": "string",
  "format": "uri-reference",
  "description": "Link to a paginated endpoint returning dimension values. When present, values MAY be omitted."
},
"generator": {
  "$ref": "#/$defs/generator",
  "description": "Algorithmic member generation definition."
}
```

Add to `$defs`:

```json
"generator": {
  "type": "object",
  "required": ["type", "output"],
  "properties": {
    "type": {
      "description": "Well-known algorithm identifier or custom generator URI.",
      "type": "string"
    },
    "api": {
      "type": "string",
      "format": "uri",
      "description": "OpenAPI definition URI. Required for custom generators."
    },
    "parameters": {
      "description": "Input parameters per JSON Schema 2020-12."
    },
    "output": {
      "description": "Output type per JSON Schema 2020-12."
    },
    "bijective": {
      "type": "boolean",
      "default": false,
      "description": "Whether the generator supports inverse mapping."
    },
    "search": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["exact", "range", "like", "vector"]
      },
      "description": "Supported search protocols."
    },
    "on_invalid": {
      "type": "string",
      "enum": ["reject", "accept", "warn"],
      "default": "reject"
    }
  }
}
```

#### Documentation changes (`README.md`)

Add section "Scalable Dimensions" documenting:
- `size` -- when to use, relationship to `values`
- `values_href` -- pagination conventions (OGC API - Common Part 2)
- `generator` -- well-known types, custom generators, conformance levels

#### Examples

Add or update examples showing:
- Temporal dimension with dekadal generator
- Non-temporal dimension with integer-range generator
- Legacy compatibility via `?format=datetime`

### Backwards compatibility

All additions are optional. No existing properties are modified. Existing collections remain valid. Clients that don't recognize the new properties ignore them per standard JSON processing rules.

### Validation

- JSON Schema validates against JSON Schema 2020-12 meta-schema
- Worked examples validate against the extended schema
- Reference implementation demonstrates all generator endpoints
- Live demo: https://data.review.fao.org/geospatial/v2/api/tools/docs

### References

- Issue: #XX (link to the issue from stac-datacube-issue.md)
- #31 (size property request)
- OGC TB-19 (23-047), TB-20 (24-035, 24-037)
- Full specification: https://github.com/ccancellieri/ogc-dimensions

# Pull Request Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Depends on:** Issue (see stac-datacube-issue.md)
**Branch name:** `feature/scalable-dimensions`

---

## Title

feat: add `size`, `href`, `generator`, `hierarchy`, and `nominal`/`ordinal` types for scalable dimension members

## Description

### Summary

Adds five optional, backwards-compatible additions to the dimension object schema to support dimensions with thousands to millions of members, framed as a profile of OGC API - Records:

- **`size`** (integer): total member count -- resolves #31
- **`href`** (URI): link to paginated endpoint returning dimension values
- **`generator`** (object): algorithmic member generation with OpenAPI discovery
- **`hierarchy`** (object): tree structure for hierarchical dimensions (recursive and leveled strategies)
- **`nominal`** / **`ordinal`**: two new dimension type values for coded dimensions

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
"href": {
  "type": "string",
  "format": "uri-reference",
  "description": "Link to a paginated endpoint returning dimension values. When present, values MAY be omitted."
},
"generator": {
  "$ref": "#/$defs/generator",
  "description": "Algorithmic member generation definition."
},
"hierarchy": {
  "$ref": "#/$defs/hierarchy",
  "description": "Tree structure metadata for hierarchical dimensions."
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
    "invertible": {
      "type": "boolean",
      "default": false,
      "description": "Whether the generator supports /inverse (Invertible conformance level)."
    },
    "hierarchical": {
      "type": "boolean",
      "default": false,
      "description": "Whether the generator supports /children and /ancestors (Hierarchical conformance level)."
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
},
"hierarchy": {
  "type": "object",
  "required": ["strategy"],
  "properties": {
    "strategy": {
      "type": "string",
      "enum": ["recursive", "leveled"],
      "description": "How hierarchy is encoded: 'recursive' (parent reference in member data) or 'leveled' (named level definitions)."
    },
    "parent_property": {
      "type": "string",
      "description": "For recursive strategy: which output field carries the parent code."
    },
    "levels": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "label", "member_id_property"],
        "properties": {
          "id": {"type": "string"},
          "label": {"type": "string"},
          "size": {"type": "integer"},
          "parent_level": {"type": "string"},
          "member_id_property": {"type": "string"},
          "parent_id_property": {"type": "string"},
          "parameters": {"type": "object"}
        }
      },
      "description": "For leveled strategy: ordered level definitions."
    }
  }
}
```

Add to `type` enum: `"nominal"`, `"ordinal"`.

#### Documentation changes (`README.md`)

Add section "Scalable Dimensions" documenting:
- `size` -- when to use, relationship to `values`
- `href` -- pagination conventions (OGC API - Common Part 2)
- `generator` -- well-known types, custom generators, conformance levels
- `hierarchy` -- recursive and leveled strategies, `/children` and `/ancestors` endpoints
- `nominal`/`ordinal` -- when to use instead of `other`

#### Examples

Add or update examples showing:
- Temporal dimension with dekadal generator (paginated, invertible, searchable)
- Hierarchical dimension with admin boundaries (leveled) and indicator tree (recursive)
- Non-temporal dimension with integer-range generator
- Legacy compatibility via `?format=datetime`

### Backwards compatibility

All additions are optional. No existing properties are modified. Existing collections remain valid. Clients that don't recognize the new properties ignore them per standard JSON processing rules. New type values (`nominal`, `ordinal`) are handled gracefully by implementations that treat unknown types as `other`.

### Validation

- JSON Schema validates against JSON Schema 2020-12 meta-schema
- Worked examples validate against the extended schema
- Reference implementation demonstrates all generator endpoints across 5 conformance levels
- 120+ tests passing in the reference implementation
- Live demo: https://data.review.fao.org/geospatial/v2/api/tools/docs
- Interactive notebooks demonstrating all features: [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb), [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb)

### References

- Issue: #XX (link to the issue from stac-datacube-issue.md)
- #31 (size property request)
- OGC TB-19 (23-047), TB-20 (24-035, 24-037)
- Full specification + OGC Building Blocks: https://github.com/ccancellieri/ogc-dimensions

# Pull Request Draft: stac-extensions/datacube

**Target repo:** https://github.com/stac-extensions/datacube
**Depends on:** Issue https://github.com/stac-extensions/datacube/issues/36
**Branch name:** `feature/scalable-dimensions`

---

## Title

feat: add `size`, `href`, `provider`, `hierarchy`, `nominal`/`ordinal` types, multilingual labels, and sort order for scalable dimension members

## Description

### Summary

Adds seven optional, backwards-compatible additions to the dimension object schema to support dimensions with thousands to millions of members:

- **`size`** (integer): total member count -- resolves #31
- **`href`** (URI): link to paginated endpoint returning dimension values
- **`provider`** (object): algorithmic member generation with OpenAPI discovery, `config`/`parameters` separation, and `language_support`
- **`hierarchy`** (object): tree structure for hierarchical dimensions (recursive and leveled strategies)
- **`nominal`** / **`ordinal`**: two new dimension type values for coded dimensions
- **Multi-language labels**: `labels` map on members, `language_support` on providers, aligned with STAC Language Extension
- **Sort order**: `sort_by` / `sort_dir` standard query parameters

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
"provider": {
  "$ref": "#/$defs/provider",
  "description": "Algorithmic member generation definition."
},
"hierarchy": {
  "$ref": "#/$defs/hierarchy",
  "description": "Tree structure metadata for hierarchical dimensions."
}
```

Add to `$defs`:

```json
"provider": {
  "type": "object",
  "required": ["type", "output"],
  "properties": {
    "type": {
      "description": "Well-known algorithm identifier or custom provider URI. Well-known types: 'daily-period' (sub-monthly temporal periods configured by config.period_days and config.scheme), 'integer-range' (evenly-spaced integer bins), 'static-tree' (recursive in-memory hierarchy), 'leveled-tree' (leveled in-memory hierarchy with ?level=N filtering). Custom providers use a full URI as the type value.",
      "type": "string"
    },
    "api": {
      "type": "string",
      "format": "uri",
      "description": "OpenAPI definition URI. REQUIRED when type is a full URI (custom provider). For well-known types the API definition is implicit."
    },
    "config": {
      "type": "object",
      "description": "Author-set configuration values for this provider instance. Static constants fixed at collection-authoring time, not overridable by API clients per-request. They configure the provider algorithm itself (e.g., period_days and scheme for temporal periods, step for integer ranges). Well-known providers with no author-configurable constants SHOULD omit this field or set it to {}.",
      "additionalProperties": true
    },
    "parameters": {
      "description": "JSON Schema 2020-12 document describing query-time parameters that clients may pass per request to /members, /children, and /search. NOT static configuration values -- use 'config' for author-set constants. Standard cross-provider parameters (SHOULD be declared here): 'language' (RFC 5646 Language-Tag), 'sort_by' (output field name), 'sort_dir' ('asc'|'desc').",
      "$ref": "https://json-schema.org/draft/2020-12/schema"
    },
    "output": {
      "description": "Type and structure of each generated member, per JSON Schema 2020-12. Standard optional output fields: 'label' (string, human-readable name), 'labels' (object, multilingual names keyed by RFC 5646 language tag), 'rank' (integer, explicit sort position for ordinal dimensions, 0-based), 'has_children' (boolean, true if member has children).",
      "$ref": "https://json-schema.org/draft/2020-12/schema"
    },
    "invertible": {
      "type": "boolean",
      "default": false,
      "description": "Whether the provider supports /inverse (Invertible conformance level)."
    },
    "hierarchical": {
      "type": "boolean",
      "default": false,
      "description": "Whether the provider supports /children and /ancestors (Hierarchical conformance level)."
    },
    "navigable": {
      "type": "boolean",
      "default": false,
      "description": "Whether the provider supports per-member navigation links (rel:children, rel:ancestors) when clients pass ?links=true. Requires hierarchical: true."
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
    },
    "language_support": {
      "type": "array",
      "description": "Languages the provider can serve member labels in. Each entry is a Language Object aligned with the STAC Language Extension. When present, clients MAY request a specific language via the 'language' query parameter (RFC 5646) or Accept-Language header.",
      "items": {
        "type": "object",
        "required": ["code"],
        "properties": {
          "code": {"type": "string", "description": "RFC 5646 Language-Tag (e.g. 'en', 'fr', 'ar')."},
          "name": {"type": "string", "description": "Name of the language in the language itself."},
          "alternate": {"type": "string", "description": "Name of the language in English."},
          "dir": {"type": "string", "enum": ["ltr", "rtl"], "default": "ltr"}
        }
      }
    }
  },
  "if": {
    "properties": { "type": { "type": "string", "format": "uri" } }
  },
  "then": {
    "required": ["type", "output", "api"]
  }
},
"hierarchy": {
  "type": "object",
  "properties": {
    "strategy": {
      "type": "string",
      "enum": ["recursive", "leveled", "composite"],
      "description": "How hierarchy is encoded: 'recursive' (parent reference in member data), 'leveled' (named level definitions), or 'composite' (leveled at top levels, recursive within a level)."
    },
    "parent_property": {
      "type": "string",
      "description": "For recursive strategy: which output field carries the parent code. Corresponds to skos:broader."
    },
    "root_filter": {
      "type": "string",
      "description": "Provider parameter expression that selects root members. For recursive providers, root members are those whose parent_property is null if omitted."
    },
    "depth": {
      "type": "integer",
      "minimum": 1,
      "description": "Maximum depth of the tree. Informational."
    },
    "levels": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "label"],
        "properties": {
          "id": {"type": "string"},
          "label": {"type": "string"},
          "labels": {
            "type": "object",
            "description": "Multilingual level names. Keys are RFC 5646 Language-Tags.",
            "additionalProperties": {"type": "string"}
          },
          "size": {"type": "integer"},
          "parent_level": {"type": "string"},
          "member_id_property": {"type": "string", "description": "Output field that uniquely identifies members at this level. Defaults to 'code'."},
          "parent_id_property": {"type": "string", "description": "Output field holding the parent member identifier (from parent level)."},
          "parameters": {"type": "object", "description": "Provider parameters that select members at this level."},
          "href": {
            "type": "string",
            "format": "uri-reference",
            "description": "Link to paginated endpoint for members at this level."
          }
        }
      },
      "description": "For leveled strategy: ordered level definitions from coarsest to finest."
    }
  }
}
```

Add to `type` enum: `"nominal"`, `"ordinal"`.

#### Documentation changes (`README.md`)

Add section "Scalable Dimensions" documenting:
- `size` -- when to use, relationship to `values`
- `href` -- pagination conventions (OGC API - Common Part 2)
- `provider` -- well-known types (`daily-period`, `integer-range`, `static-tree`, `leveled-tree`), custom providers, `config` vs `parameters`, conformance levels
- `hierarchy` -- recursive and leveled strategies, `/children` and `/ancestors` endpoints, `has_children`, `navigable`
- `nominal`/`ordinal` -- when to use instead of `other`
- Multi-language labels -- `language_support` on provider, `labels` on members and hierarchy levels, STAC Language Extension alignment
- Sort order -- `sort_by`, `sort_dir`, `rank` for ordinal dimensions

#### Examples

Add or update examples showing:
- Temporal dimension with dekadal provider (`daily-period` type, `config`, paginated, invertible, searchable)
- Hierarchical dimension with admin boundaries (leveled, multilingual `labels`, `href` per level, `language_support`)
- Hierarchical dimension with indicator tree (recursive, custom URI type)
- Non-temporal dimension with integer-range provider
- Legacy compatibility via `?format=datetime`

### Backwards compatibility

All additions are optional. No existing properties are modified. Existing collections remain valid. Clients that don't recognize the new properties ignore them per standard JSON processing rules. New type values (`nominal`, `ordinal`) are handled gracefully by implementations that treat unknown types as `other`. Clients that recognize `labels` gain multilingual display; those that don't fall back to the `label` string.

### Validation

- JSON Schema validates against JSON Schema 2020-12 meta-schema
- Worked examples validate against the extended schema
- Reference implementation demonstrates all provider endpoints across 5 conformance levels
- 138 tests passing in the reference implementation (`pytest tests/`)
- Live demo: https://data.review.fao.org/geospatial/v2/api/tools/docs
- Interactive notebooks: [Creating Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/01_creating_dimensions.ipynb), [ASIS Dimensions](https://github.com/un-fao/geoid/blob/main/src/dynastore/extensions/notebooks/examples/02_asis_dimensions.ipynb)

### References

- Issue: https://github.com/stac-extensions/datacube/issues/36
- #31 (size property request)
- OGC TB-19 (23-047), TB-20 (24-035, 24-037)
- [STAC Language Extension](https://github.com/stac-extensions/language)
- [STAC API Language Extension](https://github.com/stac-api-extensions/language)
- Full specification + OGC Building Blocks: https://github.com/ccancellieri/ogc-dimensions

# Building Block: Dimension Member

A **Dimension Member** is an OGC Record (GeoJSON Feature with
`geometry: null`) representing a single value in a dimension's
coordinate space.

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member`

Depends on:
- `http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-core`

## Record Properties Mapping

| Records property | Dimension member field | Description |
|------------------|----------------------|-------------|
| `id` | `code` | Member code (e.g. `"2024-D01"`) |
| `properties.title` | `label` | Human-readable label |
| `properties.time` | `time.interval` | Temporal interval `[start, end]` |
| `properties.keywords` | `labels` | Tags / categories |
| `properties.type` | `recordType` | Always `"dimension-member"` |
| `properties.dimension:type` | Dimension type | `"temporal"`, `"nominal"`, `"ordinal"` |
| `properties.dimension:code` | Member code | Same as `id` |
| `properties.dimension:index` | Position index | Zero-based ordinal position |
| `properties.dimension:start` | Start value | Start of the member's range |
| `properties.dimension:end` | End value | End of the member's range |

### Hierarchical Properties (optional)

| Property | Description |
|----------|-------------|
| `properties.dimension:parent` | Parent member code |
| `properties.dimension:level` | Depth in the tree (0 = root) |
| `properties.dimension:has_children` | `true` if node has children |
| `links[rel=parent]` | Link to parent member |
| `links[rel=children]` | Link to children listing |

## Link relations (normative)

The `rel` values appearing in `links[]` of a dimension or member response
**MUST** be a subset of the rel values derived from the dimension's
`provider` capabilities:

| Provider capability | Permitted `links[].rel` values |
|---------------------|-------------------------------|
| (always) | `self`, `collection`, `items`, `queryables` |
| `invertible: true` | `inverse` |
| `search: [...]` non-empty | `search` |
| `hierarchical: true` | `parent`, `children`, `ancestors` |

Servers **MUST NOT** emit a `rel` value whose corresponding capability
is not declared by the provider. A conformance test SHALL assert this
on every registered provider × `rel` combination.

> **Why:** without this rule a server can advertise a hierarchical
> traversal link on a non-hierarchical dimension, sending clients to
> an endpoint that returns 501. The `links[]` set must remain a
> truthful projection of the provider's declared capability surface.

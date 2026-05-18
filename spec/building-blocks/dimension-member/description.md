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

## Identifier (normative)

The `Feature.id` of a dimension member **MUST** equal the natural key
of that member — the dimension's `code` value (e.g. `2024-D01`,
`bin_0`, `ITA`). Servers **MUST NOT** mint surrogate identifiers
(UUIDs, auto-increment integers) for dimension members.

Regenerating the algorithm or reloading the registry from the same
`config` MUST produce the same `id` for the same member across
deployments, restarts, and releases. This is the constraint that lets
implementations substitute a virtual (generator-as-reader) backing for
a materialised one without breaking any downstream system that records
the member identifier — see the informative annex
[`docs/annex-virtual-dimensions.md`](../../../docs/annex-virtual-dimensions.md)
for the operational guidance behind this clause.

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

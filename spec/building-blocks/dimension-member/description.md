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

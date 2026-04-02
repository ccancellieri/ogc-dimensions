# Building Block: Dimension Hierarchical

Defines `/children` and `/ancestors` endpoints and the `?parent=`
filter for navigating hierarchical dimension members.

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-hierarchical`

Depends on:
- `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member`

## Endpoints

### Children

```
GET /collections/{dimensionId}/items?parent={parentCode}
```

Returns the direct children of the given parent member.  For root
members, use `parent=` (empty or omit the parameter).

### Ancestors

```
GET /collections/{dimensionId}/items/{memberId}/ancestors
```

Returns the ancestor chain from the given member to the root,
ordered from immediate parent to root.

## Hierarchy Strategies

| Strategy | Description | `dimension:level` | `dimension:has_children` |
|----------|-------------|-------------------|-------------------------|
| **Leveled** | Fixed-depth tree (e.g. Continent > Country > Region) | Present | Present |
| **Recursive** | Arbitrary-depth tree (e.g. statistical indicator taxonomy) | Present | Present |

## Link Relations

Members in hierarchical dimensions include navigation links:

| `rel` | Target | When present |
|-------|--------|-------------|
| `parent` | Parent member Record | When `dimension:parent` is set |
| `children` | Children listing with `?parent={code}` | When `dimension:has_children` is true |
| `ancestors` | Ancestor chain endpoint | Always |

## Filtering

The `?level=` query parameter restricts results to a specific depth
in the hierarchy (0 = root, 1 = first level, etc.).

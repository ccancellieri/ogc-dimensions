# Building Block: Dimension Pagination

Extends OGC API - Common Part 2 pagination with dimension-specific
semantics for paginating algorithmically generated dimension members.

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination`

Depends on:
- `http://www.opengis.net/spec/ogcapi-common-2/1.0/conf/collections`
- `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection`

## Pagination Semantics

| Field | Semantics |
|-------|-----------|
| `numberMatched` | Total members in the dimension's extent |
| `numberReturned` | Members in the current page |
| `offset` | Starting position in the generated sequence |
| `limit` | Maximum members per page |
| `rel:next` | Link to next page (if more members exist) |
| `rel:prev` | Link to previous page (if offset > 0) |

## Interaction with Generators

For algorithmically generated dimensions, `numberMatched` is computed
from the generator's extent without materializing all members.  The
server generates only the requested page (`offset` to `offset + limit`).

For materialized (stored) dimensions, standard SQL pagination applies.

# Building Block: Dimension Pagination

Profile of OGC API - Common Part 2 pagination (OGC 19-072) with
dimension-specific semantics for paginating algorithmically generated
dimension members. The normative parameter definitions live in
OGC 19-072; `schema.json` in this Building Block restates `limit` and
`offset` in JSON Schema for validation convenience and cites the
authoritative source in `$comment`.

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination`

Depends on:
- `http://www.opengis.net/spec/ogcapi-common-2/1.0/conf/collections`
- `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection`

Normative references:
- OGC API - Common - Part 2: Geospatial Data (OGC 19-072) — https://docs.ogc.org/is/19-072/19-072.html
- OGC API - Features Part 1 §7.15.3 for `numberMatched` / `numberReturned`
- RFC 8288 for `rel=next|prev|self|collection|items` link relations

## Request parameters (profile of OGC 19-072)

| Parameter | Type | Default | Min | Max | Notes |
|-----------|------|---------|-----|-----|-------|
| `limit` | integer | 10 | 1 | 10000 (server MAY lower) | Page size; advertised in the OpenAPI document |
| `offset` | integer | 0 | 0 | — | Zero-based start position in the generated sequence |

## Response envelope

| Field | Semantics |
|-------|-----------|
| `numberMatched` | Total members matching the query within the dimension's extent |
| `numberReturned` | Members in the current page |
| `rel="self"` | Canonical URL of the current page |
| `rel="next"` | Link to next page (if more members exist) |
| `rel="prev"` | Link to previous page (if offset > 0) |
| `rel="collection"` | Link to the parent dimension collection |
| `rel="items"` | (on the collection response) Link to this paginated endpoint |

## Interaction with Providers

For algorithmically generated dimensions, `numberMatched` is computed
from the provider's extent without materializing all members.  The
server generates only the requested page (`offset` to `offset + limit`).

For materialized (stored) dimensions, standard SQL pagination applies.

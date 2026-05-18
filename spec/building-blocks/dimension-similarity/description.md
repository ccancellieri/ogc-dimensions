# Building Block: Dimension Similarity

A normative conformance class for vector-embedding similarity search
over dimension members.

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-similarity`

Depends on:
- `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member`

## Endpoint

`GET /{collections-root}/{dimensionId}/search?similar={value}&limit=N`

- `similar` (required): a reference value (member code, free-text label,
  or pre-computed embedding identifier — provider-defined) against which
  members are ranked by embedding-space proximity.
- `limit` (optional, default 10, max 100): the maximum number of
  results to return (the "k" of k-NN).

The response is an OGC Records `FeatureCollection` whose `features[]`
are dimension members ranked by similarity to the reference value
(highest similarity first). Implementations MAY add a `similarity`
property to each member's `properties` object reporting the raw
similarity score.

## Stub response (normative)

Conformant servers that advertise this conformance class but do not
have a backing vector index **MUST** return:

- HTTP status: `501 Not Implemented`
- `Content-Type: application/problem+json`
- Body (RFC 7807 problem detail):

```json
{
  "type": "https://www.opengis.net/spec/ogc-dimensions/1.0/errors/similarity-not-implemented",
  "title": "Similarity search not implemented",
  "status": 501,
  "detail": "Server advertises ogc-dimensions/1.0/conf/dimension-similarity but has no backing vector index for this dimension.",
  "dimension": "{dimensionId}"
}
```

Servers MUST continue to advertise the conformance class URI at
`/conformance` even when they only ship the stub, so that clients can
negotiate the capability surface against the specification rather than
guess by probing.

## Why the stub is normative

Vector-embedding similarity is architecturally real: every produced
dimension can in principle carry an embedding column. Pinning the URI,
query parameter shape, and error envelope into v1.0 gives future
implementations a stable target. The 501 stub keeps the conformance
class honest about availability without dropping it back into
"informative" status.

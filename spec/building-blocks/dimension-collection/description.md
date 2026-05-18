# Building Block: Dimension Collection

A **Dimension Collection** is a Records catalogue (`itemType: "record"`)
whose items are dimension members.  It extends the OGC API - Records
collection with a `cube:dimensions` property containing the dimension
definition from the STAC Datacube Extension, enriched with the
ogc-dimensions extensions (`size`, `href`, `provider`, `hierarchy`).

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection`

Depends on:
- `http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core`
- `http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-collection`

## Mapping

| Records concept | Dimension concept |
|-----------------|-------------------|
| Collection | Dimension descriptor (temporal-dekadal, elevation-bands, ...) |
| `collection.id` | Dimension identifier |
| `collection.title` | Human-readable dimension name |
| `collection.description` | Dimension description |
| `collection.itemType` | Always `"record"` |
| `collection.extent` | Temporal or value extent of the dimension |
| `collection.provider` | Full provider definition (type, config, capabilities) |
| `cube:dimensions` | Slim provider reference (`{type, href}`) for STAC clients |

## Provider Object

The `provider` property at collection level carries the full provider
definition: type, config, invertibility, search protocols, and capabilities.
Within `cube:dimensions`, a slim `provider: {type, href}` reference points
STAC clients to the collection endpoint for full details.  See `provider.json` schema.

Servers that implement this building block:
1. Serve the collection at `/collections/{dimensionId}`
2. Include `cube:dimensions` in the collection metadata
3. Serve members as Records at `/collections/{dimensionId}/items`

## Extent derivation (normative)

The `extent` field of a dimension collection **MUST** be derived from
the backing provider's generator: specifically, from the
`ExtentResult.native_min` / `native_max` returned by
`provider.extent(extent_min, extent_max)` and the corresponding
`size` value.

Implementations **MUST NOT** allow `extent` to be configured
independently of the generator at the collection level. Without this
constraint, `extent` and the items endpoint's `numberMatched` can
drift independently (live regression observed against `v1.0.0-rc.1`).

Servers **SHOULD** perform a startup-time assertion of the form
`extent.size == generator.number_matched` and **SHOULD** fail loudly
on inconsistency.

### Shape dispatch on ExtentResult

The shape of the rendered `extent` is fixed by the provider's
`ExtentResult` and the collection's `dimension_type`. Exactly one of
the three keys MUST be present:

| ExtentResult signature | `dimension_type` | Rendered shape |
|---|---|---|
| `native_min`/`native_max` non-null | `temporal` | `{"temporal": {"interval": [[min, max]]}}` (RFC 3339) |
| `native_min`/`native_max` non-null | any other ordinal type | `{"values": {"min": ..., "max": ...}}` |
| `native_min`/`native_max` both `null`, `size > 0` | `nominal` / hierarchical | `{"members": {"count": <size>}}` |

> **REQ (dimension-collection, §"Extent shape for non-ordered dims"):**
> Providers whose generator has no orderable extent (purely categorical
> or hierarchical with `native_min == native_max == null`) **MUST**
> render `extent` as `{"members": {"count": <size>}}` where `<size>`
> equals the total number of members across all levels and **MUST**
> equal the items endpoint's `numberMatched` returned for a full,
> unfiltered crawl. The `members.count` field gives clients a single
> canonical "how big is this dimension" value to read before deciding
> whether to paginate, mirroring the role of `temporal.interval` and
> `values.{min,max}` for ordered dims.

Servers **MUST NOT** omit `extent` for non-ordered dims when the
provider exposes a finite size: omitting it forces clients to
special-case "no extent → fall back to paginating `/items` to learn
size", which defeats the round-trip invariant above.

## Round-trip on write paths (normative)

The conformance classes in this specification describe **read** paths
end-to-end: a client reads a STAC collection, follows
`cube:dimensions[*].provider.href`, paginates members. This section
adds the corresponding **write**-path round-trip clause.

> **REQ (dimension-collection, §"Round-trip"):** When a STAC
> collection's `cube:dimensions[*].provider.href` resolves under the
> server's own registry (i.e. the URL prefix matches
> `${baseUrl}/dimensions/`), the server **SHOULD** reject collection
> writes that reference unknown providers, returning **`422
> Unprocessable Entity`** with an `application/problem+json` body that
> names the unresolved href in `detail` and, where possible, the
> closest registered provider in a `nearest` field. Servers whose
> registry is external **SHOULD** treat the href opaquely (no
> resolution attempt, no rejection).

Without this clause, a workspace can write a STAC collection asserting
`cube:dimensions.time.provider.href = "<server>/dimensions/pentadal-monthly"`
when no such provider is registered, and the broken reference is only
detected at read time — far from the typo or the deleted dimension.

This clause depends on the singular `GET /dimensions/{id}` endpoint
defined below: a server cannot validate a `provider.href` end-to-end
without it.

## Singular endpoint (normative)

Servers **MUST** serve the dimension collection at the singular path
`/{collections-root}/{dimensionId}` (e.g. `/dimensions/{dimensionId}`),
returning the same Collection-shaped JSON that appears as one entry of
the root listing's `collections[]` array. This guarantees that the
client flow documented for `cube:dimensions[*].provider.href` — follow
the href to obtain the dimension record, then follow `links[rel="items"]`
to paginate members — resolves end-to-end without requiring a client to
parse the root listing to look up a member by `id`.

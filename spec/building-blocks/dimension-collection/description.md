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

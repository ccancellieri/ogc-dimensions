# Reusable Patterns

## Generator Protocol Pattern
All generators inherit from `DimensionGenerator` ABC in `testbed/generators/base.py`.
Required: `generate()`, `extent()`, `generator_type`, `invertible`.
Optional: `inverse()`, `search()`, `inverse_batch()`.
Capabilities and search_protocols are derived properties.

## Dekadal Index Formula
`index = (month - 1) * 3 + dekad` where dekad is 1-3.
D3 end day = last day of month (varies: 28/29/30/31).

## OGC API Pagination Response
```json
{
  "numberMatched": total,
  "numberReturned": page_size,
  "values": [...],
  "links": [{"rel": "next", "href": "..."}]
}
```

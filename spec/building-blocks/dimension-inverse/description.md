# Building Block: Dimension Inverse

Defines the `/inverse` endpoint: given a raw value, return the dimension
member it belongs to.  This enables ingestion-time coordinate
validation ("does this timestamp fall within a known dekad?").

## Conformance

URI: `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-inverse`

Depends on:
- `http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection`

## Endpoint

```
GET /collections/{dimensionId}/inverse?value={rawValue}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `value` | string | Raw value to invert (e.g. `"2024-01-05"`, `"125"`) |

### Response

Returns the dimension member Record that contains the given value,
or HTTP 404 if the value falls outside the dimension's extent.

## Use Cases

1. **Ingestion validation**: A data pipeline receives a timestamp
   `"2024-01-05"` and needs to know which dekad it belongs to. The
   `/inverse` endpoint returns `"2024-D01"`.

2. **Coordinate mapping**: An elevation value of `125` maps to the
   `"100-150"` elevation band via `/inverse?value=125`.

3. **Admin boundary lookup**: A country code maps to its position
   in the admin-boundaries hierarchy.

# Example API Responses

Companion to the worked collection examples. All responses follow the
**OGC API - Records** profile: dimension collections have `itemType: "record"`,
members are GeoJSON Features (`geometry: null`) with `dimension:*` properties,
and paginated endpoints return `FeatureCollection` envelopes.

---

## Conformance — `/conformance`

```json
{
  "conformsTo": [
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-core",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-collection",
    "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/json",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/core",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-collection",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-pagination",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-inverse",
    "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-hierarchical"
  ]
}
```

---

## List Dimensions — `/dimensions`

Each dimension is an OGC Records collection with `itemType: "record"` and a
`cube:dimensions` object carrying the generator definition.

```json
{
  "collections": [
    {
      "id": "dekadal",
      "title": "Dekadal",
      "description": "10-day periods (36/year). Used by FAO ASIS, FEWS NET, TUW-GEO.",
      "itemType": "record",
      "extent": {
        "temporal": {
          "interval": [["2024-01-01T00:00:00Z", "2024-12-31T00:00:00Z"]]
        }
      },
      "cube:dimensions": {
        "dekadal": {
          "type": "temporal",
          "generator": {
            "type": "daily-period",
            "config": {"period_days": 10, "scheme": "monthly"},
            "invertible": true,
            "capabilities": ["basic", "invertible", "searchable"],
            "search_protocols": ["exact", "range"]
          }
        }
      },
      "links": [
        {"rel": "self", "href": ".../dimensions/dekadal", "type": "application/json"},
        {"rel": "items", "href": ".../dimensions/dekadal/members", "type": "application/geo+json"},
        {"rel": "queryables", "href": ".../dimensions/dekadal/queryables", "type": "application/schema+json"}
      ]
    }
  ]
}
```

---

## dekadal — `/members`

Paginated FeatureCollection of dimension members. Each member is a GeoJSON
Feature with `geometry: null` and `dimension:*` namespaced properties.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 36,
  "numberReturned": 3,
  "features": [
    {
      "type": "Feature",
      "id": "2024-K01",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "2024-K01",
        "dimension:type": "temporal",
        "dimension:code": "2024-K01",
        "dimension:index": 0,
        "dimension:start": "2024-01-01",
        "dimension:end": "2024-01-10",
        "time": {"interval": ["2024-01-01", "2024-01-10"]}
      }
    },
    {
      "type": "Feature",
      "id": "2024-K02",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "2024-K02",
        "dimension:type": "temporal",
        "dimension:code": "2024-K02",
        "dimension:index": 1,
        "dimension:start": "2024-01-11",
        "dimension:end": "2024-01-20",
        "time": {"interval": ["2024-01-11", "2024-01-20"]}
      }
    },
    {
      "type": "Feature",
      "id": "2024-K03",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "2024-K03",
        "dimension:type": "temporal",
        "dimension:code": "2024-K03",
        "dimension:index": 2,
        "dimension:start": "2024-01-21",
        "dimension:end": "2024-01-31",
        "time": {"interval": ["2024-01-21", "2024-01-31"]}
      }
    }
  ],
  "links": [
    {"rel": "self", "href": ".../dekadal/members?limit=3&offset=0", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../dekadal", "type": "application/json"},
    {"rel": "next", "href": ".../dekadal/members?limit=3&offset=3", "type": "application/geo+json"}
  ]
}
```

---

## world-admin — `/members` (hierarchical, root level)

Root members (continents) with hierarchy properties and navigation links.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 5,
  "numberReturned": 5,
  "features": [
    {
      "type": "Feature",
      "id": "AFR",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "Africa",
        "dimension:type": "nominal",
        "dimension:code": "AFR",
        "dimension:index": 0,
        "dimension:level": 0,
        "dimension:has_children": true,
        "labels": {"en": "Africa", "fr": "Afrique", "ar": "\u0623\u0641\u0631\u064a\u0642\u064a\u0627", "es": "\u00c1frica", "zh": "\u975e\u6d32"}
      },
      "links": [
        {"href": ".../world-admin/items/AFR", "rel": "self", "type": "application/geo+json"},
        {"href": ".../world-admin", "rel": "collection", "type": "application/json"},
        {"href": ".../world-admin/children?parent=AFR", "rel": "children", "type": "application/geo+json"},
        {"href": ".../world-admin/ancestors?member=AFR", "rel": "ancestors", "type": "application/json"}
      ]
    }
  ],
  "links": [
    {"rel": "self", "href": ".../world-admin/members?limit=100&offset=0", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../world-admin", "type": "application/json"}
  ]
}
```

---

## world-admin — `/children?parent=AFR`

Direct children of Africa (countries). Each child is a Feature with hierarchy
properties and navigation links.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 9,
  "numberReturned": 3,
  "features": [
    {
      "type": "Feature",
      "id": "DZA",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "Algeria",
        "dimension:type": "nominal",
        "dimension:code": "DZA",
        "dimension:index": 0,
        "dimension:level": 1,
        "dimension:parent": "AFR",
        "labels": {"en": "Algeria", "fr": "Alg\u00e9rie"}
      },
      "links": [
        {"href": ".../world-admin/items/DZA", "rel": "self", "type": "application/geo+json"},
        {"href": ".../world-admin", "rel": "collection", "type": "application/json"},
        {"href": ".../world-admin/ancestors?member=DZA", "rel": "ancestors", "type": "application/json"}
      ]
    }
  ],
  "links": [
    {"rel": "self", "href": ".../world-admin/children?parent=AFR&limit=3&offset=0", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../world-admin", "type": "application/json"},
    {"rel": "next", "href": ".../world-admin/children?parent=AFR&limit=3&offset=3", "type": "application/geo+json"}
  ]
}
```

---

## world-admin — `/ancestors?member=KEN`

Ancestor chain from root to Kenya (inclusive), returned as a FeatureCollection.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 2,
  "numberReturned": 2,
  "features": [
    {
      "type": "Feature",
      "id": "AFR",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "Africa",
        "dimension:type": "nominal",
        "dimension:code": "AFR",
        "dimension:level": 0
      },
      "links": [
        {"href": ".../world-admin/items/AFR", "rel": "self", "type": "application/geo+json"},
        {"href": ".../world-admin/children?parent=AFR", "rel": "children", "type": "application/geo+json"}
      ]
    },
    {
      "type": "Feature",
      "id": "KEN",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "Kenya",
        "dimension:type": "nominal",
        "dimension:code": "KEN",
        "dimension:level": 1,
        "dimension:parent": "AFR"
      }
    }
  ],
  "links": [
    {"rel": "self", "href": ".../world-admin/ancestors?member=KEN", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../world-admin", "type": "application/json"}
  ]
}
```

---

## integer-range — `/members`

Integer range members with `dimension:start` and `dimension:end` bounds.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 51,
  "numberReturned": 3,
  "features": [
    {
      "type": "Feature",
      "id": "0",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "0",
        "dimension:type": "other",
        "dimension:code": "0",
        "dimension:index": 0,
        "dimension:start": 0,
        "dimension:end": 99
      }
    },
    {
      "type": "Feature",
      "id": "100",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "100",
        "dimension:type": "other",
        "dimension:code": "100",
        "dimension:index": 1,
        "dimension:start": 100,
        "dimension:end": 199
      }
    }
  ],
  "links": [
    {"rel": "self", "href": ".../integer-range/members?limit=3&offset=0", "type": "application/geo+json"},
    {"rel": "collection", "href": ".../integer-range", "type": "application/json"},
    {"rel": "next", "href": ".../integer-range/members?limit=3&offset=3", "type": "application/geo+json"}
  ]
}
```

---

## Search — `/search?exact=2024-K01`

Search results also use the FeatureCollection envelope.

```json
{
  "type": "FeatureCollection",
  "numberMatched": 1,
  "numberReturned": 1,
  "features": [
    {
      "type": "Feature",
      "id": "2024-K01",
      "geometry": null,
      "properties": {
        "type": "dimension-member",
        "title": "2024-K01",
        "dimension:type": "temporal",
        "dimension:code": "2024-K01",
        "dimension:index": 0,
        "dimension:start": "2024-01-01",
        "dimension:end": "2024-01-10",
        "time": {"interval": ["2024-01-01", "2024-01-10"]}
      }
    }
  ],
  "links": [
    {"rel": "self", "href": ".../dekadal/search?exact=2024-K01", "type": "application/geo+json"}
  ]
}
```

---

## Live endpoints

- Swagger UI: https://data.review.fao.org/geospatial/v2/api/tools/docs
- Members: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5
- Extent: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/extent
- Inverse: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-15
- Search: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?like=2024-K*

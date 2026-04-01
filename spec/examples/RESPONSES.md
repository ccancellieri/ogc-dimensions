# Example API Responses

Companion to the worked collection examples. Shows what clients receive from each endpoint.

---

## dekadal — `/members`

Live: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5

`href` points to the live reference implementation. Clients follow `rel:next` links to paginate through all 900 dekadal members. The `limit=5` default produces 180 pages, making the pagination mechanics visible.

```json
{
  "dimension": "dekadal",
  "numberMatched": 900,
  "numberReturned": 5,
  "values": [
    {"code": "2000-K01", "start": "2000-01-01", "end": "2000-01-10", "days": 10},
    {"code": "2000-K02", "start": "2000-01-11", "end": "2000-01-20", "days": 10},
    {"code": "2000-K03", "start": "2000-01-21", "end": "2000-01-31", "days": 11}
  ],
  "links": [
    {"rel": "self", "href": ".../dekadal/members?limit=5&offset=0"},
    {"rel": "next", "href": ".../dekadal/members?limit=5&offset=5"}
  ]
}
```

Live endpoints:
- Page 1: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5&offset=0
- Page 2: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/members?limit=5&offset=5
- Extent: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/extent
- Inverse: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/inverse?value=2024-01-15
- Search: https://data.review.fao.org/geospatial/v2/api/tools/dimensions/dekadal/search?like=2024-K*
- Swagger UI: https://data.review.fao.org/geospatial/v2/api/tools/docs

---

## legacy-bridge — `/members?format=datetime`

What a legacy client sees when it follows `href`. Standard ISO dates, standard pagination. No dekadal knowledge required.

```json
{
  "dimension": "dekadal",
  "numberMatched": 900,
  "numberReturned": 5,
  "values": [
    "2024-01-01",
    "2024-01-11",
    "2024-01-21",
    "2024-02-01",
    "2024-02-11"
  ],
  "links": [
    {"rel": "self", "href": ".../dekadal/members?limit=5&offset=0", "type": "application/json"},
    {"rel": "next", "href": ".../dekadal/members?limit=5&offset=5", "type": "application/json"}
  ]
}
```

---

## admin-hierarchy — `/members?level=0`

Root (country) level members. `numberMatched=195` is the full country count.

```json
{
  "dimension": "world-admin",
  "numberMatched": 195,
  "numberReturned": 5,
  "values": [
    {"code": "AFG", "label": "Afghanistan", "level": 0, "iso_code": "AFG"},
    {"code": "ALB", "label": "Albania",     "level": 0, "iso_code": "ALB"},
    {"code": "DZA", "label": "Algeria",     "level": 0, "iso_code": "DZA"},
    {"code": "AND", "label": "Andorra",     "level": 0, "iso_code": "AND"},
    {"code": "AGO", "label": "Angola",      "level": 0, "iso_code": "AGO"}
  ],
  "links": [
    {"rel": "self", "href": ".../world-admin/members?level=0&limit=5&offset=0"},
    {"rel": "next", "href": ".../world-admin/members?level=0&limit=5&offset=5"}
  ]
}
```

## admin-hierarchy — `/children?parent=AFG`

ADM1 children of Afghanistan.

```json
{
  "dimension": "world-admin",
  "parent": "AFG",
  "numberMatched": 34,
  "numberReturned": 5,
  "values": [
    {"code": "AFG-BAD", "label": "Badakhshan", "level": 1, "iso_code": "AFG"},
    {"code": "AFG-BAG", "label": "Badghis",    "level": 1, "iso_code": "AFG"},
    {"code": "AFG-BAL", "label": "Baghlan",    "level": 1, "iso_code": "AFG"},
    {"code": "AFG-BAM", "label": "Bamyan",     "level": 1, "iso_code": "AFG"},
    {"code": "AFG-DAY", "label": "Daykundi",   "level": 1, "iso_code": "AFG"}
  ],
  "links": [
    {"rel": "self",   "href": ".../world-admin/children?parent=AFG&limit=5&offset=0"},
    {"rel": "next",   "href": ".../world-admin/children?parent=AFG&limit=5&offset=5"},
    {"rel": "parent", "href": ".../world-admin/members?code=AFG"}
  ]
}
```

## admin-hierarchy — `/ancestors?member=ETH-TIG`

Ancestor chain for Tigray region (Ethiopia → Tigray).

```json
{
  "dimension": "world-admin",
  "member": "ETH-TIG",
  "ancestors": [
    {"code": "ETH",     "label": "Ethiopia", "level": 0},
    {"code": "ETH-TIG", "label": "Tigray",   "level": 1}
  ]
}
```

---

## indicator-tree — `/members`

Root (domain) level indicators, `parent_code=null`.

```json
{
  "dimension": "faostat-indicators",
  "numberMatched": 12,
  "numberReturned": 5,
  "values": [
    {"code": "QC",  "label": "Food Security",          "parent_code": null},
    {"code": "FS",  "label": "Suite of Food Security", "parent_code": null},
    {"code": "QA",  "label": "Food Balance Sheets",    "parent_code": null},
    {"code": "GT",  "label": "Food Trade",             "parent_code": null},
    {"code": "FA",  "label": "Food Aid Shipments",     "parent_code": null}
  ],
  "links": [
    {"rel": "self", "href": ".../faostat-indicators/members?limit=5&offset=0"},
    {"rel": "next", "href": ".../faostat-indicators/members?limit=5&offset=5"}
  ]
}
```

## indicator-tree — `/children?parent=QC`

Child indicators of the Food Security domain.

```json
{
  "dimension": "faostat-indicators",
  "parent": "QC",
  "numberMatched": 28,
  "numberReturned": 5,
  "values": [
    {"code": "QC001", "label": "Dietary Energy Supply (DES)",           "parent_code": "QC", "unit": "kcal/person/day"},
    {"code": "QC002", "label": "Average Dietary Energy Requirement",    "parent_code": "QC", "unit": "kcal/person/day"},
    {"code": "QC003", "label": "Coefficient of Variation of Hab. Food", "parent_code": "QC", "unit": "%"},
    {"code": "QC004", "label": "Skewness Coefficient of Food",          "parent_code": "QC", "unit": "—"},
    {"code": "FI",    "label": "Food Insecurity Experience Scale",      "parent_code": "QC", "unit": "%"}
  ],
  "links": [
    {"rel": "self",   "href": ".../faostat-indicators/children?parent=QC&limit=5&offset=0"},
    {"rel": "next",   "href": ".../faostat-indicators/children?parent=QC&limit=5&offset=5"},
    {"rel": "parent", "href": ".../faostat-indicators/members?code=QC"}
  ]
}
```

## indicator-tree — `/ancestors?member=QC001`

```json
{
  "dimension": "faostat-indicators",
  "member": "QC001",
  "ancestors": [
    {"code": "QC",    "label": "Food Security",               "parent_code": null},
    {"code": "QC001", "label": "Dietary Energy Supply (DES)", "parent_code": "QC"}
  ]
}
```

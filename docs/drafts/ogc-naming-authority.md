# OGC Naming Authority Registration Draft

**Target:** OGC Naming Authority (OGC-NA)
**Procedure:** OGC doc 09-046r6 (Naming Authority Policies and Procedures)
**Related SWGs:** Temporal WKT for Calendars SWG, GeoDataCube SWG

---

## Requested registrations

### Generator algorithm definitions

Register dimension generator algorithm definitions under the OGC Definition Server namespace. Each definition includes the algorithm specification, edge cases, notation system, and a link to the reference implementation.

**Proposed URI pattern:**

```
http://www.opengis.net/def/generator/ogc/0/{algorithm-name}
```

### Individual registrations

#### 1. Dekadal Generator

| Field | Value |
|---|---|
| **URI** | `http://www.opengis.net/def/generator/ogc/0/dekadal` |
| **Label** | Dekadal calendar generator |
| **Description** | Generates dimension members for the dekadal calendar system used in agricultural drought monitoring. Divides each Gregorian month into three periods: days 1-10 (D1), days 11-20 (D2), and day 21 to month-end (D3). Produces 36 periods per year with variable-length D3 (8-11 days). |
| **Notation** | `YYYY-Knn` where nn = 01..36 |
| **Invertible** | Yes (any date maps to exactly one dekad) |
| **Period lengths** | D1: always 10 days. D2: always 10 days. D3: 8 (Feb non-leap), 9 (Feb leap), 10 (30-day months), 11 (31-day months). |
| **Reference implementation** | https://github.com/ccancellieri/ogc-dimensions |
| **Prior art** | cadati (TU Wien, MIT): https://github.com/TUW-GEO/cadati |
| **OpenAPI definition** | `http://www.opengis.net/def/generator/ogc/0/dekadal/openapi.json` |
| **Domain** | Agricultural drought monitoring, food security early warning (FAO ASIS, GIEWS, FEWS NET) |

#### 2. Pentadal-Monthly Generator

| Field | Value |
|---|---|
| **URI** | `http://www.opengis.net/def/generator/ogc/0/pentadal-monthly` |
| **Label** | Month-based pentadal generator |
| **Description** | Divides each Gregorian month into six 5-day periods. P1: days 1-5, P2: days 6-10, P3: days 11-15, P4: days 16-20, P5: days 21-25, P6: day 26 to month-end. Produces 72 periods per year with variable-length P6 (3-6 days). Used by CHIRPS, CDT, and FAO. |
| **Notation** | `YYYY-Pnn` where nn = 01..72 |
| **Invertible** | Yes |
| **Period lengths** | P1-P5: always 5 days. P6: 3 (Feb non-leap), 4 (Feb leap), 5 (30-day months), 6 (31-day months). |
| **Reference implementation** | https://github.com/ccancellieri/ogc-dimensions |
| **OpenAPI definition** | `http://www.opengis.net/def/generator/ogc/0/pentadal-monthly/openapi.json` |
| **Domain** | Precipitation monitoring (CHIRPS, Climate Data Tools), agricultural statistics (FAO) |

#### 3. Pentadal-Annual Generator

| Field | Value |
|---|---|
| **URI** | `http://www.opengis.net/def/generator/ogc/0/pentadal-annual` |
| **Label** | Year-based pentadal generator |
| **Description** | Counts consecutive 5-day periods from January 1. Periods 1-72 each cover exactly 5 days. Period 73 covers the remaining 5 days (non-leap year) or 6 days (leap year). Produces 73 periods per year. Used by GPCP and CPC/NOAA. |
| **Notation** | `YYYY-Ann` where nn = 01..73 |
| **Invertible** | Yes |
| **Period lengths** | A01-A72: always 5 days. A73: 5 (non-leap) or 6 (leap year). |
| **Reference implementation** | https://github.com/ccancellieri/ogc-dimensions |
| **OpenAPI definition** | `http://www.opengis.net/def/generator/ogc/0/pentadal-annual/openapi.json` |
| **Domain** | Global precipitation (GPCP), climate monitoring (CPC/NOAA) |

#### 4. Integer-Range Generator

| Field | Value |
|---|---|
| **URI** | `http://www.opengis.net/def/generator/ogc/0/integer-range` |
| **Label** | Integer range generator |
| **Description** | Generates integer dimension members from a minimum, maximum, and step. Applicable to elevation bands, percentile bins, quality flags, and other regularly-spaced integer dimensions. |
| **Notation** | Plain integers |
| **Invertible** | Yes (any integer maps to exactly one bin) |
| **Parameters** | `min` (integer), `max` (integer), `step` (integer, default 1) |
| **Reference implementation** | https://github.com/ccancellieri/ogc-dimensions |
| **OpenAPI definition** | `http://www.opengis.net/def/generator/ogc/0/integer-range/openapi.json` |
| **Domain** | Elevation bands, percentile bins, quality flags, index ranges |

### SKOS RDF structure

Each registered algorithm SHOULD include a SKOS concept scheme entry:

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ogcgen: <http://www.opengis.net/def/generator/ogc/0/> .

ogcgen:dekadal a skos:Concept ;
    skos:prefLabel "Dekadal calendar generator"@en ;
    skos:definition "Generates dimension members for the dekadal calendar system. Divides each Gregorian month into three periods (days 1-10, 11-20, 21 to month-end). 36 periods per year."@en ;
    skos:notation "dekadal" ;
    skos:broader <http://www.opengis.net/def/generator/ogc/0> ;
    skos:related <http://www.opengis.net/def/trs/ogc/0/dekadal> .
```

### Coordination

- **Temporal WKT SWG**: The dekadal and pentadal definitions overlap with the Temporal WKT SWG scope for non-Gregorian calendar systems. Coordinate to ensure the generator definitions and temporal reference system definitions are aligned.
- **GDC SWG**: The generator concept is proposed as a conformance class for the GeoDataCube API profile.

## Submitter

Carlo Cancellieri, FAO, OGC Member

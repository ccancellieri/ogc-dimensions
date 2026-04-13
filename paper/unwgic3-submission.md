# UNWGIC-3 Submission Package

**Form:** https://forms.gle/SVw5EzfZc4nBa3C1A
**Deadline:** ~24 April 2026
**Framing:** GeoID-led (platform primary; OGC Dimensions cited as standards-leadership proof point)
**Status:** DRAFT — ready for copy-paste. Final track choice and word-count trim depend on the form fields.

---

## Title (pick one when submitting)

**A. Mission + platform (recommended default)**
> GeoID: An Open-Source United Nations Spatial Data Infrastructure for Food Security, SDG Monitoring, and OGC Standards Leadership

**B. IGIF-coded**
> From Local Agencies to the Global Village: An Open-Source IGIF Reference Implementation Built at FAO and Deployed Across the UN System

**C. Mission-forward (Dimensions-led, fallback only if a Standards track is announced)**
> From Dekads to Dashboards: An Open Geospatial Platform for UN-Scale Food Security Monitoring and Datacube Interoperability

---

## Author

```
Carlo Cancellieri
Lead Software Engineer, Agro-Informatics Platform
Food and Agriculture Organization of the United Nations (FAO)

Affiliations: Open Geospatial Consortium (OGC) member; ISO/TC 211 contributor
Public profile: https://ccancellieri.github.io
GitHub: https://github.com/ccancellieri  (also @un-fao, @FAOSTAT, @ISO-TC211, @OPENDAP)
LinkedIn: https://linkedin.com/in/ccancellieri
```

*Privacy:* Do NOT include email or phone in the form (only LinkedIn / GitHub / ORCID-style identifiers, per global privacy policy).

---

## Abstract — long form (~360 words)

The United Nations Integrated Geospatial Information Framework (IGIF) calls on Member States to build modern, interoperable spatial data infrastructures (SDIs) for sustainable development. Implementing that vision is hard: most operational geospatial platforms in the UN system are bespoke, vendor-coupled, and difficult for national agencies to replicate. We present **GeoID**, the open-source SDI that powers the Agro-Informatics Platform of the Food and Agriculture Organization of the United Nations (FAO) — a cloud-native, multi-tenant catalog and processing stack supporting agricultural monitoring, food-security early warning, and Sustainable Development Goal (SDG) indicator publication across the FAO Hand-in-Hand Initiative and partner ministries.

GeoID is built end-to-end on open standards (Open Geospatial Consortium (OGC) API — Features, Records, Processes, Environmental Data Retrieval (EDR), Coverages; the SpatioTemporal Asset Catalog (STAC); and statistical-to-geospatial bridges) and open infrastructure (PostgreSQL/PostGIS, GeoParquet/Iceberg, Cloud Run / Kubernetes, Keycloak-based identity and access management). It is designed to be **forkable by a national mapping or statistical agency** rather than consumed as a service: every component is publicly licensed (Apache-2.0), every data flow is standards-typed, and every authentication boundary is OpenID Connect–pluggable. The same codebase serves FAO's review and production environments and is being made available to partner organizations as a catalog backbone.

Operating GeoID at UN scale surfaced a recurring obstacle that no current standard solves: cube *dimensions* — time, space, indicator, administrative unit — must today be embedded inline in collection metadata, which is impractical when a single dimension carries 9,000+ time steps (daily climate), 10,000+ indicators (FAOSTAT), 40,000+ thesaurus concepts (AGROVOC), or 50,000+ administrative units (GAUL). The non-Gregorian "dekadal" (36/year) and "pentadal" (72/year or 73/year) calendars used worldwide for food-security monitoring — operationalised inside the UN system by earlier FAO services such as the Agricultural Stress Index System (ASIS) — cannot be expressed in ISO 8601 at all. As a contribution back to the standards community, GeoID has produced and now deploys in production a backwards-compatible **OGC API — Records profile** for datacube dimensions: five OGC Building Blocks plus three additions to the STAC Datacube Extension that introduce paginated, algorithmically-generated, hierarchical, and bijectively invertible dimension members — closing gaps documented across nine surveyed standards and four OGC Testbeds (TB 17–20, including the 44% interoperability finding of OGC 24-037).

The Congress audience is invited to consider GeoID both as a deployable open SDI for IGIF action plans and as evidence that operational UN platforms can credibly upstream the standards advances the geospatial community needs.

---

## Abstract — short/elevator (~120 words)

GeoID is the open-source spatial data infrastructure powering FAO's Agro-Informatics Platform: a cloud-native, multi-tenant, fully OGC/STAC-compliant catalog and processing stack designed to be forked by national agencies pursuing IGIF-aligned modernization. Live across FAO services for food-security monitoring and SDG indicators under the Hand-in-Hand Initiative, GeoID has produced and now deploys a concrete contribution back to the standards community — an OGC API — Records profile that solves long-standing scalability gaps in geospatial datacube *dimensions* (paginated, algorithmic, hierarchical, invertible) — validated against FAO's own dekadal and pentadal calendars, FAOSTAT indicators, and GAUL administrative hierarchies. The talk presents both the platform and the standards advancement it enabled.

---

## Speaker bio (~100 words)

Carlo Cancellieri is Lead Software Engineer for FAO's Agro-Informatics Platform (United Nations), where he architects **GeoID**, the open-source spatial data infrastructure underpinning agricultural monitoring and food-security services across 50+ countries under the Hand-in-Hand Initiative. An OGC member and ISO/TC 211 contributor with 20+ years of geospatial engineering — including core contributions to GeoServer and a Google Summer of Code project (OPeNDAP SQL handler) still in production after fifteen years — he focuses on building open, replicable UN-scale data platforms and on upstreaming the OGC and STAC standards advances that operational UN deployments require.

---

## Keywords (≤ 6)

`open SDI, IGIF implementation, FAO Agro-Informatics, SDG monitoring, OGC API and STAC, food security`

---

## Track mapping (pick when you see the form's options)

| Form track | Pick if… |
|---|---|
| IGIF / SDI / National geospatial infrastructure | **default** — GeoID as forkable IGIF reference implementation |
| SDG monitoring / Data integration | lead with Hand-in-Hand + FAOSTAT indicator publication |
| EO / Climate / Food Security | lead with dekadal monitoring + agricultural stress index operational use |
| Capacity development / Open source | emphasise Apache-2.0, OIDC-pluggable IAM, no vendor lock-in |
| Standards & Interoperability | move the OGC Dimensions paragraph to the top; demote platform context |

---

## Supporting links

- Platform (primary): https://github.com/un-fao/geoid
- Catalog engine (standalone): https://github.com/un-fao/dynastore
- Live deployment: https://data.review.fao.org/geospatial/v2/api/tools/docs
- Standards contribution (spec & paper): https://github.com/ccancellieri/ogc-dimensions
- Author profile: https://ccancellieri.github.io
- OGC lineage: GDC SWG charter 22-052; TB-19 ER 23-047; TB-20 ER 24-035; STAC as OGC Community Standard Oct 2025 (25-004, 25-005)

---

## Pre-submission checklist

- [ ] Open the form and read the actual fields / word limit; trim the long abstract if capped below 360 words
- [ ] Confirm acronyms spelled out on first use: SDG, OGC, STAC, FAO, SDMX, GAUL, ASIS, CHIRPS, GPCP, NOAA, IGIF, EDR, GeoDataCube, SWG, openEO, AGROVOC, SKOS
- [ ] Load `https://data.review.fao.org/geospatial/v2/api/tools/docs` in a browser on the day of submission to confirm the deployment is live
- [ ] Submit at least 48h before 24 April 2026
- [ ] After submitting, add a "Submitted" section at the top of this file with the timestamp, the chosen title, and the chosen track

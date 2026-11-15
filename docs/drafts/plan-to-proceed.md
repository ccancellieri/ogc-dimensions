# Plan-to-Proceed: datacube #36 Decomposition (Superseded)

> **STATUS — SUPERSEDED (November 2026):** Standalone `ogc-dimensions` pagination has been **withdrawn** (no further software development on `reference-implementation/`). The active community resolution — preserving `size`, UAD `definition` + `variableType`, and evolving to **standard OGC API – EDR `/collections/{cid}/items` + CQL2 `S_INTERSECTS` + `f=CoverageJSON` (`Domain`)** — is documented in [`../EDR_SPARSE_TILE_CUBES_PROPOSAL.md`](../EDR_SPARSE_TILE_CUBES_PROPOSAL.md).

**Objective:** Resolve fmigneault's decomposition request (comment 4577791012) while preserving the OGC API-Dimensions spec whole, minimizing external footprint, and landing exactly two optional additive fields in stac-extensions/datacube.

---

## Ordered Steps

### Step 1 — Post the reply to datacube #36

Draft target: `docs/drafts/stac-datacube-issue.md` (or a fresh comment block).

Content spine (see REPLY SPINE in strategic context):
1. Open with concession: agree datacube should not carry 7 concerns.
2. Reframe: spec is standalone, live, v1.0-candidate; only a thin discovery hook is needed.
3. Adopt fmigneault's UAD pointer: `definition` URI + `variableType` enum; drop our `provider` field proposal from the datacube ask.
4. Gently correct the dekadal/duration misread.
5. Disambiguate `product:acquisition_type` (one sentence).
6. Close with the minimal ask: two optional fields, offer a focused PR or piggybacking on #31.

**Gate:** reply must be posted before opening any fragment issues, so fragment issue URLs can be cross-linked in the reply if desired (or cross-link after).

---

### Step 2 — Reshape the OGC API-Dimensions draft (spec-internal, no external footprint)

Edits confined to `ccancellieri/ogc-dimensions`:

| Change | File(s) | What to do |
|---|---|---|
| Drop bespoke nominal/ordinal vocabulary | `spec/schema/provider.json`, spec prose | Remove or rename fields encoding Stevens scale; replace with UAD `variableType` enum values: `continuous | numericalOrdinal | numericalNominal | categoricalOrdinal | categoricalNominal` |
| Adopt UAD `definition` as the link-out pattern | provider schema + spec prose | Document that the Dimensions collection endpoint URL IS a valid `definition` URI; add note that `reference_system` is the prose gloss in OGC API-Common; `definition` is the schema property |
| Add disambiguation sentence for `product` extension | spec prose (§ on nominal types) | One sentence: `product:acquisition_type = "nominal"` is an EO acquisition term; unrelated to a nominal measurement scale |
| Align link-relation names to #1386 tracking note | hierarchy spec section | Add a non-normative note: if/when stac-spec #1386 (`ancestor`/`descendant` rel types) lands, align our link-relation naming to avoid implementor confusion; our endpoints operate on dimension *members* (one layer below collection-level rels) |

No backward-compatibility risk: OGC API-Dimensions is a draft with no prior adopters locked in.

---

### Step 3 — Open fragment tracking issues in `ccancellieri/ogc-dimensions`

One issue per concern. These are internal tracking tickets, not external opens.

| Issue title | Label | Action |
|---|---|---|
| `[track] values-scaling: align /extent cardinality field name to datacube #31 resolution` | `interop` | Watch #31; once maintainer picks `size` or `count`, update `/extent` response schema to match. |
| `[track] dekadal-temporal: document ISO 8601 duration gap + daily-period bridge` | `spec` | Add a short normative note in the temporal dimension section explaining why `step:null+values` is insufficient for dekadal calendar rules, and how `daily-period+calendar` fills the gap. |
| `[track] provider-uad-reshape: adopt UAD variableType + definition link-out` | `spec` | Tracks Step 2 above; close when provider.json and spec prose are updated. |
| `[track] multi-language: per-member labels have no home in stac-extensions/language` | `interop` | No external action. Note in spec that document-level i18n defers to stac-extensions/language; per-member `labels` map is out of scope for that extension. |
| `[track] sorting: reference stac-api-extensions/sort as prior art` | `spec` | Add a non-normative reference to sort ext v1.1.0; document why scope prevents conformance claim. |
| `[track] hierarchy: align with stac-spec #1374 / fmigneault PR #1386` | `interop` | Watch #1386; align link-relation naming when it lands. No datacube ask. |
| `[track] building-blocks: decomposition complete — monitor datacube delta PR` | `meta` | Close when datacube delta PR (Step 4) merges or is formally declined. |

---

### Step 4 — File the datacube delta issue/PR (the ONLY external ask)

**Target repo:** stac-extensions/datacube

**Scope (non-negotiable, nothing else):**

1. **`size: integer` (or `count`)** on all dimension objects — total member cardinality.
   - Resolves issue #31 directly; coordinate with jsignell / m-mohr on naming.
   - Option: fold into the #31 thread rather than opening a new issue.

2. **UAD `definition` link-out** — a single optional string/uri field on dimension objects.
   - Semantics: OGC API-Common Part 2 UAD `definition` (a URI for the semantic concept).
   - Dereferenceable to: an OGC API-Dimensions collection endpoint (or any semantic URI).
   - Optionally: accept `variableType` enum alongside (reuse UAD vocabulary rather than inventing one).

**PR strategy:**
- One small PR, two fields, both `required: false`, no existing field touched.
- PR description: cite UAD definition source (opengeospatial/ogcapi-common schema), cite #31 for `size`/`count`, link to deployed OGC API-Dimensions endpoint as a concrete `definition` URI example.
- If maintainer prefers to fold `size` into #31 thread: open only the `definition` PR; reference #31 explicitly.

---

### Step 5 — Cross-link everything

After Step 1 (reply posted) and Step 3 (fragment issues opened):
- Edit the datacube #36 reply (or add a follow-up comment) linking to each fragment issue in `ccancellieri/ogc-dimensions`.
- After Step 4 (datacube PR filed): link the PR number back into the `[track] building-blocks` fragment issue.
- Update `docs/drafts/stac-datacube-issue.md` with the final state of each concern for future reference.

---

## Decomposition Table

| # | Concern | Home | Action | External footprint |
|---|---|---|---|---|
| 1 | values-scaling (`size`/`count`) | **datacube** + our `/extent` | File datacube PR (fold into #31 if preferred); align field name in our schema once #31 settles | **Yes** — one field in datacube PR; watch #31 |
| 2 | dekadal-temporal | **OGC API-Dimensions spec** | Add normative note on ISO 8601 duration gap; `daily-period+calendar` is the rule carrier; reachable via `definition` link-out | **No** — spec prose only; link-out covers discovery |
| 3 | provider / nominal / ordinal | **OGC API-Dimensions spec** (reshape) + **datacube** (link-out only) | Drop bespoke vocabulary; adopt UAD `variableType`; `definition` URI is the bridge (the second field in the datacube PR) | **Yes** — one field in datacube PR (`definition` URI) |
| 4 | multi-language | **OGC API-Dimensions spec** | Keep per-member `labels` in our spec; cite stac-extensions/language for document-level only; note gap explicitly | **No** — no external issue; no datacube ask |
| 5 | sorting | **OGC API-Dimensions spec** | Reference stac-api-extensions/sort v1.1.0 as prior art; document scope incompatibility; define in our spec | **No** — reference only, no conformance claim |
| 6 | hierarchy | **OGC API-Dimensions spec** + watch #1374/#1386 | Align link-relation naming when #1386 lands; no datacube ask | **No** — watch only; no new external issue |
| 7 | building-blocks (meta) | **ccancellieri/ogc-dimensions** tracking | Concede decomposition; reframe: standalone spec + thin bridge; fragment/track in personal repo | **No** — only the datacube delta PR from #1+#3 |

---

## Net External Footprint

- **stac-extensions/datacube:** one PR, two optional additive fields (`size`/`count` and `definition` URI). Nothing else.
- **stac-spec #1374 / #1386:** watch-only; no new issue opened.
- **stac-api-extensions/sort:** reference-only; no issue opened.
- **stac-extensions/language:** reference-only; no issue opened.

---

## Key References

| Resource | Path / URL |
|---|---|
| OGC API-Dimensions spec repo | `ccancellieri/ogc-dimensions` (this repo) |
| Live deployment | `https://tellurion-stac-harvest-demo.onrender.com/public/records/catalogs/default/dimensions/` (supersedes decommissioned `data.review.fao.org`) |
| provider schema | `spec/schema/provider.json` |
| datacube issue draft | `docs/drafts/stac-datacube-issue.md` |
| datacube PR draft | `docs/drafts/stac-datacube-pr.md` |
| fmigneault decomposition comment | stac-extensions/datacube #36, comment 4577791012 |
| UAD definition schema | `opengeospatial/ogcapi-common` `.../additionalDimensionExtent.yaml` |
| datacube values-scaling issue | stac-extensions/datacube #31 |
| stac-spec hierarchy discussion | stac-spec #1374 |
| fmigneault hierarchy PR | stac-spec #1386 (opened 2026-06-01) |
| sort ext prior art | stac-api-extensions/sort v1.1.0 |
| language ext prior art | stac-extensions/language, stac-api-extensions/language |
| product ext disambiguation | stac-extensions/product (`acquisition_type` field) |

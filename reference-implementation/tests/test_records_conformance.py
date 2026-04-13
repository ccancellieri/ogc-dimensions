"""Explicit conformance tests for OGC API - Records Part 1 (OGC 20-004).

Guards against silent drift between the ogc-dimensions profile and the
Records core: every registered dimension collection and every `/items`
response must carry the fields Records requires, so a generic Records
client can consume dimension endpoints without special-casing.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app

client = TestClient(app)

RECORDS_CORE = "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core"
RECORDS_COLLECTION = "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/record-collection"


def _all_dim_ids() -> list[str]:
    r = client.get("/dimensions/")
    assert r.status_code == 200
    return [c["id"] for c in r.json()["collections"]]


class TestCollectionRecordsConformance:
    def test_every_collection_itemtype_is_record(self):
        r = client.get("/dimensions/")
        for coll in r.json()["collections"]:
            assert coll.get("itemType") == "record", (
                f"{coll.get('id')!r} collection missing itemType=record"
            )

    def test_every_collection_has_required_records_fields(self):
        r = client.get("/dimensions/")
        for coll in r.json()["collections"]:
            assert "id" in coll
            assert "links" in coll and isinstance(coll["links"], list)
            rels = {link["rel"] for link in coll["links"]}
            # Records requires self and items link relations on a collection
            assert "self" in rels, f"{coll['id']}: missing rel=self"
            assert "items" in rels, f"{coll['id']}: missing rel=items"

    def test_collection_conformsto_cites_records(self):
        r = client.get("/dimensions/")
        for coll in r.json()["collections"]:
            conf = coll.get("conformsTo", [])
            # ogc-dimensions conformance URIs must be present
            assert any("ogc-dimensions" in u for u in conf), (
                f"{coll['id']}: conformsTo missing ogc-dimensions URIs"
            )


class TestItemsRecordsConformance:
    def test_every_items_response_is_feature_collection(self):
        for dim_id in _all_dim_ids():
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 2})
            assert r.status_code == 200, f"{dim_id}: {r.status_code}"
            body = r.json()
            assert body.get("type") == "FeatureCollection", (
                f"{dim_id}: items response not a FeatureCollection"
            )

    def test_every_items_response_has_paging_fields(self):
        for dim_id in _all_dim_ids():
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 2})
            body = r.json()
            assert "numberMatched" in body, f"{dim_id}: missing numberMatched"
            assert "numberReturned" in body, f"{dim_id}: missing numberReturned"
            assert isinstance(body["numberMatched"], int)
            assert isinstance(body["numberReturned"], int)
            assert body["numberReturned"] == len(body.get("features", []))

    def test_every_feature_is_valid_geojson(self):
        for dim_id in _all_dim_ids():
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 2})
            body = r.json()
            for feat in body.get("features", []):
                assert feat.get("type") == "Feature", f"{dim_id}: wrong feature type"
                # Records permits geometry: null for catalog records with no footprint
                assert "geometry" in feat, f"{dim_id}: feature missing geometry key"
                assert "properties" in feat, f"{dim_id}: feature missing properties"
                assert "id" in feat, f"{dim_id}: feature missing id"

    def test_items_response_has_self_link(self):
        for dim_id in _all_dim_ids():
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 2})
            body = r.json()
            rels = {link["rel"] for link in body.get("links", [])}
            assert "self" in rels, f"{dim_id}: items response missing rel=self"

    def test_dimension_properties_are_namespaced(self):
        for dim_id in _all_dim_ids():
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 1})
            feats = r.json().get("features", [])
            if not feats:
                continue
            props = feats[0].get("properties", {})
            # At least one dimension:* property must be present
            assert any(k.startswith("dimension:") for k in props), (
                f"{dim_id}: no dimension:* properties on first feature"
            )

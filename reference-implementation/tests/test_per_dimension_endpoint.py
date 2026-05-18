"""Tests for the singular ``GET /dimensions/{id}`` endpoint.

Verifies the documented client flow ``cube:dimensions[*].provider.href``
resolves end-to-end against the same payload as the listing.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app

client = TestClient(app)


def _list_collection(dim_id: str) -> dict:
    r = client.get("/dimensions/")
    assert r.status_code == 200
    return next(c for c in r.json()["collections"] if c["id"] == dim_id)


class TestSingularEndpoint:
    def test_returns_200_for_known_dimension(self):
        r = client.get("/dimensions/dekadal")
        assert r.status_code == 200

    def test_returns_404_for_unknown_dimension(self):
        r = client.get("/dimensions/does-not-exist")
        assert r.status_code == 404

    def test_payload_matches_listing(self):
        r = client.get("/dimensions/dekadal")
        assert r.status_code == 200
        singular = r.json()
        listed = _list_collection("dekadal")
        # Same shape - id, itemType, provider, conformsTo, cube:dimensions
        assert singular["id"] == listed["id"]
        assert singular["itemType"] == listed["itemType"]
        assert singular["provider"] == listed["provider"]
        assert singular["conformsTo"] == listed["conformsTo"]
        assert singular["cube:dimensions"] == listed["cube:dimensions"]

    def test_has_items_link(self):
        r = client.get("/dimensions/dekadal")
        data = r.json()
        rels = [link["rel"] for link in data["links"]]
        assert "items" in rels
        items_link = next(lk for lk in data["links"] if lk["rel"] == "items")
        assert items_link["href"].endswith("/dimensions/dekadal/items")

    def test_self_link_points_to_singular(self):
        r = client.get("/dimensions/dekadal")
        data = r.json()
        self_link = next(lk for lk in data["links"] if lk["rel"] == "self")
        assert self_link["href"].endswith("/dimensions/dekadal")

    def test_resolves_for_every_registered_dimension(self):
        listing = client.get("/dimensions/").json()
        for coll in listing["collections"]:
            dim_id = coll["id"]
            r = client.get(f"/dimensions/{dim_id}")
            assert r.status_code == 200, f"{dim_id} did not resolve"
            assert r.json()["id"] == dim_id

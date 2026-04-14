"""Integration tests for the FastAPI routes.

Validates OGC Records response format: FeatureCollection envelopes,
GeoJSON Feature members with dimension:* properties, and pagination links.
"""

import pytest
from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app

client = TestClient(app)


class TestConformance:
    def test_conformance_uris(self):
        r = client.get("/dimensions/conformance")
        assert r.status_code == 200
        data = r.json()
        uris = data["conformsTo"]
        assert "http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core" in uris
        assert "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/core" in uris
        assert "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-member" in uris


class TestListDimensions:
    def test_list_returns_collections(self):
        r = client.get("/dimensions/")
        assert r.status_code == 200
        data = r.json()
        dim_ids = [d["id"] for d in data["collections"]]
        assert "dekadal" in dim_ids
        assert "world-admin" in dim_ids

    def test_collection_has_item_type_record(self):
        r = client.get("/dimensions/")
        data = r.json()
        dek = next(d for d in data["collections"] if d["id"] == "dekadal")
        assert dek["itemType"] == "record"

    def test_collection_has_cube_dimensions(self):
        r = client.get("/dimensions/")
        data = r.json()
        dek = next(d for d in data["collections"] if d["id"] == "dekadal")
        # Full provider details at collection level
        assert dek["provider"]["config"] == {"period_days": 10, "scheme": "monthly"}
        # Slim provider reference inside cube:dimensions
        cube_dim = dek["cube:dimensions"]["dekadal"]
        assert cube_dim["provider"]["type"] == "daily-period"
        assert cube_dim["type"] == "temporal"

    def test_collection_has_links(self):
        r = client.get("/dimensions/")
        data = r.json()
        dek = next(d for d in data["collections"] if d["id"] == "dekadal")
        rels = [l["rel"] for l in dek["links"]]
        assert "self" in rels
        assert "items" in rels
        assert "queryables" in rels

    def test_temporal_collection_has_extent(self):
        r = client.get("/dimensions/")
        data = r.json()
        dek = next(d for d in data["collections"] if d["id"] == "dekadal")
        assert "extent" in dek
        assert "temporal" in dek["extent"]


class TestItems:
    def test_feature_collection_envelope(self):
        r = client.get("/dimensions/dekadal/items?limit=3")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert data["numberMatched"] == 36
        assert data["numberReturned"] == 3
        assert len(data["features"]) == 3

    def test_member_is_geojson_feature(self):
        r = client.get("/dimensions/dekadal/items?limit=1")
        data = r.json()
        feature = data["features"][0]
        assert feature["type"] == "Feature"
        assert feature["id"] == "2024-K01"
        assert feature["geometry"] is None
        props = feature["properties"]
        assert props["type"] == "dimension-member"
        assert props["dimension:type"] == "temporal"
        assert props["dimension:code"] == "2024-K01"
        assert props["dimension:index"] == 0
        assert "time" in props
        assert props["time"]["interval"] == ["2024-01-01", "2024-01-10"]

    def test_sort_dir_desc(self):
        r = client.get("/dimensions/dekadal/items?limit=1&sort_dir=desc")
        data = r.json()
        assert data["features"][0]["id"] == "2024-K36"

    def test_pagination_links(self):
        r = client.get("/dimensions/dekadal/items?limit=10&offset=0")
        data = r.json()
        rels = [l["rel"] for l in data["links"]]
        assert "self" in rels
        assert "next" in rels
        assert "collection" in rels

    def test_hierarchical_members_have_links(self):
        r = client.get("/dimensions/world-admin/items")
        data = r.json()
        feature = data["features"][0]
        assert "links" in feature
        rels = [l["rel"] for l in feature["links"]]
        assert "children" in rels
        assert "ancestors" in rels
        assert "self" in rels

    def test_hierarchical_member_properties(self):
        r = client.get("/dimensions/world-admin/items")
        data = r.json()
        feature = data["features"][0]
        props = feature["properties"]
        assert props["dimension:type"] == "nominal"
        assert "dimension:level" in props
        assert props["dimension:has_children"] is True

    def test_language_header(self):
        r = client.get("/dimensions/world-admin/items?language=fr")
        assert r.status_code == 200
        assert r.headers.get("content-language") == "fr"

    def test_integer_range_member(self):
        r = client.get("/dimensions/integer-range/items?limit=1")
        data = r.json()
        feature = data["features"][0]
        props = feature["properties"]
        assert props["dimension:type"] == "other"
        assert "dimension:start" in props
        assert "dimension:end" in props


class TestExtent:
    def test_dekadal_extent(self):
        r = client.get("/dimensions/dekadal/extent")
        assert r.status_code == 200
        data = r.json()
        assert data["size"] == 36

    def test_integer_range_extent(self):
        r = client.get("/dimensions/integer-range/extent")
        data = r.json()
        assert data["size"] == 51


class TestInverse:
    def test_dekadal_inverse(self):
        r = client.get("/dimensions/dekadal/inverse?value=2024-01-15")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "Feature"
        assert data["id"] == "2024-K02"

    def test_integer_range_inverse(self):
        r = client.get("/dimensions/integer-range/inverse?value=1234")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "Feature"
        assert data["id"] == "1200"

    def test_inverse_invalid_returns_error(self):
        r = client.get("/dimensions/dekadal/inverse?value=not-a-date")
        assert r.status_code == 404
        data = r.json()
        assert "code" in data
        assert "description" in data

    def test_non_invertible_501(self):
        r = client.get("/dimensions/world-admin/inverse?value=AFR")
        assert r.status_code == 501

    def test_batch_inverse(self):
        r = client.post(
            "/dimensions/dekadal/inverse",
            json={"values": ["2024-01-05", "2024-01-15"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert data["numberMatched"] == 2
        assert data["numberReturned"] == 2
        assert len(data["features"]) == 2
        assert data["errors"] == []
        assert data["features"][0]["type"] == "Feature"

    def test_batch_inverse_with_errors(self):
        r = client.post(
            "/dimensions/dekadal/inverse",
            json={"values": ["2024-01-15", "not-a-date"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["numberMatched"] == 1
        assert len(data["features"]) == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["value"] == "not-a-date"
        assert "code" in data["errors"][0]


class TestSearch:
    def test_exact(self):
        r = client.get("/dimensions/dekadal/search?exact=2024-K01")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert data["numberMatched"] == 1
        assert data["features"][0]["id"] == "2024-K01"

    def test_range(self):
        r = client.get("/dimensions/dekadal/search?min=2024-K01&max=2024-K03")
        data = r.json()
        assert data["numberMatched"] == 3

    def test_like_tree(self):
        r = client.get("/dimensions/world-admin/search?like=*Ken*")
        data = r.json()
        assert data["numberMatched"] >= 1

    def test_missing_params_400(self):
        r = client.get("/dimensions/dekadal/search")
        assert r.status_code == 400


class TestChildren:
    def test_children_feature_collection(self):
        r = client.get("/dimensions/world-admin/children?parent=AFR")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert data["numberMatched"] > 0
        # All children should be Features
        for feature in data["features"]:
            assert feature["type"] == "Feature"
            assert feature["geometry"] is None

    def test_children_non_hierarchical_501(self):
        r = client.get("/dimensions/dekadal/children?parent=foo")
        assert r.status_code == 501

    def test_children_with_language(self):
        r = client.get("/dimensions/world-admin/children?parent=AFR&language=fr")
        assert r.status_code == 200
        assert r.headers.get("content-language") == "fr"

    def test_children_have_links(self):
        r = client.get("/dimensions/world-admin/children?parent=AFR")
        data = r.json()
        rels = [l["rel"] for l in data["links"]]
        assert "self" in rels
        assert "collection" in rels


class TestAncestors:
    def test_ancestors_feature_collection(self):
        r = client.get("/dimensions/world-admin/ancestors?member=KEN")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "FeatureCollection"
        codes = [f["id"] for f in data["features"]]
        assert codes == ["AFR", "KEN"]

    def test_ancestor_features_are_valid(self):
        r = client.get("/dimensions/world-admin/ancestors?member=KEN")
        data = r.json()
        for feature in data["features"]:
            assert feature["type"] == "Feature"
            assert feature["geometry"] is None
            props = feature["properties"]
            assert "dimension:type" in props
            assert "dimension:code" in props

    def test_ancestors_not_found_404(self):
        r = client.get("/dimensions/world-admin/ancestors?member=NONEXISTENT")
        assert r.status_code == 404


class TestQueryables:
    def test_queryables_response(self):
        r = client.get("/dimensions/dekadal/queryables")
        assert r.status_code == 200
        data = r.json()
        assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "properties" in data
        assert "x-ogc-parameters" in data
        assert "x-ogc-config" in data
        assert data["x-ogc-config"] == {"period_days": 10, "scheme": "monthly"}

    def test_queryables_404(self):
        r = client.get("/dimensions/nonexistent/queryables")
        assert r.status_code == 404

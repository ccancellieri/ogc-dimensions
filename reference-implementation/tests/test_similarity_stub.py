"""dimension-similarity stub — every dimension's /search?similar=... MUST
return the prescribed 501 problem-detail, and the conformance class URI
MUST appear at /conformance.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app
from ogc_dimensions.api.routes import DIMENSIONS

client = TestClient(app)

SIMILARITY_URI = "http://www.opengis.net/spec/ogc-dimensions/1.0/conf/dimension-similarity"
SIMILARITY_ERROR_TYPE = (
    "https://www.opengis.net/spec/ogc-dimensions/1.0/errors/similarity-not-implemented"
)


class TestSimilarityStub:
    def test_conformance_advertises_similarity(self):
        r = client.get("/dimensions/conformance")
        assert r.status_code == 200
        assert SIMILARITY_URI in r.json()["conformsTo"]

    def test_returns_501_problem_detail_for_every_dimension(self):
        for dim_id in DIMENSIONS:
            r = client.get(f"/dimensions/{dim_id}/search", params={"similar": "foo"})
            assert r.status_code == 501, (
                f"{dim_id}: expected 501, got {r.status_code}"
            )
            assert r.headers["content-type"] == "application/problem+json"
            body = r.json()
            assert body["type"] == SIMILARITY_ERROR_TYPE
            assert body["status"] == 501
            assert body["dimension"] == dim_id
            assert "title" in body
            assert "detail" in body

    def test_other_search_protocols_still_work(self):
        """Regression — similar= path MUST NOT intercept exact/range/like."""
        r = client.get(
            "/dimensions/world-admin/search",
            params={"exact": "ITA"},
        )
        # Either 200 (member found) or 200 with empty features — but not 501.
        assert r.status_code != 501

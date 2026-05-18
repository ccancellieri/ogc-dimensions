"""dimension-member BB §"Identifier" — Feature.id MUST equal the natural
key (the dimension's `code`) for every produced member. Guards against
surrogate-UUID drift introduced by future materialisation refactors.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app
from ogc_dimensions.api.routes import DIMENSIONS

client = TestClient(app)


class TestFeatureIdEqualsNaturalKey:
    def test_every_item_feature_id_equals_dimension_code(self):
        for dim_id in DIMENSIONS:
            r = client.get(f"/dimensions/{dim_id}/items", params={"limit": 5})
            assert r.status_code == 200, f"{dim_id} /items failed: {r.status_code}"
            for feat in r.json()["features"]:
                code = feat["properties"]["dimension:code"]
                assert feat["id"] == code, (
                    f"{dim_id}: Feature.id={feat['id']!r} != dimension:code={code!r}"
                )

    def test_inverse_feature_id_equals_code(self):
        # Pick a representative invertible call per dimension.
        for dim_id, cfg in DIMENSIONS.items():
            if not cfg.provider.invertible:
                continue
            for value in ("2024-06-15", "123"):
                r = client.get(
                    f"/dimensions/{dim_id}/inverse", params={"value": value}
                )
                if r.status_code != 200:
                    continue
                feat = r.json()
                assert feat["id"] == feat["properties"]["dimension:code"]
                break

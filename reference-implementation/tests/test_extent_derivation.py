"""dimension-collection BB §"Extent derivation" — extent MUST be derived
from the provider's generator min/max, and the size MUST round-trip
with the items endpoint's numberMatched.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app
from ogc_dimensions.api.routes import DIMENSIONS

client = TestClient(app)


class TestExtentDerivedFromGenerator:
    def test_collection_extent_matches_provider_extent(self):
        for dim_id, cfg in DIMENSIONS.items():
            if not (cfg.extent_min and cfg.extent_max):
                continue
            r = client.get(f"/dimensions/{dim_id}")
            assert r.status_code == 200
            extent = r.json().get("extent")
            ext = cfg.provider.extent(cfg.extent_min, cfg.extent_max)
            if cfg.dimension_type == "temporal":
                assert extent is not None
                assert "temporal" in extent
            else:
                assert extent is not None
                assert "values" in extent
                assert extent["values"]["min"] == ext.native_min
                assert extent["values"]["max"] == ext.native_max

    def test_extent_size_round_trips_with_number_matched(self):
        for dim_id, cfg in DIMENSIONS.items():
            if not (cfg.extent_min and cfg.extent_max):
                continue
            ext = cfg.provider.extent(cfg.extent_min, cfg.extent_max)
            r = client.get(
                f"/dimensions/{dim_id}/items",
                params={"limit": 1, "offset": 0},
            )
            assert r.status_code == 200
            assert ext.size == r.json()["numberMatched"], (
                f"{dim_id}: extent.size={ext.size} != numberMatched="
                f"{r.json()['numberMatched']}"
            )

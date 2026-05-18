"""Conformance test: links[].rel MUST be a subset of provider capabilities.

dimension-member BB §"Link relations" forbids servers from emitting a `rel`
whose corresponding capability is not declared by the provider.
"""

from fastapi.testclient import TestClient

from ogc_dimensions.api.app import app

client = TestClient(app)

# Rels that are always permitted regardless of capability flags.
ALWAYS_REL = {"self", "collection", "items", "queryables", "next", "prev"}

# Rels that are gated on a provider capability.
HIERARCHICAL_REL = {"parent", "children", "ancestors"}
INVERTIBLE_REL = {"inverse"}
SEARCH_REL = {"search"}


def _allowed_rels(provider: dict) -> set[str]:
    allowed = set(ALWAYS_REL)
    if provider.get("invertible"):
        allowed |= INVERTIBLE_REL
    if provider.get("search"):
        allowed |= SEARCH_REL
    if provider.get("hierarchical"):
        allowed |= HIERARCHICAL_REL
    return allowed


def _collect_rels(obj) -> set[str]:
    """Walk JSON, return every `rel` value found in any links[] array."""
    rels: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "links" and isinstance(v, list):
                for lk in v:
                    if isinstance(lk, dict) and "rel" in lk:
                        rels.add(lk["rel"])
            else:
                rels |= _collect_rels(v)
    elif isinstance(obj, list):
        for item in obj:
            rels |= _collect_rels(item)
    return rels


def _registered_dimensions() -> list[tuple[str, dict]]:
    r = client.get("/dimensions/")
    assert r.status_code == 200
    return [(c["id"], c["provider"]) for c in r.json()["collections"]]


class TestLinkRelSubsetOfProviderCapabilities:
    def test_collection_listing_links_are_subset(self):
        for dim_id, provider in _registered_dimensions():
            r = client.get(f"/dimensions/{dim_id}")
            allowed = _allowed_rels(provider)
            rels = _collect_rels(r.json())
            assert rels.issubset(allowed), (
                f"{dim_id}: emitted rels {rels - allowed} not in "
                f"allowed set {allowed} (capabilities: invertible="
                f"{provider.get('invertible')}, hierarchical="
                f"{provider.get('hierarchical')}, search={provider.get('search')})"
            )

    def test_items_response_links_are_subset(self):
        for dim_id, provider in _registered_dimensions():
            r = client.get(f"/dimensions/{dim_id}/items?limit=3")
            if r.status_code != 200:
                continue
            allowed = _allowed_rels(provider)
            rels = _collect_rels(r.json())
            assert rels.issubset(allowed), (
                f"{dim_id}/items: emitted rels {rels - allowed} not allowed "
                f"(allowed: {allowed})"
            )

    def test_inverse_response_links_are_subset(self):
        """Regression: elevation-bands /inverse used to leak rel=ancestors
        even though the provider has hierarchical=false."""
        for dim_id, provider in _registered_dimensions():
            if not provider.get("invertible"):
                continue
            # Pick a value likely to land inside the extent.
            r = client.get(
                f"/dimensions/{dim_id}/inverse",
                params={"value": "2024-06-15"},
            )
            if r.status_code != 200:
                # Non-temporal invertible providers — try an integer value.
                r = client.get(
                    f"/dimensions/{dim_id}/inverse",
                    params={"value": "123"},
                )
            if r.status_code != 200:
                continue
            allowed = _allowed_rels(provider)
            rels = _collect_rels(r.json())
            assert rels.issubset(allowed), (
                f"{dim_id}/inverse: rels {rels - allowed} leaked "
                f"(provider hierarchical={provider.get('hierarchical')})"
            )

    def test_non_hierarchical_never_emits_ancestors_or_children(self):
        for dim_id, provider in _registered_dimensions():
            if provider.get("hierarchical"):
                continue
            for path in (
                f"/dimensions/{dim_id}",
                f"/dimensions/{dim_id}/items?limit=3",
            ):
                r = client.get(path)
                rels = _collect_rels(r.json())
                assert "ancestors" not in rels, f"{path} leaked rel=ancestors"
                assert "children" not in rels, f"{path} leaked rel=children"

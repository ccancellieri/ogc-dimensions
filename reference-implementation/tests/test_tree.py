"""Tests for StaticTreeProvider and LeveledTreeProvider."""

import pytest

from ogc_dimensions.providers.tree import (
    LeveledTreeProvider,
    StaticTreeConfig,
    StaticTreeProvider,
    WORLD_ADMIN_NODES,
)


@pytest.fixture
def tree():
    return StaticTreeProvider()


@pytest.fixture
def leveled():
    return LeveledTreeProvider()


class TestConfig:
    def test_static_tree_config(self, tree):
        assert isinstance(tree.config, StaticTreeConfig)
        assert tree.config_as_dict() == {}

    def test_leveled_inherits_config(self, leveled):
        assert isinstance(leveled.config, StaticTreeConfig)

    def test_provider_types(self, tree, leveled):
        assert tree.provider_type == "static-tree"
        assert leveled.provider_type == "leveled-tree"

    def test_hierarchical(self, tree):
        assert tree.hierarchical is True
        assert tree.invertible is False


class TestMultilingualData:
    def test_continents_have_labels(self, tree):
        roots = tree.generate("", "", limit=10)
        for m in roots.members:
            labels = m.extra.get("labels", {})
            assert "en" in labels, f"{m.code} missing English label"
            assert "fr" in labels, f"{m.code} missing French label"
            assert "ar" in labels, f"{m.code} missing Arabic label"

    def test_countries_have_labels(self, tree):
        children = tree.children("AFR")
        for m in children.members:
            labels = m.extra.get("labels", {})
            assert "en" in labels, f"{m.code} missing English label"
            assert "fr" in labels, f"{m.code} missing French label"

    def test_iso_codes(self):
        """All continents use 3-letter codes."""
        continents = [n for n in WORLD_ADMIN_NODES if n["parent_code"] is None]
        for c in continents:
            assert len(c["code"]) == 3, f"Continent code {c['code']} not 3 chars"


class TestGenerate:
    def test_root_members(self, tree):
        r = tree.generate("", "", limit=10)
        assert r.number_matched == 5
        codes = [m.code for m in r.members]
        assert "AFR" in codes

    def test_has_children_set(self, tree):
        r = tree.generate("", "", limit=10)
        for m in r.members:
            assert m.has_children is True

    def test_parent_delegates_to_children(self, tree):
        r = tree.generate("", "", limit=100, parent="AFR")
        assert r.number_matched > 0
        for m in r.members:
            assert m.extra["parent_code"] == "AFR"


class TestChildren:
    def test_children_of_afr(self, tree):
        r = tree.children("AFR")
        assert r.number_matched > 0
        codes = [m.code for m in r.members]
        assert "KEN" in codes

    def test_sort_by_label_french(self, tree):
        r = tree.children("AFR", sort_by="label", language="fr")
        fr_labels = [m.extra["labels"]["fr"] for m in r.members]
        assert fr_labels == sorted(fr_labels, key=str.casefold)

    def test_sort_dir_desc(self, tree):
        asc = tree.children("AFR", sort_by="code", sort_dir="asc")
        desc = tree.children("AFR", sort_by="code", sort_dir="desc")
        asc_codes = [m.code for m in asc.members]
        desc_codes = [m.code for m in desc.members]
        assert asc_codes == list(reversed(desc_codes))

    def test_no_children(self, tree):
        r = tree.children("KEN")
        assert r.number_matched == 0


class TestAncestors:
    def test_root_ancestor(self, tree):
        chain = tree.ancestors("AFR")
        assert len(chain) == 1
        assert chain[0]["code"] == "AFR"

    def test_country_ancestors(self, tree):
        chain = tree.ancestors("KEN")
        assert len(chain) == 2
        assert chain[0]["code"] == "AFR"
        assert chain[1]["code"] == "KEN"

    def test_not_found(self, tree):
        chain = tree.ancestors("NONEXISTENT")
        assert chain == []


class TestHasChildren:
    def test_continent_has_children(self, tree):
        assert tree.has_children("AFR") is True

    def test_leaf_no_children(self, tree):
        assert tree.has_children("KEN") is False


class TestSearch:
    def test_exact(self, tree):
        r = tree.search(tree.search_protocols[0], "", "", exact="KEN")
        assert len(r.members) == 1
        assert r.members[0].code == "KEN"

    def test_like_pattern(self, tree):
        r = tree.search(tree.search_protocols[1], "", "", like="*Tan*")
        codes = [m.code for m in r.members]
        assert "TZA" in codes  # Tanzania

    def test_like_with_language(self, tree):
        r = tree.search(tree.search_protocols[1], "", "", like="*Afrique*", language="fr")
        codes = [m.code for m in r.members]
        assert "AFR" in codes or "ZAF" in codes  # Afrique or Afrique du Sud


class TestLeveledGenerate:
    def test_level_0(self, leveled):
        r = leveled.generate("", "", level=0)
        assert r.number_matched == 5
        for m in r.members:
            assert m.extra["level"] == 0

    def test_level_1(self, leveled):
        r = leveled.generate("", "", level=1)
        assert r.number_matched > 0
        for m in r.members:
            assert m.extra["level"] == 1

    def test_level_with_parent(self, leveled):
        r = leveled.generate("", "", level=1, parent="EUR")
        for m in r.members:
            assert m.extra["parent_code"] == "EUR"
            assert m.extra["level"] == 1

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

    def test_level_filter_excludes_other_levels(self, leveled):
        """?level=0 MUST NOT leak level-1 members into the response."""
        r = leveled.generate("", "", level=0, limit=1000)
        levels = {m.extra["level"] for m in r.members}
        assert levels == {0}, f"level=0 query returned mixed levels: {levels}"


# ---------------------------------------------------------------------------
# SKOS-like fixture: concept-hierarchy scheme with 3 levels, multilingual labels,
# and cross-level integrity — approximates how AGROVOC / GEMET concept schemes
# look when they are surfaced through ogc-dimensions.
# ---------------------------------------------------------------------------

SKOS_CONCEPTS = [
    {"code": "c_crops", "label": "Crops", "labels": {"en": "Crops", "fr": "Cultures"}, "parent_code": None, "level": 0},
    {"code": "c_livestock", "label": "Livestock", "labels": {"en": "Livestock", "fr": "Bétail"}, "parent_code": None, "level": 0},

    {"code": "c_cereals", "label": "Cereals", "labels": {"en": "Cereals", "fr": "Céréales"}, "parent_code": "c_crops", "level": 1},
    {"code": "c_legumes", "label": "Legumes", "labels": {"en": "Legumes", "fr": "Légumineuses"}, "parent_code": "c_crops", "level": 1},
    {"code": "c_ruminants", "label": "Ruminants", "labels": {"en": "Ruminants", "fr": "Ruminants"}, "parent_code": "c_livestock", "level": 1},

    {"code": "c_wheat", "label": "Wheat", "labels": {"en": "Wheat", "fr": "Blé"}, "parent_code": "c_cereals", "level": 2},
    {"code": "c_maize", "label": "Maize", "labels": {"en": "Maize", "fr": "Maïs"}, "parent_code": "c_cereals", "level": 2},
    {"code": "c_soybean", "label": "Soybean", "labels": {"en": "Soybean", "fr": "Soja"}, "parent_code": "c_legumes", "level": 2},
    {"code": "c_cattle", "label": "Cattle", "labels": {"en": "Cattle", "fr": "Bovins"}, "parent_code": "c_ruminants", "level": 2},
]


@pytest.fixture
def skos_tree():
    return StaticTreeProvider(nodes=SKOS_CONCEPTS)


class TestSKOSLikeHierarchy:
    def test_roots_only_contain_top_concepts(self, skos_tree):
        roots = skos_tree.generate("", "", limit=100)
        codes = {m.code for m in roots.members}
        assert codes == {"c_crops", "c_livestock"}

    def test_cross_level_integrity_every_parent_exists(self, skos_tree):
        """Every non-root parent_code MUST resolve to a node in the scheme."""
        codes = {n["code"] for n in SKOS_CONCEPTS}
        for n in SKOS_CONCEPTS:
            if n["parent_code"] is not None:
                assert n["parent_code"] in codes, (
                    f"{n['code']}: dangling parent_code={n['parent_code']!r}"
                )

    def test_ancestors_depth_matches_level(self, skos_tree):
        """ancestors(leaf) length MUST equal leaf.level + 1 for a well-formed tree."""
        for n in SKOS_CONCEPTS:
            chain = skos_tree.ancestors(n["code"])
            assert len(chain) == n["level"] + 1, (
                f"{n['code']} at level {n['level']} has {len(chain)} ancestors"
            )

    def test_ancestors_path_is_monotonic(self, skos_tree):
        """Ancestor chain for a leaf MUST link root→…→leaf via parent_code."""
        chain = skos_tree.ancestors("c_wheat")
        assert [n["code"] for n in chain] == ["c_crops", "c_cereals", "c_wheat"]

    def test_multilingual_labels_cover_all_nodes(self, skos_tree):
        for n in SKOS_CONCEPTS:
            assert "en" in n["labels"] and "fr" in n["labels"], (
                f"{n['code']}: missing EN/FR label"
            )


class TestCycleRejection:
    def test_self_parent_does_not_loop_forever(self):
        """A node pointing to itself MUST NOT cause ancestors() to hang."""
        cyclic = [
            {"code": "X", "label": "X", "labels": {"en": "X"}, "parent_code": "X", "level": 0},
        ]
        tree = StaticTreeProvider(nodes=cyclic)
        chain = tree.ancestors("X")
        assert len(chain) == 1
        assert chain[0]["code"] == "X"

    def test_two_node_cycle_terminates(self):
        """A → B → A MUST terminate via seen-set guard."""
        cyclic = [
            {"code": "A", "label": "A", "labels": {"en": "A"}, "parent_code": "B", "level": 0},
            {"code": "B", "label": "B", "labels": {"en": "B"}, "parent_code": "A", "level": 0},
        ]
        tree = StaticTreeProvider(nodes=cyclic)
        chain = tree.ancestors("A")
        codes = {n["code"] for n in chain}
        assert codes == {"A", "B"}, (
            f"expected cycle to break with both nodes visited once, got {codes}"
        )

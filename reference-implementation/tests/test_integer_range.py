"""Tests for IntegerRangeProvider."""

import pytest

from ogc_dimensions.providers.base import InverseError
from ogc_dimensions.providers.integer_range import IntegerRangeConfig, IntegerRangeProvider


@pytest.fixture
def gen():
    return IntegerRangeProvider(step=100)


class TestConfig:
    def test_config_type(self, gen):
        assert isinstance(gen.config, IntegerRangeConfig)
        assert gen.config.step == 100
        assert gen.config_as_dict() == {"step": 100}

    def test_provider_type(self, gen):
        assert gen.provider_type == "integer-range"


class TestGenerate:
    def test_51_bands_0_to_5000(self, gen):
        r = gen.generate(0, 5000)
        assert r.number_matched == 51

    def test_first_band(self, gen):
        r = gen.generate(0, 5000, limit=1)
        m = r.members[0]
        assert m.code == "0"
        assert m.extra["lower"] == 0
        assert m.extra["upper"] == 99

    def test_last_band(self, gen):
        r = gen.generate(0, 5000, limit=100)
        last = r.members[-1]
        assert last.code == "5000"
        assert last.extra["lower"] == 5000
        assert last.extra["upper"] == 5000

    def test_sort_dir_desc(self, gen):
        asc = gen.generate(0, 5000, limit=1)
        desc = gen.generate(0, 5000, limit=1, sort_dir="desc")
        assert asc.members[0].code == "0"
        assert desc.members[0].code == "5000"

    def test_step_1(self):
        g = IntegerRangeProvider(step=1)
        r = g.generate(0, 9)
        assert r.number_matched == 10


class TestExtent:
    def test_extent(self, gen):
        ext = gen.extent(0, 5000)
        assert ext.size == 51
        assert ext.native_min == 0
        assert ext.native_max == 5000


class TestInverse:
    def test_inverse_exact_boundary(self, gen):
        inv = gen.inverse("100")
        assert inv.code == "100"
        assert inv.extra["lower"] == 100
        assert inv.extra["upper"] == 199

    def test_inverse_mid_band(self, gen):
        inv = gen.inverse("1234")
        assert inv.code == "1200"

    def test_inverse_zero(self, gen):
        inv = gen.inverse("0")
        assert inv.code == "0"

    def test_inverse_invalid(self, gen):
        with pytest.raises(InverseError) as excinfo:
            gen.inverse("abc")
        assert excinfo.value.code == "InvalidFormat"


class TestSearch:
    def test_exact(self, gen):
        r = gen.search(gen.search_protocols[0], 0, 5000, exact="500")
        assert len(r.members) == 1
        assert r.members[0].code == "500"

    def test_range(self, gen):
        r = gen.search(gen.search_protocols[1], 0, 5000, min=100, max=300)
        codes = [m.code for m in r.members]
        assert codes == ["100", "200", "300"]

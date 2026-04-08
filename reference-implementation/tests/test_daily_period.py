"""Tests for the unified DailyPeriodProvider."""

import pytest

from ogc_dimensions.providers.daily_period import DailyPeriodConfig, DailyPeriodProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dekadal():
    return DailyPeriodProvider(period_days=10, scheme="monthly")


@pytest.fixture
def pentadal_monthly():
    return DailyPeriodProvider(period_days=5, scheme="monthly")


@pytest.fixture
def pentadal_annual():
    return DailyPeriodProvider(period_days=5, scheme="annual")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_dekadal_config(self, dekadal):
        cfg = dekadal.config
        assert isinstance(cfg, DailyPeriodConfig)
        assert cfg.period_days == 10
        assert cfg.scheme == "monthly"
        assert dekadal.config_as_dict() == {"period_days": 10, "scheme": "monthly"}

    def test_pentadal_monthly_config(self, pentadal_monthly):
        assert pentadal_monthly.config_as_dict() == {"period_days": 5, "scheme": "monthly"}

    def test_pentadal_annual_config(self, pentadal_annual):
        assert pentadal_annual.config_as_dict() == {"period_days": 5, "scheme": "annual"}

    def test_provider_type(self, dekadal):
        assert dekadal.provider_type == "daily-period"

    def test_invertible(self, dekadal):
        assert dekadal.invertible is True


# ---------------------------------------------------------------------------
# Monthly scheme — dekadal (10-day)
# ---------------------------------------------------------------------------

class TestDekadalGenerate:
    def test_36_periods_per_year(self, dekadal):
        r = dekadal.generate("2025-01-01", "2025-12-31")
        assert r.number_matched == 36

    def test_january_structure(self, dekadal):
        r = dekadal.generate("2025-01-01", "2025-12-31", limit=3)
        assert r.members[0].code == "2025-K01"
        assert r.members[0].start == "2025-01-01"
        assert r.members[0].end == "2025-01-10"
        assert r.members[1].code == "2025-K02"
        assert r.members[1].start == "2025-01-11"
        assert r.members[1].end == "2025-01-20"
        assert r.members[2].code == "2025-K03"
        assert r.members[2].start == "2025-01-21"
        assert r.members[2].end == "2025-01-31"

    def test_february_non_leap_d3(self, dekadal):
        """D3 of Feb non-leap: 21–28 (8 days)."""
        r = dekadal.generate("2025-01-01", "2025-12-31", limit=36)
        feb_d3 = [m for m in r.members if m.code == "2025-K06"][0]
        assert feb_d3.start == "2025-02-21"
        assert feb_d3.end == "2025-02-28"

    def test_february_leap_d3(self, dekadal):
        """D3 of Feb leap: 21–29 (9 days)."""
        r = dekadal.generate("2024-01-01", "2024-12-31", limit=36)
        feb_d3 = [m for m in r.members if m.code == "2024-K06"][0]
        assert feb_d3.start == "2024-02-21"
        assert feb_d3.end == "2024-02-29"

    def test_multi_year(self, dekadal):
        r = dekadal.generate("2024-01-01", "2025-12-31")
        assert r.number_matched == 72

    def test_sort_dir_desc(self, dekadal):
        asc = dekadal.generate("2025-01-01", "2025-12-31", limit=1)
        desc = dekadal.generate("2025-01-01", "2025-12-31", limit=1, sort_dir="desc")
        assert asc.members[0].code == "2025-K01"
        assert desc.members[0].code == "2025-K36"

    def test_pagination(self, dekadal):
        page1 = dekadal.generate("2025-01-01", "2025-12-31", limit=10, offset=0)
        page2 = dekadal.generate("2025-01-01", "2025-12-31", limit=10, offset=10)
        assert page1.number_returned == 10
        assert page2.number_returned == 10
        assert page1.members[-1].code != page2.members[0].code


class TestDekadalExtent:
    def test_extent_single_year(self, dekadal):
        ext = dekadal.extent("2025-01-01", "2025-12-31")
        assert ext.size == 36
        assert ext.native_min == "2025-K01"
        assert ext.native_max == "2025-K36"
        assert ext.standard_min == "2025-01-01"
        assert ext.standard_max == "2025-12-31"


class TestDekadalInverse:
    @pytest.mark.parametrize("date_str,expected_code", [
        ("2025-01-01", "2025-K01"),
        ("2025-01-10", "2025-K01"),
        ("2025-01-11", "2025-K02"),
        ("2025-01-20", "2025-K02"),
        ("2025-01-21", "2025-K03"),
        ("2025-01-31", "2025-K03"),
        ("2025-02-28", "2025-K06"),
        ("2024-02-29", "2024-K06"),
        ("2025-12-31", "2025-K36"),
    ])
    def test_inverse(self, dekadal, date_str, expected_code):
        inv = dekadal.inverse(date_str)
        assert inv.valid is True
        assert inv.member == expected_code

    def test_inverse_invalid(self, dekadal):
        inv = dekadal.inverse("not-a-date")
        assert inv.valid is False
        assert inv.reason is not None


# ---------------------------------------------------------------------------
# Monthly scheme — pentadal (5-day)
# ---------------------------------------------------------------------------

class TestPentadalMonthlyGenerate:
    def test_72_periods_per_year(self, pentadal_monthly):
        r = pentadal_monthly.generate("2025-01-01", "2025-12-31")
        assert r.number_matched == 72

    def test_january_six_pentads(self, pentadal_monthly):
        r = pentadal_monthly.generate("2025-01-01", "2025-12-31", limit=6)
        codes = [m.code for m in r.members]
        assert codes == ["2025-P01", "2025-P02", "2025-P03", "2025-P04", "2025-P05", "2025-P06"]
        assert r.members[4].end == "2025-01-25"  # P05
        assert r.members[5].start == "2025-01-26"  # P06
        assert r.members[5].end == "2025-01-31"  # P06 absorbs 26-31

    def test_p06_february(self, pentadal_monthly):
        """P06 Feb non-leap: 26–28."""
        r = pentadal_monthly.generate("2025-01-01", "2025-12-31", limit=72)
        feb_p6 = [m for m in r.members if m.code == "2025-P12"][0]
        assert feb_p6.start == "2025-02-26"
        assert feb_p6.end == "2025-02-28"


class TestPentadalMonthlyInverse:
    @pytest.mark.parametrize("date_str,expected_code", [
        ("2025-01-01", "2025-P01"),
        ("2025-01-05", "2025-P01"),
        ("2025-01-06", "2025-P02"),
        ("2025-01-25", "2025-P05"),
        ("2025-01-26", "2025-P06"),
        ("2025-01-31", "2025-P06"),
    ])
    def test_inverse(self, pentadal_monthly, date_str, expected_code):
        inv = pentadal_monthly.inverse(date_str)
        assert inv.valid is True
        assert inv.member == expected_code


# ---------------------------------------------------------------------------
# Annual scheme — pentadal (5-day)
# ---------------------------------------------------------------------------

class TestPentadalAnnualGenerate:
    def test_73_periods_per_year(self, pentadal_annual):
        r = pentadal_annual.generate("2025-01-01", "2025-12-31")
        assert r.number_matched == 73

    def test_first_period(self, pentadal_annual):
        r = pentadal_annual.generate("2025-01-01", "2025-12-31", limit=1)
        assert r.members[0].code == "2025-A01"
        assert r.members[0].start == "2025-01-01"
        assert r.members[0].end == "2025-01-05"

    def test_last_period_non_leap(self, pentadal_annual):
        """A73 non-leap: Dec 27–31 (5 days)."""
        r = pentadal_annual.generate("2025-01-01", "2025-12-31", limit=100)
        last = r.members[-1]
        assert last.code == "2025-A73"
        assert last.start == "2025-12-27"
        assert last.end == "2025-12-31"

    def test_last_period_leap(self, pentadal_annual):
        """A73 leap: Dec 26–31 (6 days)."""
        r = pentadal_annual.generate("2024-01-01", "2024-12-31", limit=100)
        last = r.members[-1]
        assert last.code == "2024-A73"
        assert last.end == "2024-12-31"

    def test_73_in_both_leap_and_non_leap(self, pentadal_annual):
        assert pentadal_annual.generate("2024-01-01", "2024-12-31").number_matched == 73
        assert pentadal_annual.generate("2025-01-01", "2025-12-31").number_matched == 73


class TestPentadalAnnualInverse:
    @pytest.mark.parametrize("date_str,expected_code", [
        ("2025-01-01", "2025-A01"),
        ("2025-01-05", "2025-A01"),
        ("2025-01-06", "2025-A02"),
        ("2025-12-27", "2025-A73"),
        ("2025-12-31", "2025-A73"),
    ])
    def test_inverse(self, pentadal_annual, date_str, expected_code):
        inv = pentadal_annual.inverse(date_str)
        assert inv.valid is True
        assert inv.member == expected_code


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_exact(self, dekadal):
        r = dekadal.search(dekadal.search_protocols[0], "2025-01-01", "2025-12-31", exact="2025-K02")
        assert len(r.members) == 1
        assert r.members[0].code == "2025-K02"

    def test_exact_not_found(self, dekadal):
        r = dekadal.search(dekadal.search_protocols[0], "2025-01-01", "2025-12-31", exact="NOPE")
        assert len(r.members) == 0

    def test_range(self, dekadal):
        r = dekadal.search(
            dekadal.search_protocols[1], "2025-01-01", "2025-12-31",
            min="2025-K01", max="2025-K03",
        )
        assert len(r.members) == 3
        codes = [m.code for m in r.members]
        assert codes == ["2025-K01", "2025-K02", "2025-K03"]


# ---------------------------------------------------------------------------
# Backward-compat aliases
# ---------------------------------------------------------------------------

class TestAliases:
    def test_dekadal_alias(self):
        from ogc_dimensions.providers import DekadalProvider
        g = DekadalProvider()
        assert g.provider_type == "daily-period"
        assert g.config_as_dict() == {"period_days": 10, "scheme": "monthly"}
        assert g.generate("2025-01-01", "2025-12-31").number_matched == 36

    def test_pentadal_monthly_alias(self):
        from ogc_dimensions.providers import PentadalMonthlyProvider
        g = PentadalMonthlyProvider()
        assert g.config_as_dict() == {"period_days": 5, "scheme": "monthly"}
        assert g.generate("2025-01-01", "2025-12-31").number_matched == 72

    def test_pentadal_annual_alias(self):
        from ogc_dimensions.providers import PentadalAnnualProvider
        g = PentadalAnnualProvider()
        assert g.config_as_dict() == {"period_days": 5, "scheme": "annual"}
        assert g.generate("2025-01-01", "2025-12-31").number_matched == 73

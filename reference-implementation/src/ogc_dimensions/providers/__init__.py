"""OGC Dimension Providers -- reference implementations."""

from .base import DimensionProvider, ProviderCapability, ProviderConfig, SearchProtocol
from .daily_period import DailyPeriodConfig, DailyPeriodProvider
from .dekadal import DekadalProvider
from .integer_range import IntegerRangeConfig, IntegerRangeProvider
from .pentadal import PentadalAnnualProvider, PentadalMonthlyProvider
from .tree import StaticTreeConfig, StaticTreeProvider, LeveledTreeProvider

__all__ = [
    # Base
    "DimensionProvider",
    "ProviderCapability",
    "ProviderConfig",
    "SearchProtocol",
    # Daily period (unified)
    "DailyPeriodConfig",
    "DailyPeriodProvider",
    # Aliases
    "DekadalProvider",
    "PentadalMonthlyProvider",
    "PentadalAnnualProvider",
    # Integer range
    "IntegerRangeConfig",
    "IntegerRangeProvider",
    # Tree
    "StaticTreeConfig",
    "StaticTreeProvider",
    "LeveledTreeProvider",
]

"""OGC Dimension Generators -- reference implementations."""

from .base import DimensionGenerator, GeneratorCapability, GeneratorConfig, SearchProtocol
from .daily_period import DailyPeriodConfig, DailyPeriodGenerator
from .dekadal import DekadalGenerator
from .integer_range import IntegerRangeConfig, IntegerRangeGenerator
from .pentadal import PentadalAnnualGenerator, PentadalMonthlyGenerator
from .tree import StaticTreeConfig, StaticTreeGenerator, LeveledTreeGenerator

__all__ = [
    # Base
    "DimensionGenerator",
    "GeneratorCapability",
    "GeneratorConfig",
    "SearchProtocol",
    # Daily period (unified)
    "DailyPeriodConfig",
    "DailyPeriodGenerator",
    # Aliases
    "DekadalGenerator",
    "PentadalMonthlyGenerator",
    "PentadalAnnualGenerator",
    # Integer range
    "IntegerRangeConfig",
    "IntegerRangeGenerator",
    # Tree
    "StaticTreeConfig",
    "StaticTreeGenerator",
    "LeveledTreeGenerator",
]

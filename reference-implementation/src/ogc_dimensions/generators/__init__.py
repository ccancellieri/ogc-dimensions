"""OGC Dimension Generators -- reference implementations."""

from .base import DimensionGenerator, GeneratorCapability, SearchProtocol
from .dekadal import DekadalGenerator
from .pentadal import PentadalMonthlyGenerator, PentadalAnnualGenerator
from .integer_range import IntegerRangeGenerator
from .tree import StaticTreeGenerator, LeveledTreeGenerator

__all__ = [
    "DimensionGenerator",
    "GeneratorCapability",
    "SearchProtocol",
    "DekadalGenerator",
    "PentadalMonthlyGenerator",
    "PentadalAnnualGenerator",
    "IntegerRangeGenerator",
    "StaticTreeGenerator",
    "LeveledTreeGenerator",
]

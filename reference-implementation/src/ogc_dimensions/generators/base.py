"""Abstract base for dimension generators.

Defines the Protocol that all generators must implement,
mapping to the conformance levels in the specification:
  Basic      = generate + extent
  Invertible = + inverse
  Searchable = + search (exact, range, like)
  Similarity = + search (vector)
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class GeneratorCapability(str, enum.Enum):
    GENERATE = "generate"
    EXTENT = "extent"
    INVERSE = "inverse"
    SEARCH = "search"
    CHILDREN = "children"
    ANCESTORS = "ancestors"


class SearchProtocol(str, enum.Enum):
    EXACT = "exact"
    RANGE = "range"
    LIKE = "like"
    VECTOR = "vector"


@dataclass
class GeneratedMember:
    """A single generated dimension member."""

    value: Any
    index: int
    code: str | None = None
    start: str | None = None
    end: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class InverseResult:
    """Result of an inverse operation."""

    valid: bool
    member: str | None = None
    coordinate: dict[str, Any] | None = None
    range: dict[str, str] | None = None
    index: int | None = None
    nearest: str | None = None
    reason: str | None = None


@dataclass
class ExtentResult:
    """Dimension extent in native and standard representations."""

    native_min: Any
    native_max: Any
    standard_min: str
    standard_max: str
    size: int


@dataclass
class PaginatedResult:
    """Paginated list of generated members."""

    dimension: str
    number_matched: int
    number_returned: int
    members: list[GeneratedMember]
    offset: int = 0
    limit: int = 100


class DimensionGenerator(ABC):
    """Abstract base class for all dimension generators.

    Subclasses MUST implement generate() and extent() (Basic conformance).
    Subclasses SHOULD implement inverse() if invertible.
    Subclasses MAY implement search() for Searchable conformance.
    """

    @property
    @abstractmethod
    def generator_type(self) -> str:
        """Short identifier (e.g., 'dekadal', 'integer-range')."""
        ...

    @property
    @abstractmethod
    def invertible(self) -> bool:
        """Whether this generator supports inverse operations."""
        ...

    @property
    def hierarchical(self) -> bool:
        """Whether this generator supports Hierarchical conformance level."""
        return False

    @property
    def capabilities(self) -> list[GeneratorCapability]:
        """Supported capabilities."""
        caps = [GeneratorCapability.GENERATE, GeneratorCapability.EXTENT]
        if self.invertible:
            caps.append(GeneratorCapability.INVERSE)
        if self.search_protocols:
            caps.append(GeneratorCapability.SEARCH)
        if self.hierarchical:
            caps.append(GeneratorCapability.CHILDREN)
            caps.append(GeneratorCapability.ANCESTORS)
        return caps

    @property
    def search_protocols(self) -> list[SearchProtocol]:
        """Supported search protocols. Override in subclasses."""
        return []

    @abstractmethod
    def generate(
        self,
        extent_min: Any,
        extent_max: Any,
        limit: int = 100,
        offset: int = 0,
        **params: Any,
    ) -> PaginatedResult:
        """Generate paginated dimension members within extent."""
        ...

    @abstractmethod
    def extent(self, extent_min: Any, extent_max: Any, **params: Any) -> ExtentResult:
        """Return dimension boundaries."""
        ...

    def inverse(self, value: str) -> InverseResult:
        """Map a value back to its dimension member. Requires invertible=True."""
        raise NotImplementedError(
            f"Generator '{self.generator_type}' does not support inverse operations."
        )

    def inverse_batch(
        self, values: list[str], on_invalid: str = "reject"
    ) -> list[InverseResult]:
        """Batch inverse for pipeline operations."""
        return [self.inverse(v) for v in values]

    def search(
        self,
        protocol: SearchProtocol,
        extent_min: Any,
        extent_max: Any,
        **query: Any,
    ) -> PaginatedResult:
        """Search for dimension members matching a query."""
        raise NotImplementedError(
            f"Generator '{self.generator_type}' does not support "
            f"search protocol '{protocol}'."
        )

    def children(
        self,
        parent_code: str,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Return paginated direct children of parent_code (Hierarchical conformance)."""
        raise NotImplementedError(
            f"Generator '{self.generator_type}' does not support Hierarchical operations."
        )

    def has_children(self, member_code: str) -> bool:
        """Return True if *member_code* has at least one child (Hierarchical conformance).

        Used to decide whether to emit a ``children`` navigation link for a
        member.  The default implementation returns ``False``; hierarchical
        generators SHOULD override this.
        """
        return False

    def ancestors(self, member_code: str) -> list[dict[str, Any]]:
        """Return ancestor chain from root to member_code inclusive (Hierarchical conformance)."""
        raise NotImplementedError(
            f"Generator '{self.generator_type}' does not support Hierarchical operations."
        )

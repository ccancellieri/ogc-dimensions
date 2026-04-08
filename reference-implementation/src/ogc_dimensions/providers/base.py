"""Abstract base for dimension providers.

Defines the Protocol that all generators must implement,
mapping to the conformance levels in the specification:
  Basic      = generate + extent
  Invertible = + inverse
  Searchable = + search (exact, range, like)
  Similarity = + search (vector)

Three distinct input categories exist for any generator:

  config     — Author-set constants, fixed at Collection-authoring time.
               Exposed via the 'config' field in the provider JSON object
               and in the /dimensions list + /queryables API responses.
               Clients cannot override these per-request.
               Examples: IntegerRangeProvider.step, epoch year.

  parameters — Query-time inputs clients pass per request.
               Declared as a JSON Schema in the provider JSON object.
               Examples: language, sort_by, sort_dir, parent, level.

  extent     — Dimension bounds (extent_min / extent_max), already
               a first-class field on the dimension object and the API.
"""

from __future__ import annotations

import dataclasses
import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderCapability(str, enum.Enum):
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


@dataclass(frozen=True)
class ProviderConfig:
    """Base class for provider instance configuration.

    Subclasses declare the author-set constants that parameterise a specific
    provider algorithm.  These values are static for the lifetime of the
    Collection and map 1:1 to the ``config`` field in the generator JSON
    object.  Generators with no configurable constants subclass this with no
    additional fields and return an instance of their empty subclass from the
    ``config`` property.
    """

    def as_dict(self) -> dict[str, Any]:
        """Return config as a plain dict suitable for JSON serialisation."""
        return dataclasses.asdict(self)


@dataclass
class GeneratedMember:
    """A single generated dimension member."""

    value: Any
    index: int
    code: str | None = None
    start: str | None = None
    end: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    has_children: bool = False


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


class DimensionProvider(ABC):
    """Abstract base class for all dimension providers.

    Subclasses MUST implement generate() and extent() (Basic conformance).
    Subclasses SHOULD implement inverse() if invertible.
    Subclasses MAY implement search() for Searchable conformance.
    """

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Short identifier (e.g., 'dekadal', 'integer-range')."""
        ...

    @property
    @abstractmethod
    def config(self) -> ProviderConfig:
        """Author-set configuration constants for this provider instance.

        Returns a frozen :class:`ProviderConfig` subclass carrying the static
        values set by the data author when declaring the dimension.  These are
        exposed via the ``/dimensions`` list and ``/queryables`` endpoints so
        clients can discover the exact parameterisation without reading server
        source code.  Generators with no configurable constants return an
        instance of their empty config subclass (``as_dict()`` → ``{}``).
        """
        ...

    def config_as_dict(self) -> dict[str, Any]:
        """Return generator config as a plain JSON-serialisable dict."""
        return self.config.as_dict()

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
    def capabilities(self) -> list[ProviderCapability]:
        """Supported capabilities."""
        caps = [ProviderCapability.GENERATE, ProviderCapability.EXTENT]
        if self.invertible:
            caps.append(ProviderCapability.INVERSE)
        if self.search_protocols:
            caps.append(ProviderCapability.SEARCH)
        if self.hierarchical:
            caps.append(ProviderCapability.CHILDREN)
            caps.append(ProviderCapability.ANCESTORS)
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
            f"Generator '{self.provider_type}' does not support inverse operations."
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
            f"Generator '{self.provider_type}' does not support "
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
            f"Generator '{self.provider_type}' does not support Hierarchical operations."
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
            f"Generator '{self.provider_type}' does not support Hierarchical operations."
        )

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class SourceMatch:
    source: str
    source_id: str
    url: str | None = None
    label: str | None = None
    description: str | None = None
    confidence: float = 1.0
    identifiers: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class SourceAdapter(Protocol):
    """Minimal contract for external metadata/entity reconciliation sources."""

    name: str

    @property
    def capabilities(self) -> tuple[str, ...]: ...

    def reconcile_isbn(self, isbn: str) -> list[SourceMatch]: ...

    def health(self) -> dict[str, Any]: ...

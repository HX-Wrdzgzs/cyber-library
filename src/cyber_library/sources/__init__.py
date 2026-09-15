"""External catalog source adapters and entity reconciliation contracts."""

from .base import SourceAdapter, SourceMatch
from .registry import SourceRegistry, register_builtin_sources, registry

__all__ = [
    "SourceAdapter",
    "SourceMatch",
    "SourceRegistry",
    "registry",
    "register_builtin_sources",
]

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import SourceAdapter

AdapterFactory = Callable[..., SourceAdapter]


class SourceRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    def register(self, name: str, factory: AdapterFactory, *, replace: bool = False) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("source name must not be empty")
        if key in self._factories and not replace:
            raise ValueError(f"source already registered: {key}")
        self._factories[key] = factory

    def unregister(self, name: str) -> None:
        self._factories.pop(name.strip().lower(), None)

    def names(self) -> list[str]:
        return sorted(self._factories)

    def create(self, name: str, **kwargs: Any) -> SourceAdapter:
        key = name.strip().lower()
        try:
            factory = self._factories[key]
        except KeyError as exc:
            raise KeyError(f"unknown source: {name}") from exc
        adapter = factory(**kwargs)
        if not isinstance(adapter, SourceAdapter):
            raise TypeError(f"registered source {key!r} does not satisfy SourceAdapter")
        return adapter


_registry = SourceRegistry()


def registry() -> SourceRegistry:
    return _registry


def register_builtin_sources() -> SourceRegistry:
    from .wikidata import WikidataAdapter

    if "wikidata" not in _registry.names():
        _registry.register("wikidata", WikidataAdapter)
    return _registry

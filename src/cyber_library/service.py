from __future__ import annotations

from pathlib import Path

from .cache import JsonCache
from .database import CatalogDB
from .identifiers import normalize_isbn
from .intelligence import catalog_analysis
from .sources.openlibrary import NotFound, OpenLibraryClient


class CatalogService:
    def __init__(
        self,
        cache_path: str | Path = ".cyber-library/cache.sqlite3",
        contact: str | None = None,
        catalog_db_path: str | Path | None = None,
        live_fallback: bool = True,
    ) -> None:
        self.cache = JsonCache(cache_path)
        self.openlibrary = OpenLibraryClient(self.cache, contact)
        self.catalog = CatalogDB(catalog_db_path) if catalog_db_path else None
        self.live_fallback = live_fallback

    def resolve_isbn(self, isbn: str, analyze: bool = False):
        isbn13 = normalize_isbn(isbn)
        record = self.catalog.lookup_isbn(isbn13) if self.catalog else None
        if record is None:
            if not self.live_fallback:
                raise NotFound(isbn13)
            record = self.openlibrary.lookup_isbn(isbn13)
        if analyze:
            record.analysis = catalog_analysis(record)
        return record

    def stats(self) -> dict[str, int]:
        return self.catalog.stats() if self.catalog else {"works": 0, "editions": 0, "authors": 0, "identifiers": 0}

    def close(self) -> None:
        if self.catalog:
            self.catalog.close()
        self.cache.close()

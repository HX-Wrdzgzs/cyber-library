from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..cache import JsonCache
from ..identifiers import compact, normalize_isbn
from .base import ExternalSourceError, SourceMatch

DEFAULT_BASE_URL = "https://api.crossref.org"


class CrossrefError(ExternalSourceError):
    pass


class CrossrefAdapter:
    name = "crossref"

    def __init__(self, cache: JsonCache | None = None, contact: str | None = None, base_url: str | None = None, timeout: float = 25.0) -> None:
        self.cache = cache
        self.contact = (contact or os.getenv("CYBER_LIBRARY_CONTACT", "")).strip()
        self.base_url = (base_url or os.getenv("CYBER_LIBRARY_CROSSREF_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("isbn-reconciliation", "doi-linking")

    def health(self) -> dict[str, object]:
        return {"name": self.name, "configured": bool(self.base_url), "endpoint": self.base_url, "capabilities": list(self.capabilities)}

    def _get(self, params: dict[str, str], cache_key: str) -> dict:
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        if self.contact:
            params = {**params, "mailto": self.contact}
        request = Request(
            f"{self.base_url}/works?{urlencode(params)}",
            headers={
                "Accept": "application/json",
                "User-Agent": "CyberLibrary/1.2 (+https://github.com/HX-Wrdzgzs/cyber-library)" + (f" mailto:{self.contact}" if self.contact else ""),
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except HTTPError as exc:
            detail = ""
            try: detail = exc.read(1600).decode("utf-8", "replace")
            except Exception: pass
            raise CrossrefError(f"Crossref HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CrossrefError(f"Crossref request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise CrossrefError("Crossref returned a non-object response")
        if self.cache:
            self.cache.set(cache_key, payload)
        return payload

    @staticmethod
    def _first_text(value) -> str | None:
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str):
            return value
        return None

    def reconcile_isbn(self, isbn: str) -> list[SourceMatch]:
        isbn13 = normalize_isbn(isbn)
        payload = self._get(
            {
                "filter": f"isbn:{isbn13}",
                "rows": "20",
                "select": "DOI,title,type,ISBN,publisher,issued,author,URL",
            },
            f"crossref:isbn:{isbn13}",
        )
        message = payload.get("message")
        items = message.get("items", []) if isinstance(message, dict) else []
        if not isinstance(items, list):
            return []
        matches: list[SourceMatch] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_isbns = [compact(str(value)) for value in item.get("ISBN", []) if str(value).strip()]
            if isbn13 not in raw_isbns:
                continue
            doi = str(item.get("DOI") or "").strip().lower()
            if not doi or doi in seen:
                continue
            seen.add(doi)
            authors = []
            for author in item.get("author") or []:
                if not isinstance(author, dict):
                    continue
                name = " ".join(str(author.get(key) or "").strip() for key in ("given", "family")).strip()
                if name:
                    authors.append(name)
            issued = item.get("issued") if isinstance(item.get("issued"), dict) else {}
            date_parts = issued.get("date-parts", []) if isinstance(issued, dict) else []
            date = date_parts[0] if date_parts and isinstance(date_parts[0], list) else []
            matches.append(
                SourceMatch(
                    source=self.name,
                    source_id=doi,
                    url=str(item.get("URL") or f"https://doi.org/{doi}"),
                    label=self._first_text(item.get("title")),
                    description=str(item.get("type") or "") or None,
                    confidence=1.0,
                    identifiers={"doi": [doi], "isbn13": [isbn13]},
                    metadata={
                        "type": item.get("type"),
                        "publisher": item.get("publisher"),
                        "authors": authors,
                        "issued": date,
                    },
                )
            )
        return matches

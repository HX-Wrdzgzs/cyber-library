from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..cache import JsonCache
from ..evidence import openlibrary_evidence, text_value, toc_titles
from ..identifiers import normalize_isbn
from ..models import Analysis, BookRecord, Edition, Provenance, Work
from ..taxonomy import classify

BASE = "https://openlibrary.org"


class SourceError(RuntimeError):
    pass


class NotFound(SourceError):
    pass


class OpenLibraryClient:
    """Rate-safe, low-volume Open Library client.

    Bulk catalog creation must use Open Library monthly dumps rather than
    repeatedly calling these endpoints.
    """

    def __init__(self, cache: JsonCache | None = None, contact: str | None = None, timeout: float = 15.0) -> None:
        self.cache = cache
        self.timeout = timeout
        self.contact = (contact or os.getenv("CYBER_LIBRARY_CONTACT", "")).strip()
        self.user_agent = "CyberLibrary/1.0.0" + (f" ({self.contact})" if self.contact else "")
        self.min_interval = 0.36 if self.contact else 1.05
        self._rate_lock = threading.Lock()
        self._last_request = 0.0

    def _throttle(self) -> None:
        with self._rate_lock:
            elapsed = time.monotonic() - self._last_request
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request = time.monotonic()

    def _get_json(self, url: str, key: str) -> dict:
        if self.cache:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        self._throttle()
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if self.contact:
            headers["From"] = self.contact
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.load(resp)
        except HTTPError as exc:
            if exc.code == 404:
                raise NotFound(url) from exc
            raise SourceError(f"Open Library HTTP {exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SourceError(f"Open Library request failed: {exc}") from exc
        if not isinstance(data, dict):
            raise SourceError("Open Library response was not a JSON object")
        if self.cache:
            self.cache.set(key, data)
        return data

    def _author_name(self, key: str) -> str:
        raw = self._get_json(f"{BASE}{key}.json", f"ol:author:{key}")
        return str(raw.get("name") or key.rsplit("/", 1)[-1])

    @staticmethod
    def _author_keys(work: dict | None, edition: dict) -> list[str]:
        raw_authors = (work or {}).get("authors") or edition.get("authors") or []
        keys: list[str] = []
        for item in raw_authors:
            if not isinstance(item, dict):
                continue
            candidate = item.get("author", item)
            if isinstance(candidate, dict) and candidate.get("key"):
                keys.append(str(candidate["key"]))
        return list(dict.fromkeys(keys))[:8]

    @staticmethod
    def _cover_url(edition: dict, isbn13: str) -> str:
        covers = edition.get("covers") or []
        if covers and str(covers[0]).lstrip("-").isdigit() and int(covers[0]) > 0:
            return f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg?default=false"
        return f"https://covers.openlibrary.org/b/isbn/{isbn13}-L.jpg?default=false"

    @staticmethod
    def build_record(isbn13: str, edition_raw: dict, work_raw: dict | None, author_names: list[str]) -> BookRecord:
        ekey = str(edition_raw.get("key") or f"/isbn/{isbn13}")
        eid = ekey.rsplit("/", 1)[-1]
        works = edition_raw.get("works") or []
        wkey = works[0].get("key") if works and isinstance(works[0], dict) else None
        language = None
        langs = edition_raw.get("languages") or []
        if langs and isinstance(langs[0], dict):
            language = str(langs[0].get("key", "")).rsplit("/", 1)[-1] or None
        work = None
        wid = None
        if work_raw is not None and wkey:
            wid = wkey.rsplit("/", 1)[-1]
            description = text_value(work_raw.get("description"))
            subjects = [str(x) for x in (work_raw.get("subjects") or []) if isinstance(x, str)]
            work = Work(id=f"openlibrary:work:{wid}", title=str(work_raw.get("title") or edition_raw.get("title") or ""), authors=author_names, subjects=subjects, description=description, first_sentence=text_value(work_raw.get("first_sentence")), categories=classify(subjects, str(work_raw.get("title") or ""), description or ""), source_refs=[f"openlibrary:{wkey}"])
        ids: dict[str, list[str]] = {"isbn13": [isbn13]}
        field_map = {"isbn10": "isbn_10", "isbn13": "isbn_13", "lccn": "lccn", "oclc": "oclc_numbers"}
        for scheme, field in field_map.items():
            values = edition_raw.get(field) or []
            if values:
                ids[scheme] = list(dict.fromkeys(str(x).replace("-", "").strip() for x in values))
        if edition_raw.get("ocaid"):
            ids["internet_archive"] = [str(edition_raw["ocaid"])]
        toc = toc_titles(edition_raw.get("table_of_contents"))
        edition = Edition(id=f"openlibrary:edition:{eid}", work_id=f"openlibrary:work:{wid}" if wid else None, title=str(edition_raw.get("title") or ""), language=language, publishers=[str(x) for x in (edition_raw.get("publishers") or [])], publish_date=edition_raw.get("publish_date"), page_count=edition_raw.get("number_of_pages") if isinstance(edition_raw.get("number_of_pages"), int) else None, identifiers=ids, cover_url=OpenLibraryClient._cover_url(edition_raw, isbn13), table_of_contents=toc, physical_format=edition_raw.get("physical_format"), source_refs=[f"openlibrary:{ekey}"])
        work_ref = f"openlibrary:{wkey}" if wkey else None
        edition_ref = f"openlibrary:{ekey}"
        evidence = openlibrary_evidence(work_raw, edition_raw, work_ref, edition_ref)
        sources = [edition_ref] + ([work_ref] if work_ref else [])
        return BookRecord(work=work, edition=edition, analysis=Analysis(level="L0", confidence=1.0, sources=sources, warnings=["No interpretation has been generated for this record."]), provenance=[Provenance(source="Open Library", source_id=eid, url=f"{BASE}{ekey}", retrieved_at=datetime.now(timezone.utc).isoformat())], evidence=evidence)

    def lookup_isbn(self, isbn: str) -> BookRecord:
        isbn13 = normalize_isbn(isbn)
        eraw = self._get_json(f"{BASE}/isbn/{isbn13}.json", f"ol:isbn:{isbn13}")
        works = eraw.get("works") or []
        wkey = works[0].get("key") if works and isinstance(works[0], dict) else None
        wraw = self._get_json(f"{BASE}{wkey}.json", f"ol:work:{wkey}") if wkey else None
        author_names: list[str] = []
        for author_key in self._author_keys(wraw, eraw):
            try:
                author_names.append(self._author_name(author_key))
            except SourceError:
                author_names.append(author_key.rsplit("/", 1)[-1])
        return self.build_record(isbn13, eraw, wraw, author_names)

    def search_books(self, query: str, limit: int = 20) -> list[dict]:
        query = query.strip()
        if not query:
            return []
        limit = max(1, min(int(limit), 50))
        params = urlencode({"q": query, "limit": limit})
        raw = self._get_json(f"{BASE}/search.json?{params}", f"ol:search:{query}:{limit}")
        results: list[dict] = []
        for doc in raw.get("docs") or []:
            if not isinstance(doc, dict):
                continue
            isbns = [str(x).replace("-", "") for x in (doc.get("isbn") or [])]
            isbn = next((x for x in isbns if len(x) == 13 and x[:3] in {"978", "979"}), None)
            subjects = [str(x) for x in (doc.get("subject") or [])[:24]]
            cover_id = doc.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg?default=false" if cover_id else None
            key = str(doc.get("key") or "")
            if key and not key.startswith("/"):
                key = f"/works/{key}"
            results.append({"edition_id": None, "work_id": f"openlibrary:work:{key.rsplit('/', 1)[-1]}" if key else None, "title": str(doc.get("title") or ""), "authors": [str(x) for x in (doc.get("author_name") or [])[:8]], "subjects": subjects, "publishers": [str(x) for x in (doc.get("publisher") or [])[:8]], "categories": classify(subjects, str(doc.get("title") or "")), "language": (doc.get("language") or [None])[0], "publish_date": str(doc.get("first_publish_year") or "") or None, "isbn": isbn, "cover_url": cover_url, "score": None, "source": "openlibrary-search"})
        return results

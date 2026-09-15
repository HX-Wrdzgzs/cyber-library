from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .cache import JsonCache
from .database import CatalogDB
from .scale import build_universe_tiles
from .sources.openlibrary import BASE, NotFound, OpenLibraryClient, SourceError
from .taxonomy import normalize_subjects

MAX_CHANGES_PER_RUN = 1000
MAX_DOCUMENTS_PER_RUN = 1000


class RecentChangesClient(Protocol):
    def recent_changes(self, limit: int, offset: int = 0) -> list[dict]: ...
    def get_document(self, key: str) -> dict: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _canonical_work(raw: dict) -> dict:
    subjects = [str(x) for x in (raw.get("subjects") or []) if isinstance(x, str)]
    if not subjects:
        return raw
    normalized = normalize_subjects(subjects, 128)
    return raw if normalized == subjects else {**raw, "subjects": normalized}


def _upsert_work_preserving_raw(catalog: CatalogDB, key: str, raw: dict) -> None:
    canonical = _canonical_work(raw)
    catalog.upsert_work(key, canonical)
    if canonical is not raw:
        catalog.db.execute("UPDATE works SET raw_json=? WHERE id=?", (json.dumps(raw, ensure_ascii=False), key))


class OpenLibraryRecentClient:
    """Low-volume RecentChanges client for keeping a dump-based catalog warm."""

    def __init__(self, cache: JsonCache | None = None, contact: str | None = None, timeout: float = 20.0) -> None:
        self.base = OpenLibraryClient(cache=cache, contact=contact, timeout=timeout)
        self.timeout = timeout

    def _request(self, url: str) -> Any:
        self.base._throttle()
        headers = {"Accept": "application/json", "User-Agent": self.base.user_agent}
        if self.base.contact:
            headers["From"] = self.base.contact
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 404:
                raise NotFound(url) from exc
            raise SourceError(f"Open Library HTTP {exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SourceError(f"Open Library request failed: {exc}") from exc

    def recent_changes(self, limit: int, offset: int = 0) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        offset = max(0, min(int(offset), 10000))
        raw = self._request(f"{BASE}/recentchanges.json?{urlencode({'limit': limit, 'offset': offset})}")
        if not isinstance(raw, list):
            raise SourceError("Open Library recentchanges response was not a JSON array")
        return [item for item in raw if isinstance(item, dict)]

    def get_document(self, key: str) -> dict:
        key = key.strip()
        if not key.startswith("/"):
            raise ValueError(f"invalid Open Library key: {key}")
        raw = self._request(f"{BASE}{key}.json")
        if not isinstance(raw, dict):
            raise SourceError(f"Open Library document response was not an object: {key}")
        return raw


def ensure_refresh_schema(catalog: CatalogDB) -> None:
    with catalog._lock:
        catalog.db.execute("""CREATE TABLE IF NOT EXISTS catalog_refresh_state(
              source TEXT PRIMARY KEY,
              checkpoint TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )""")
        catalog.db.commit()


def get_refresh_checkpoint(catalog: CatalogDB, source: str = "openlibrary") -> str | None:
    ensure_refresh_schema(catalog)
    with catalog._lock:
        row = catalog.db.execute("SELECT checkpoint FROM catalog_refresh_state WHERE source=?", (source,)).fetchone()
    return str(row["checkpoint"]) if row else None


def set_refresh_checkpoint(catalog: CatalogDB, checkpoint: str, source: str = "openlibrary") -> str:
    normalized = _timestamp_text(_parse_timestamp(checkpoint))
    ensure_refresh_schema(catalog)
    with catalog._lock:
        catalog.db.execute(
            "INSERT INTO catalog_refresh_state(source,checkpoint,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(source) DO UPDATE SET checkpoint=excluded.checkpoint,updated_at=excluded.updated_at",
            (source, normalized, _now()),
        )
        catalog.db.commit()
    return normalized


def _normalize_key(key: str) -> str | None:
    key = key.strip()
    if key.startswith("/author/"):
        key = "/authors/" + key.rsplit("/", 1)[-1]
    if key.startswith(("/authors/", "/works/", "/books/")):
        return key
    return None


def _change_keys(changesets: list[dict]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for changeset in changesets:
        for change in changeset.get("changes") or []:
            if not isinstance(change, dict):
                continue
            key = _normalize_key(str(change.get("key") or ""))
            if key and key not in seen:
                seen.add(key)
                out.append(key)
    return out


def _collect_changes(client: RecentChangesClient, since: datetime, max_changes: int, page_size: int = 100) -> tuple[list[dict], bool]:
    page_size = max(1, min(int(page_size), 1000))
    max_changes = max(1, min(int(max_changes), MAX_CHANGES_PER_RUN))
    selected: list[dict] = []
    offset = 0
    reached_checkpoint = False
    while len(selected) < max_changes and offset <= 10000:
        take = min(page_size, max_changes - len(selected))
        page = client.recent_changes(take, offset)
        if not page:
            reached_checkpoint = True
            break
        for change in page:
            timestamp = change.get("timestamp")
            if not isinstance(timestamp, str):
                continue
            try:
                changed_at = _parse_timestamp(timestamp)
            except ValueError:
                continue
            if changed_at <= since:
                reached_checkpoint = True
                break
            selected.append(change)
            if len(selected) >= max_changes:
                break
        if reached_checkpoint or len(page) < take or len(selected) >= max_changes:
            break
        offset += len(page)
    return selected, (not reached_checkpoint and len(selected) >= max_changes)


def _reindex_work(catalog: CatalogDB, work_key: str) -> int:
    with catalog._lock:
        rows = catalog.db.execute("SELECT id FROM editions WHERE work_id=?", (work_key,)).fetchall()
        for row in rows:
            catalog._upsert_search(str(row["id"]))
    return len(rows)


def _reindex_author(catalog: CatalogDB, author_key: str) -> int:
    count = 0
    with catalog._lock:
        works = catalog.db.execute("SELECT id FROM works WHERE authors LIKE ?", (f'%"{author_key}"%',)).fetchall()
    for work in works:
        count += _reindex_work(catalog, str(work["id"]))
    return count


def refresh_openlibrary(db_path: str | Path, *, client: RecentChangesClient, since: str | None = None, max_changes: int = 250, max_documents: int = 500, rebuild_universe: bool = False) -> dict[str, Any]:
    if max_changes < 1 or max_changes > MAX_CHANGES_PER_RUN:
        raise ValueError(f"max_changes must be between 1 and {MAX_CHANGES_PER_RUN}")
    if max_documents < 1 or max_documents > MAX_DOCUMENTS_PER_RUN:
        raise ValueError(f"max_documents must be between 1 and {MAX_DOCUMENTS_PER_RUN}")
    catalog = CatalogDB(db_path)
    try:
        checkpoint = since or get_refresh_checkpoint(catalog)
        if not checkpoint:
            raise ValueError("No Open Library refresh checkpoint exists. Pass --since after a dump import, or seed a checkpoint explicitly.")
        since_dt = _parse_timestamp(checkpoint)
        changesets, truncated = _collect_changes(client, since_dt, max_changes)
        keys = _change_keys(changesets)
        documents_truncated = len(keys) > max_documents
        keys = keys[:max_documents]
        counts = {"authors": 0, "works": 0, "editions": 0, "not_found": 0, "errors": 0, "reindexed": 0}
        failures: list[dict[str, str]] = []
        for key in keys:
            try:
                raw = client.get_document(key)
                if key.startswith("/authors/"):
                    catalog.upsert_author(key, raw); counts["authors"] += 1
                    counts["reindexed"] += _reindex_author(catalog, key)
                elif key.startswith("/works/"):
                    _upsert_work_preserving_raw(catalog, key, raw); counts["works"] += 1
                    counts["reindexed"] += _reindex_work(catalog, key)
                elif key.startswith("/books/"):
                    catalog.upsert_edition(key, raw); counts["editions"] += 1
            except NotFound:
                counts["not_found"] += 1; failures.append({"key": key, "error": "not_found"})
            except (SourceError, ValueError, TypeError, KeyError) as exc:
                counts["errors"] += 1; failures.append({"key": key, "error": str(exc)})
        catalog.commit()
        newest = max((_parse_timestamp(str(item["timestamp"])) for item in changesets if isinstance(item.get("timestamp"), str)), default=None)
        safe = not truncated and not documents_truncated and not failures
        advanced_to = set_refresh_checkpoint(catalog, _timestamp_text(newest)) if safe and newest is not None else None
        universe = build_universe_tiles(catalog, force=True) if rebuild_universe and counts["editions"] else None
        return {"source": "openlibrary", "previous_checkpoint": _timestamp_text(since_dt), "checkpoint_advanced_to": advanced_to, "changesets": len(changesets), "documents": len(keys), "truncated": truncated, "documents_truncated": documents_truncated, "counts": counts, "failures": failures, "universe": universe, "guidance": "Use a newer monthly dump if truncated=true; RecentChanges is not a bulk ingestion API." if truncated or documents_truncated else None}
    finally:
        catalog.close()

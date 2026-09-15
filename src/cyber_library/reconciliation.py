from __future__ import annotations

import json
from datetime import datetime, timezone

from .database import CatalogDB
from .identifiers import normalize_isbn
from .sources.base import SourceAdapter, SourceMatch


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_link_schema(catalog: CatalogDB) -> None:
    with catalog._lock:
        catalog.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS entity_links(
              local_type TEXT NOT NULL,
              local_id TEXT NOT NULL,
              source TEXT NOT NULL,
              source_id TEXT NOT NULL,
              url TEXT,
              confidence REAL NOT NULL,
              payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(local_type,local_id,source,source_id)
            );
            CREATE INDEX IF NOT EXISTS idx_entity_links_source
              ON entity_links(source,source_id);
            CREATE INDEX IF NOT EXISTS idx_entity_links_local
              ON entity_links(local_type,local_id);
            """
        )
        catalog.db.commit()


def store_matches(
    catalog: CatalogDB,
    *,
    local_type: str,
    local_id: str,
    matches: list[SourceMatch],
) -> int:
    ensure_link_schema(catalog)
    now = _now()
    with catalog._lock:
        for match in matches:
            catalog.db.execute(
                "INSERT INTO entity_links(local_type,local_id,source,source_id,url,confidence,payload_json,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(local_type,local_id,source,source_id) DO UPDATE SET "
                "url=excluded.url,confidence=excluded.confidence,payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                (
                    local_type,
                    local_id,
                    match.source,
                    match.source_id,
                    match.url,
                    float(match.confidence),
                    json.dumps(match.to_dict(), ensure_ascii=False),
                    now,
                ),
            )
        catalog.db.commit()
    return len(matches)


def links_for(catalog: CatalogDB, local_type: str, local_id: str) -> list[dict]:
    ensure_link_schema(catalog)
    with catalog._lock:
        rows = catalog.db.execute(
            "SELECT source,source_id,url,confidence,payload_json,updated_at FROM entity_links "
            "WHERE local_type=? AND local_id=? ORDER BY confidence DESC,source,source_id",
            (local_type, local_id),
        ).fetchall()
    out = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            payload = {}
        out.append(
            {
                "source": row["source"],
                "source_id": row["source_id"],
                "url": row["url"],
                "confidence": float(row["confidence"]),
                "updated_at": row["updated_at"],
                "match": payload,
            }
        )
    return out


def reconcile_isbn(catalog: CatalogDB, adapter: SourceAdapter, isbn: str) -> dict:
    isbn13 = normalize_isbn(isbn)
    record = catalog.lookup_isbn(isbn13)
    if record is None:
        raise LookupError(f"ISBN is not present in the local catalog: {isbn13}")
    matches = adapter.reconcile_isbn(isbn)
    store_matches(catalog, local_type="edition", local_id=record.edition.id, matches=matches)
    return {
        "isbn13": isbn13,
        "edition_id": record.edition.id,
        "source": adapter.name,
        "matches": [match.to_dict() for match in matches],
        "stored": len(matches),
    }

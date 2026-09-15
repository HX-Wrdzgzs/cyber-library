from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from .database import CatalogDB
from .taxonomy import normalize_subjects


def _open(path: Path) -> TextIO:
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" else path.open("r", encoding="utf-8", errors="replace")


def _normalize_timestamp(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _newest(current: str | None, candidate: str | None) -> str | None:
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


def _normalize_work(raw: dict) -> dict:
    subjects = [str(x) for x in (raw.get("subjects") or []) if isinstance(x, str)]
    if not subjects:
        return raw
    normalized = normalize_subjects(subjects, 128)
    if normalized == subjects:
        return raw
    return {**raw, "subjects": normalized}


def import_openlibrary_dump(path: str | Path, db_path: str | Path, limit: int | None = None, commit_every: int = 5000, reindex: bool = False) -> dict[str, int | str | None]:
    path = Path(path)
    db = CatalogDB(db_path, index_on_write=False)
    counts: dict[str, int | str | None] = {"lines": 0, "works": 0, "editions": 0, "authors": 0, "errors": 0, "latest_modified": None}
    try:
        with _open(path) as fh:
            for line in fh:
                if limit is not None and int(counts["lines"] or 0) >= limit:
                    break
                counts["lines"] = int(counts["lines"] or 0) + 1
                try:
                    cols = line.rstrip("\n").split("\t", 4)
                    if len(cols) != 5:
                        raise ValueError("expected five TSV columns")
                    typ, key, _revision, last_modified, payload = cols
                    normalized_modified = _normalize_timestamp(last_modified)
                    counts["latest_modified"] = _newest(counts.get("latest_modified") if isinstance(counts.get("latest_modified"), str) else None, normalized_modified)
                    raw = json.loads(payload)
                    if typ == "/type/work":
                        db.upsert_work(key, _normalize_work(raw)); counts["works"] = int(counts["works"] or 0) + 1
                    elif typ == "/type/edition":
                        db.upsert_edition(key, raw); counts["editions"] = int(counts["editions"] or 0) + 1
                    elif typ == "/type/author":
                        db.upsert_author(key, raw); counts["authors"] = int(counts["authors"] or 0) + 1
                except (ValueError, json.JSONDecodeError, TypeError, KeyError):
                    counts["errors"] = int(counts["errors"] or 0) + 1
                if int(counts["lines"] or 0) % commit_every == 0:
                    db.commit()
        db.commit()
        if reindex:
            counts.update(db.reindex())
        return counts
    finally:
        db.close()


def import_openlibrary_dumps(paths: list[str | Path], db_path: str | Path, limit_each: int | None = None, reindex: bool = True) -> dict[str, int | str | None]:
    total: dict[str, int | str | None] = {"lines": 0, "works": 0, "editions": 0, "authors": 0, "errors": 0, "latest_modified": None}
    numeric_keys = ("lines", "works", "editions", "authors", "errors")
    for path in paths:
        counts = import_openlibrary_dump(path, db_path, limit_each, reindex=False)
        for key in numeric_keys:
            total[key] = int(total[key] or 0) + int(counts.get(key) or 0)
        modified = counts.get("latest_modified")
        total["latest_modified"] = _newest(total.get("latest_modified") if isinstance(total.get("latest_modified"), str) else None, modified if isinstance(modified, str) else None)
    if reindex:
        db = CatalogDB(db_path, index_on_write=False)
        try:
            total.update(db.reindex())
        finally:
            db.close()
    return total

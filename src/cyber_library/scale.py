from __future__ import annotations

import json
import math
from datetime import datetime, timezone

from .database import CatalogDB

MAX_TILE_LEVEL = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_scale_schema(catalog: CatalogDB) -> None:
    with catalog._lock:
        catalog.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS universe_tiles(
              zoom INTEGER NOT NULL,
              tile_x INTEGER NOT NULL,
              tile_y INTEGER NOT NULL,
              item_count INTEGER NOT NULL,
              sample_edition_id TEXT,
              PRIMARY KEY(zoom,tile_x,tile_y)
            );
            CREATE INDEX IF NOT EXISTS idx_universe_tiles_view
              ON universe_tiles(zoom,tile_x,tile_y);
            CREATE TABLE IF NOT EXISTS maintenance_state(
              state_key TEXT PRIMARY KEY,
              state_value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        catalog.db.commit()


def _source_revision(catalog: CatalogDB) -> str:
    row = catalog.db.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN space_x IS NOT NULL AND space_y IS NOT NULL THEN 1 ELSE 0 END) AS mapped, "
        "COALESCE(MAX(rowid),0) AS max_rowid FROM editions"
    ).fetchone()
    return f"{int(row['total'])}:{int(row['mapped'] or 0)}:{int(row['max_rowid'] or 0)}"


def _state(catalog: CatalogDB, key: str) -> dict | None:
    row = catalog.db.execute(
        "SELECT state_value FROM maintenance_state WHERE state_key=?", (key,)
    ).fetchone()
    if not row:
        return None
    try:
        value = json.loads(str(row["state_value"]))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _set_state(catalog: CatalogDB, key: str, value: dict) -> None:
    catalog.db.execute(
        "INSERT INTO maintenance_state(state_key,state_value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(state_key) DO UPDATE SET state_value=excluded.state_value,updated_at=excluded.updated_at",
        (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), _now()),
    )


def build_universe_tiles(
    catalog: CatalogDB,
    *,
    max_level: int = MAX_TILE_LEVEL,
    force: bool = False,
) -> dict[str, object]:
    """Build resumable density tiles for the ISBN universe.

    Each level is committed independently. If the process is interrupted, rerunning
    the command skips levels already built against the same catalog revision.
    """
    max_level = max(0, min(int(max_level), 12))
    ensure_scale_schema(catalog)
    built: list[dict[str, int]] = []
    skipped: list[int] = []

    with catalog._lock:
        revision = _source_revision(catalog)
        for level in range(max_level + 1):
            key = f"universe_tiles:{level}"
            current = _state(catalog, key)
            if not force and current and current.get("revision") == revision:
                skipped.append(level)
                continue

            n = 1 << level
            catalog.db.execute("DELETE FROM universe_tiles WHERE zoom=?", (level,))
            catalog.db.execute(
                f"""
                INSERT INTO universe_tiles(zoom,tile_x,tile_y,item_count,sample_edition_id)
                SELECT ?,
                       MIN(CAST(space_x * {n} AS INTEGER), {n - 1}) AS tile_x,
                       MIN(CAST(space_y * {n} AS INTEGER), {n - 1}) AS tile_y,
                       COUNT(*) AS item_count,
                       MIN(id) AS sample_edition_id
                  FROM editions
                 WHERE space_x IS NOT NULL AND space_y IS NOT NULL
                 GROUP BY tile_x,tile_y
                """,
                (level,),
            )
            row = catalog.db.execute(
                "SELECT COUNT(*) AS cells, COALESCE(SUM(item_count),0) AS items "
                "FROM universe_tiles WHERE zoom=?",
                (level,),
            ).fetchone()
            info = {
                "level": level,
                "cells": int(row["cells"]),
                "items": int(row["items"]),
            }
            _set_state(catalog, key, {"revision": revision, **info})
            catalog.db.commit()
            built.append(info)

    return {"revision": revision, "built": built, "skipped": skipped, "max_level": max_level}


def universe_tile_status(catalog: CatalogDB) -> dict[str, object]:
    ensure_scale_schema(catalog)
    with catalog._lock:
        revision = _source_revision(catalog)
        rows = catalog.db.execute(
            "SELECT zoom,COUNT(*) AS cells,COALESCE(SUM(item_count),0) AS items "
            "FROM universe_tiles GROUP BY zoom ORDER BY zoom"
        ).fetchall()
        return {
            "revision": revision,
            "levels": [
                {"level": int(r["zoom"]), "cells": int(r["cells"]), "items": int(r["items"])}
                for r in rows
            ],
        }


def query_universe_tiles(
    catalog: CatalogDB,
    *,
    level: int,
    min_x: float = 0.0,
    max_x: float = 1.0,
    min_y: float = 0.0,
    max_y: float = 1.0,
    limit: int = 5000,
) -> list[dict[str, object]]:
    ensure_scale_schema(catalog)
    level = max(0, min(int(level), MAX_TILE_LEVEL))
    n = 1 << level
    min_x, max_x = sorted((max(0.0, min(1.0, min_x)), max(0.0, min(1.0, max_x))))
    min_y, max_y = sorted((max(0.0, min(1.0, min_y)), max(0.0, min(1.0, max_y))))
    tx0 = max(0, min(n - 1, int(math.floor(min_x * n))))
    tx1 = max(0, min(n - 1, int(math.floor(max_x * n))))
    ty0 = max(0, min(n - 1, int(math.floor(min_y * n))))
    ty1 = max(0, min(n - 1, int(math.floor(max_y * n))))
    limit = max(1, min(int(limit), 10000))

    with catalog._lock:
        rows = catalog.db.execute(
            "SELECT zoom,tile_x,tile_y,item_count FROM universe_tiles "
            "WHERE zoom=? AND tile_x BETWEEN ? AND ? AND tile_y BETWEEN ? AND ? "
            "ORDER BY item_count DESC,tile_x,tile_y LIMIT ?",
            (level, tx0, tx1, ty0, ty1, limit),
        ).fetchall()

    size = 1.0 / n
    return [
        {
            "zoom": int(r["zoom"]),
            "tile_x": int(r["tile_x"]),
            "tile_y": int(r["tile_y"]),
            "x": (int(r["tile_x"]) + 0.5) / n,
            "y": (int(r["tile_y"]) + 0.5) / n,
            "size": size,
            "count": int(r["item_count"]),
        }
        for r in rows
    ]

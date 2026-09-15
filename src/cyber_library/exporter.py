from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .database import CatalogDB
from .scale import MAX_TILE_LEVEL, build_universe_tiles, ensure_scale_schema
from .universe import space_metadata


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def export_universe_static(db_path: str | Path, output_dir: str | Path, *, max_level: int = MAX_TILE_LEVEL, rebuild: bool = False) -> dict:
    root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
    db = CatalogDB(db_path, index_on_write=False)
    try:
        ensure_scale_schema(db)
        with db._lock:
            existing = int(db.db.execute("SELECT COUNT(*) FROM universe_tiles").fetchone()[0])
        if rebuild or not existing:
            build_universe_tiles(db, max_level=max_level, force=rebuild)
        files = []
        max_level = max(0, min(int(max_level), MAX_TILE_LEVEL))
        for level in range(max_level + 1):
            with db._lock:
                rows = db.db.execute(
                    "SELECT tile_x,tile_y,item_count,sample_edition_id FROM universe_tiles WHERE zoom=? ORDER BY tile_x,tile_y",
                    (level,),
                ).fetchall()
            payload = {
                "zoom": level,
                "grid": 1 << level,
                "tiles": [
                    {"x": int(r["tile_x"]), "y": int(r["tile_y"]), "count": int(r["item_count"]), "sample_edition_id": r["sample_edition_id"]}
                    for r in rows
                ],
            }
            path = root / f"z{level}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            files.append({"path": path.name, "sha256": _sha256(path), "tiles": len(rows), "items": sum(int(r["item_count"]) for r in rows)})
        manifest = {"format": "cyber-library-universe-static", "version": 1, "generated_at": _now(), "space": space_metadata(), "files": files}
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**manifest, "manifest": str(manifest_path)}
    finally:
        db.close()


def export_analysis_bundle(db_path: str | Path, output_dir: str | Path) -> dict:
    root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
    data_path = root / "analyses.jsonl"
    db = CatalogDB(db_path, index_on_write=False)
    sources: set[str] = set()
    count = 0
    try:
        with data_path.open("w", encoding="utf-8", newline="\n") as fh, db._lock:
            rows = db.db.execute("SELECT analysis_key,edition_id,level,payload_json,created_at FROM analyses ORDER BY analysis_key").fetchall()
            for row in rows:
                try:
                    payload = json.loads(row["payload_json"])
                except json.JSONDecodeError:
                    payload = {"raw": row["payload_json"]}
                if isinstance(payload, dict):
                    for source in payload.get("sources") or []:
                        if isinstance(source, str): sources.add(source)
                record = {"analysis_key": row["analysis_key"], "edition_id": row["edition_id"], "level": row["level"], "payload": payload, "created_at": row["created_at"]}
                fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
        digest = _sha256(data_path)
        manifest = {"format": "cyber-library-analysis-bundle", "version": 1, "generated_at": _now(), "records": count, "data_file": data_path.name, "sha256": digest, "sources": sorted(sources)}
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {**manifest, "manifest": str(manifest_path)}
    finally:
        db.close()


def import_analysis_bundle(db_path: str | Path, bundle_dir: str | Path) -> dict:
    root = Path(bundle_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "cyber-library-analysis-bundle" or manifest.get("version") != 1:
        raise ValueError("unsupported analysis bundle format")
    data_path = root / str(manifest.get("data_file") or "analyses.jsonl")
    digest = _sha256(data_path)
    if digest != manifest.get("sha256"):
        raise ValueError("analysis bundle SHA-256 mismatch")
    db = CatalogDB(db_path, index_on_write=False)
    imported = 0
    try:
        with data_path.open("r", encoding="utf-8") as fh, db._lock:
            for line in fh:
                if not line.strip(): continue
                item = json.loads(line)
                db.db.execute(
                    "INSERT INTO analyses(analysis_key,edition_id,level,payload_json,created_at) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(analysis_key) DO UPDATE SET edition_id=excluded.edition_id,level=excluded.level,payload_json=excluded.payload_json,created_at=excluded.created_at",
                    (str(item["analysis_key"]), item.get("edition_id"), str(item["level"]), json.dumps(item.get("payload") or {}, ensure_ascii=False, separators=(",", ":")), str(item["created_at"])),
                )
                imported += 1
            db.db.commit()
        return {"imported": imported, "sha256": digest}
    finally:
        db.close()

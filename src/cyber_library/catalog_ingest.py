from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .cache import JsonCache
from .identifiers import InvalidISBN, normalize_isbn
from .sources.openlibrary import OpenLibraryClient


def catalog_path(root: str | Path, isbn: str) -> Path:
    isbn13 = normalize_isbn(isbn)
    return Path(root).resolve() / "data" / "catalog" / f"isbn-{isbn13}.json"


def _validate_record(value: Any, *, source_path: str = "<memory>") -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{source_path}: root must be a JSON object"]
    work = value.get("work")
    edition = value.get("edition")
    if not isinstance(work, dict):
        errors.append(f"{source_path}: missing work object")
    if not isinstance(edition, dict):
        errors.append(f"{source_path}: missing edition object")
        return errors
    if not str(edition.get("id") or "").strip():
        errors.append(f"{source_path}: edition.id is required")
    identifiers = edition.get("identifiers") or {}
    if not isinstance(identifiers, dict):
        errors.append(f"{source_path}: edition.identifiers must be an object")
        identifiers = {}
    valid_isbn = False
    for scheme in ("isbn13", "isbn10"):
        values = identifiers.get(scheme) or []
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            errors.append(f"{source_path}: {scheme} must be a list or string")
            continue
        for raw in values:
            try:
                normalize_isbn(str(raw))
                valid_isbn = True
            except InvalidISBN:
                errors.append(f"{source_path}: invalid {scheme} value {raw!r}")
    if not valid_isbn:
        errors.append(f"{source_path}: at least one valid ISBN-10/13 is required for data/catalog records")
    provenance = value.get("provenance") or []
    if not isinstance(provenance, list) or not provenance:
        errors.append(f"{source_path}: non-empty provenance is required")
    else:
        for index, item in enumerate(provenance):
            if not isinstance(item, dict) or not str(item.get("source") or "").strip():
                errors.append(f"{source_path}: provenance[{index}].source is required")
    analysis = value.get("analysis")
    if analysis is not None and not isinstance(analysis, dict):
        errors.append(f"{source_path}: analysis must be an object when present")
    return errors


def validate_catalog(root: str | Path = ".") -> dict[str, Any]:
    root = Path(root).resolve()
    folder = root / "data" / "catalog"
    errors: list[str] = []
    records = 0
    if folder.exists():
        for path in sorted(folder.rglob("*.json")):
            records += 1
            rel = path.relative_to(root).as_posix()
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{rel}: invalid JSON: {exc}")
                continue
            errors.extend(_validate_record(value, source_path=rel))
    return {"records": records, "errors": errors, "ok": not errors}


def add_isbn(
    isbn: str,
    *,
    root: str | Path = ".",
    contact: str | None = None,
    cache_path: str | Path = ".cyber-library/github-cache.sqlite3",
    overwrite: bool = False,
    client: OpenLibraryClient | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    isbn13 = normalize_isbn(isbn)
    target = catalog_path(root, isbn13)
    if target.exists() and not overwrite:
        return {"isbn13": isbn13, "path": target.relative_to(root).as_posix(), "changed": False, "reason": "already_exists"}

    owned_cache: JsonCache | None = None
    if client is None:
        cache_file = Path(cache_path)
        if not cache_file.is_absolute():
            cache_file = root / cache_file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        owned_cache = JsonCache(cache_file)
        client = OpenLibraryClient(cache=owned_cache, contact=contact)
    try:
        record = client.lookup_isbn(isbn13)
        payload = record.to_dict()
        errors = _validate_record(payload, source_path=target.relative_to(root).as_posix())
        if errors:
            raise ValueError("; ".join(errors))
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(target)
        return {
            "isbn13": isbn13,
            "path": target.relative_to(root).as_posix(),
            "changed": True,
            "title": payload.get("work", {}).get("title") or payload.get("edition", {}).get("title"),
            "source": "Open Library",
        }
    finally:
        if owned_cache is not None:
            owned_cache.close()


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library-catalog", description="GitHub-native sourced catalog maintenance.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-isbn", help="resolve one ISBN through Open Library and commit-ready JSON under data/catalog")
    add.add_argument("isbn")
    add.add_argument("--root", default=".")
    add.add_argument("--contact")
    add.add_argument("--cache", default=".cyber-library/github-cache.sqlite3")
    add.add_argument("--overwrite", action="store_true")

    check = sub.add_parser("validate", help="validate sourced records under data/catalog")
    check.add_argument("--root", default=".")

    args = parser.parse_args()
    if args.command == "add-isbn":
        try:
            result = add_isbn(args.isbn, root=args.root, contact=args.contact, cache_path=args.cache, overwrite=args.overwrite)
        except (InvalidISBN, ValueError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        return 0

    result = validate_catalog(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

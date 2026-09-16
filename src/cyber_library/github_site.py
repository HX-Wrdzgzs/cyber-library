from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import __version__
from .universe import isbn_space_point

REPO_URL = "https://github.com/HX-Wrdzgzs/cyber-library"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_records(root: Path) -> Iterable[tuple[Path, dict]]:
    seen: set[Path] = set()
    for base in (root / "data" / "catalog", root / "data" / "samples"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            if path in seen:
                continue
            seen.add(path)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("work"), dict) and isinstance(value.get("edition"), dict):
                yield path, value


def _first_isbn(record: dict) -> str | None:
    identifiers = record.get("edition", {}).get("identifiers") or {}
    for key in ("isbn13", "isbn10"):
        values = identifiers.get(key) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            if value:
                return str(value)
    return None


def _record_for_static(path: Path, record: dict, root: Path) -> dict:
    item = json.loads(json.dumps(record, ensure_ascii=False))
    item["repository_path"] = path.relative_to(root).as_posix()
    isbn = _first_isbn(item)
    if isbn:
        try:
            item["universe"] = isbn_space_point(isbn).to_dict()
        except (ValueError, TypeError):
            item["universe"] = None
    else:
        item["universe"] = None
    return item


def _lite_record(item: dict, record_file: str) -> dict:
    work = item.get("work") or {}
    edition = item.get("edition") or {}
    analysis = item.get("analysis") or {}
    return {
        "work": {
            "id": work.get("id"),
            "title": work.get("title"),
            "authors": list(work.get("authors") or []),
            "subjects": list(work.get("subjects") or []),
            "categories": list(work.get("categories") or analysis.get("categories") or []),
        },
        "edition": {
            "id": edition.get("id"),
            "work_id": edition.get("work_id"),
            "title": edition.get("title"),
            "language": edition.get("language"),
            "publishers": list(edition.get("publishers") or []),
            "publish_date": edition.get("publish_date"),
            "page_count": edition.get("page_count"),
            "identifiers": edition.get("identifiers") or {},
            "cover_url": edition.get("cover_url"),
            "physical_format": edition.get("physical_format"),
        },
        "analysis_level": analysis.get("level") or "L0",
        "repository_path": item.get("repository_path"),
        "universe": item.get("universe"),
        "record_file": record_file,
    }


def _markdown_files(root: Path) -> list[str]:
    ignored = {".git", ".venv", "node_modules", "_site", "dist"}
    files: list[str] = []
    for path in root.rglob("*.md"):
        if any(part in ignored for part in path.parts):
            continue
        files.append(path.relative_to(root).as_posix())
    return sorted(files)


def build_github_site(root: str | Path = ".", output: str | Path = "_site") -> dict:
    root = Path(root).resolve()
    output = Path(output).resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    web = root / "web"
    if not web.exists():
        raise FileNotFoundError("web directory not found")
    for path in web.iterdir():
        if path.is_file():
            shutil.copy2(path, output / path.name)

    data_dir = output / "site-data"
    records_dir = data_dir / "records"
    records_dir.mkdir(parents=True)

    full_records = [_record_for_static(path, record, root) for path, record in _iter_records(root)]
    full_records.sort(key=lambda item: (str(item.get("work", {}).get("title") or "").casefold(), str(item.get("edition", {}).get("id") or "")))

    index_records: list[dict] = []
    record_files: list[Path] = []
    for item in full_records:
        identity = str(item.get("edition", {}).get("id") or item.get("repository_path") or json.dumps(item, sort_keys=True))
        name = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20] + ".json"
        rel = f"records/{name}"
        path = data_dir / rel
        path.write_text(json.dumps(item, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        record_files.append(path)
        index_records.append(_lite_record(item, rel))

    categories = sorted({str(cat) for item in index_records for cat in (item.get("work", {}).get("categories") or []) if cat})
    subjects = sorted({str(subject) for item in index_records for subject in (item.get("work", {}).get("subjects") or []) if subject})
    stats = {"works": len({str(item.get('work', {}).get('id')) for item in index_records}), "editions": len(index_records), "llm_enabled": False}
    index = {
        "format": "cyber-library-github-index",
        "version": 2,
        "project_version": __version__,
        "generated_at": _now(),
        "repository": REPO_URL,
        "records": index_records,
        "categories": categories,
        "subjects": subjects,
        "stats": stats,
    }
    index_path = data_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    refs_path = root / "references" / "sources.json"
    refs = json.loads(refs_path.read_text(encoding="utf-8")) if refs_path.exists() else {"sources": []}
    references_path = data_dir / "references.json"
    references_path.write_text(json.dumps(refs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    project = {
        "name": "Cyber Library",
        "version": __version__,
        "repository": REPO_URL,
        "generated_at": _now(),
        "markdown": _markdown_files(root),
        "index": "./site-data/index.json",
        "references": "./site-data/references.json",
        "mode": "github-only",
    }
    project_path = data_dir / "project.json"
    project_path.write_text(json.dumps(project, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    files = [index_path, references_path, project_path, *record_files]
    manifest = {
        "format": "cyber-library-github-manifest",
        "version": 1,
        "project_version": __version__,
        "generated_at": _now(),
        "records": len(index_records),
        "files": [
            {"path": path.relative_to(data_dir).as_posix(), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(files)
        ],
    }
    manifest_path = data_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    (output / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copy2(output / "index.html", output / "404.html")
    return {
        "output": str(output),
        "records": len(index_records),
        "record_files": len(record_files),
        "categories": len(categories),
        "markdown": len(project["markdown"]),
        "manifest": str(manifest_path),
    }


_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def check_markdown_links(root: str | Path = ".") -> dict:
    root = Path(root).resolve()
    broken: list[dict[str, str]] = []
    checked = 0
    for rel in _markdown_files(root):
        path = root / rel
        text = path.read_text(encoding="utf-8")
        for match in _LINK_RE.finditer(text):
            raw = match.group(1).strip()
            target = raw.split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            local = target.split("#", 1)[0].split("?", 1)[0]
            if not local:
                continue
            checked += 1
            candidate = (path.parent / local).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                broken.append({"file": rel, "target": target, "reason": "outside repository"})
                continue
            if not candidate.exists():
                broken.append({"file": rel, "target": target, "reason": "missing"})
    return {"checked": checked, "broken": broken, "ok": not broken}


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library-github", description="Build and validate the serverless GitHub-only Cyber Library site.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--root", default=".")
    build.add_argument("--out", default="_site")
    check = sub.add_parser("check")
    check.add_argument("--root", default=".")
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build_github_site(args.root, args.out), ensure_ascii=False, indent=2))
        return 0
    result = check_markdown_links(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import gzip
import json
import tempfile
import time
from pathlib import Path

from .dump import import_openlibrary_dumps


def _isbn13(number: int) -> str:
    body = f"978{number % 1_000_000_000:09d}"
    total = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _write_row(fh, typ: str, key: str, payload: dict, modified: str = "2026-09-01T00:00:00Z") -> None:
    fh.write("\t".join([typ, key, "1", modified, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))]) + "\n")


def generate_synthetic_openlibrary(directory: str | Path, editions: int) -> list[Path]:
    editions = max(1, int(editions))
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    author_count = max(1, min(1000, editions // 20 or 1))
    work_count = max(1, editions // 3)
    authors = root / "authors.txt.gz"; works = root / "works.txt.gz"; edition_file = root / "editions.txt.gz"
    with gzip.open(authors, "wt", encoding="utf-8") as fh:
        for i in range(author_count):
            _write_row(fh, "/type/author", f"/authors/A{i}", {"name": f"Benchmark Author {i}"})
    with gzip.open(works, "wt", encoding="utf-8") as fh:
        for i in range(work_count):
            _write_row(fh, "/type/work", f"/works/W{i}", {"title": f"Benchmark Work {i}", "authors": [{"author": {"key": f"/authors/A{i % author_count}"}}], "subjects": ["Benchmark", f"Subject {i % 32}"]})
    with gzip.open(edition_file, "wt", encoding="utf-8") as fh:
        for i in range(editions):
            _write_row(fh, "/type/edition", f"/books/E{i}", {"title": f"Benchmark Edition {i}", "works": [{"key": f"/works/W{i % work_count}"}], "isbn_13": [_isbn13(i)], "publishers": [f"Benchmark Press {i % 16}"], "publish_date": str(1950 + i % 77), "languages": [{"key": "/languages/eng"}]})
    return [authors, works, edition_file]


def _run(root: Path, records: int, reindex: bool) -> dict[str, object]:
    dumps = generate_synthetic_openlibrary(root / "dumps", records)
    db_path = root / "catalog.sqlite3"
    started = time.perf_counter()
    result = import_openlibrary_dumps(dumps, db_path, reindex=reindex)
    seconds = max(time.perf_counter() - started, 1e-9)
    editions = int(result.get("editions") or 0)
    return {
        "requested_editions": int(records),
        "imported": result,
        "seconds": seconds,
        "editions_per_second": editions / seconds,
        "database_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "reindex": bool(reindex),
    }


def run_bulk_benchmark(records: int = 10_000, workdir: str | Path | None = None, reindex: bool = True) -> dict[str, object]:
    records = max(1, int(records))
    if workdir is not None:
        root = Path(workdir); root.mkdir(parents=True, exist_ok=True)
        result = _run(root, records, reindex)
        result["workdir"] = str(root)
        return result
    with tempfile.TemporaryDirectory(prefix="cyber-library-bench-") as directory:
        result = _run(Path(directory), records, reindex)
        result["workdir"] = None
        return result

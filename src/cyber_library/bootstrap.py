from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .dump import import_openlibrary_dumps

OPENLIBRARY_DUMP_URLS: dict[str, str] = {
    "authors": "https://openlibrary.org/data/ol_dump_authors_latest.txt.gz",
    "works": "https://openlibrary.org/data/ol_dump_works_latest.txt.gz",
    "editions": "https://openlibrary.org/data/ol_dump_editions_latest.txt.gz",
}

ProgressCallback = Callable[[dict], None]


class DownloadError(RuntimeError):
    pass


def _emit(progress: ProgressCallback | None, **payload) -> None:
    if progress:
        progress(payload)


def _target_name(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name:
        raise DownloadError(f"Cannot derive filename from URL: {url}")
    return name


def _gzip_magic_ok(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(2) == b"\x1f\x8b"
    except OSError:
        return False


def download_url(
    url: str,
    directory: str | Path,
    *,
    force: bool = False,
    timeout: float = 90.0,
    chunk_size: int = 8 * 1024 * 1024,
    progress: ProgressCallback | None = None,
) -> dict:
    """Download a large file with HTTP Range resume support.

    A partial transfer is stored as ``<name>.part`` and atomically renamed only
    after a complete response has been received. Existing completed files are
    reused unless ``force`` is true.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / _target_name(url)
    partial = target.with_name(target.name + ".part")

    if force:
        target.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)

    if target.exists() and target.stat().st_size > 0:
        if target.suffix == ".gz" and not _gzip_magic_ok(target):
            target.unlink()
        else:
            result = {
                "url": url,
                "path": str(target),
                "bytes": target.stat().st_size,
                "status": "existing",
            }
            _emit(progress, event="download-skip", **result)
            return result

    start = partial.stat().st_size if partial.exists() else 0
    headers = {
        "User-Agent": "CyberLibrary/1.0 (+https://github.com/HX-Wrdzgzs/cyber-library)",
        "Accept-Encoding": "identity",
    }
    if start:
        headers["Range"] = f"bytes={start}-"

    request = Request(url, headers=headers)
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code} while downloading {url}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DownloadError(f"Download failed for {url}: {exc}") from exc

    with response:
        status = int(getattr(response, "status", 200) or 200)
        resumed = bool(start and status == 206)
        if start and not resumed:
            start = 0
        mode = "ab" if resumed else "wb"
        content_length = response.headers.get("Content-Length")
        expected = None
        if content_length and str(content_length).isdigit():
            expected = start + int(content_length)
        content_range = response.headers.get("Content-Range")
        if content_range and "/" in content_range:
            total = content_range.rsplit("/", 1)[-1]
            if total.isdigit():
                expected = int(total)

        _emit(
            progress,
            event="download-start",
            url=url,
            final_url=getattr(response, "geturl", lambda: url)(),
            path=str(target),
            resumed=resumed,
            start=start,
            total=expected,
        )

        written = start
        next_report = written
        with partial.open(mode) as fh:
            while True:
                block = response.read(chunk_size)
                if not block:
                    break
                fh.write(block)
                written += len(block)
                if written >= next_report:
                    _emit(
                        progress,
                        event="download-progress",
                        path=str(target),
                        bytes=written,
                        total=expected,
                    )
                    next_report = written + 64 * 1024 * 1024
            fh.flush()
            os.fsync(fh.fileno())

    if expected is not None and written != expected:
        raise DownloadError(
            f"Incomplete download for {url}: got {written} bytes, expected {expected}"
        )
    if target.suffix == ".gz" and not _gzip_magic_ok(partial):
        raise DownloadError(f"Downloaded file is not gzip data: {partial}")

    os.replace(partial, target)
    result = {"url": url, "path": str(target), "bytes": written, "status": "downloaded"}
    _emit(progress, event="download-complete", **result)
    return result


def download_openlibrary_dump(
    kind: str,
    directory: str | Path,
    *,
    force: bool = False,
    progress: ProgressCallback | None = None,
) -> dict:
    try:
        url = OPENLIBRARY_DUMP_URLS[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown Open Library dump kind: {kind}") from exc
    result = download_url(url, directory, force=force, progress=progress)
    result["kind"] = kind
    return result


def bootstrap_openlibrary(
    db_path: str | Path = ".cyber-library/catalog.sqlite3",
    download_dir: str | Path = ".cyber-library/dumps",
    *,
    kinds: tuple[str, ...] | list[str] = ("authors", "works", "editions"),
    force_download: bool = False,
    limit_each: int | None = None,
    reindex: bool = True,
    progress: ProgressCallback | None = None,
) -> dict:
    """Download the official latest Open Library dumps and build the catalog."""
    ordered = list(dict.fromkeys(kinds))
    unknown = [kind for kind in ordered if kind not in OPENLIBRARY_DUMP_URLS]
    if unknown:
        raise ValueError(f"Unknown dump kinds: {', '.join(unknown)}")

    downloads = [
        download_openlibrary_dump(kind, download_dir, force=force_download, progress=progress)
        for kind in ordered
    ]
    paths = [item["path"] for item in downloads]
    _emit(progress, event="import-start", paths=paths, db=str(db_path))
    imported = import_openlibrary_dumps(paths, db_path, limit_each=limit_each, reindex=reindex)
    result = {
        "database": str(db_path),
        "download_directory": str(download_dir),
        "downloads": downloads,
        "import": imported,
    }
    manifest = Path(download_dir) / "bootstrap-manifest.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _emit(progress, event="import-complete", result=imported, manifest=str(manifest))
    return result

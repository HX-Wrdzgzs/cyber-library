from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bootstrap import DownloadError, OPENLIBRARY_DUMP_URLS, bootstrap_openlibrary
from .content import ContentError, RIGHTS_VALUES, extract_document
from .database import CatalogDB
from .dump import import_openlibrary_dumps
from .identifiers import InvalidISBN, normalize_isbn
from .server import serve
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError
from .taxonomy import categories
from .universe import isbn_space_point, space_metadata


def _dump(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _bootstrap_progress(event: dict) -> None:
    kind = event.get("event")
    if kind == "download-start":
        resumed = " (resume)" if event.get("resumed") else ""
        print(f"[download]{resumed} {event.get('path')}", file=sys.stderr)
    elif kind == "download-progress":
        current = int(event.get("bytes") or 0)
        total = event.get("total")
        if total:
            percent = current * 100 / int(total)
            print(f"[download] {current / 1024**3:.2f} / {int(total) / 1024**3:.2f} GiB ({percent:.1f}%)", file=sys.stderr)
        else:
            print(f"[download] {current / 1024**3:.2f} GiB", file=sys.stderr)
    elif kind == "download-complete":
        print(f"[download] complete: {event.get('path')}", file=sys.stderr)
    elif kind == "download-skip":
        print(f"[download] reuse: {event.get('path')}", file=sys.stderr)
    elif kind == "import-start":
        print(f"[import] building catalog: {event.get('db')}", file=sys.stderr)
    elif kind == "import-complete":
        print(f"[import] complete: {event.get('manifest')}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cyber-library",
        description="Book catalog, knowledge graph, evidence-aware analysis and ISBN universe.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("isbn", help="validate and normalize an ISBN")
    cmd.add_argument("value")

    cmd = sub.add_parser("space", help="map an ISBN into Cyber Library ISBN space")
    cmd.add_argument("value")

    sub.add_parser("categories", help="list top-level knowledge categories")

    cmd = sub.add_parser("resolve", help="resolve and optionally analyze one ISBN")
    cmd.add_argument("value")
    cmd.add_argument("--analyze", action="store_true", help="alias for --analysis auto")
    cmd.add_argument("--analysis", choices=["none", "catalog", "source", "auto"], default="none")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db", help="optional local bulk catalog database")
    cmd.add_argument("--no-live", action="store_true", help="do not fall back to Open Library")
    cmd.add_argument("--no-llm", action="store_true", help="disable configured LLM enhancement")
    cmd.add_argument("--contact", help="contact address used to identify Open Library requests")

    cmd = sub.add_parser("search", help="search the local catalog, with optional live fallback")
    cmd.add_argument("query")
    cmd.add_argument("--limit", type=int, default=20)
    cmd.add_argument("--category")
    cmd.add_argument("--language")
    cmd.add_argument("--year-from", type=int)
    cmd.add_argument("--year-to", type=int)
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db")
    cmd.add_argument("--no-live", action="store_true")
    cmd.add_argument("--contact")

    cmd = sub.add_parser("graph", help="build a knowledge graph around one ISBN")
    cmd.add_argument("value")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db")
    cmd.add_argument("--no-live", action="store_true")
    cmd.add_argument("--no-llm", action="store_true")
    cmd.add_argument("--contact")

    cmd = sub.add_parser("import-dump", help="import one or more Open Library TSV/TSV.GZ dumps")
    cmd.add_argument("paths", nargs="+")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit-each", type=int)
    cmd.add_argument("--skip-reindex", action="store_true", help="skip final search/ISBN-space index rebuild")

    cmd = sub.add_parser(
        "bootstrap-openlibrary",
        help="download official latest Open Library dumps, import them and rebuild indexes",
    )
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--download-dir", default=".cyber-library/dumps")
    cmd.add_argument(
        "--kinds",
        nargs="+",
        choices=sorted(OPENLIBRARY_DUMP_URLS),
        default=["authors", "works", "editions"],
        help="dump groups to download/import",
    )
    cmd.add_argument("--force-download", action="store_true", help="discard completed/partial files and download again")
    cmd.add_argument("--limit-each", type=int, help="development/testing limit per dump")
    cmd.add_argument("--skip-reindex", action="store_true", help="skip final search/ISBN-space index rebuild")

    cmd = sub.add_parser("reindex", help="rebuild search and ISBN-space indexes")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("stats", help="show local catalog counts")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("analyze-file", help="analyze a local TXT/Markdown/EPUB/PDF")
    cmd.add_argument("path")
    cmd.add_argument("--rights", required=True, choices=sorted(RIGHTS_VALUES), help="your basis for analyzing the supplied content")
    cmd.add_argument("--title")
    cmd.add_argument("--isbn")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db")
    cmd.add_argument("--no-live", action="store_true")
    cmd.add_argument("--no-llm", action="store_true")
    cmd.add_argument("--contact")

    cmd = sub.add_parser("inspect", help="pretty-print a normalized JSON record")
    cmd.add_argument("path")

    cmd = sub.add_parser("serve", help="run the API and web explorer")
    cmd.add_argument("--host", default="127.0.0.1")
    cmd.add_argument("--port", type=int, default=8080)
    cmd.add_argument("--web-root", default="web")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db", help="optional local bulk catalog database")
    cmd.add_argument("--no-live", action="store_true")
    cmd.add_argument("--no-llm", action="store_true")
    cmd.add_argument("--contact")

    args = parser.parse_args()

    if args.command == "inspect":
        _dump(json.loads(Path(args.path).read_text(encoding="utf-8")))
        return 0

    if args.command == "isbn":
        try:
            print(normalize_isbn(args.value))
            return 0
        except InvalidISBN as exc:
            print(str(exc))
            return 2

    if args.command == "space":
        try:
            _dump({"space": space_metadata(), "point": isbn_space_point(args.value).to_dict()})
            return 0
        except (InvalidISBN, ValueError) as exc:
            _dump({"error": "invalid_isbn", "detail": str(exc)})
            return 2

    if args.command == "categories":
        _dump({"categories": categories()})
        return 0

    if args.command == "import-dump":
        _dump(import_openlibrary_dumps(args.paths, args.db, limit_each=args.limit_each, reindex=not args.skip_reindex))
        return 0

    if args.command == "bootstrap-openlibrary":
        try:
            _dump(
                bootstrap_openlibrary(
                    db_path=args.db,
                    download_dir=args.download_dir,
                    kinds=args.kinds,
                    force_download=args.force_download,
                    limit_each=args.limit_each,
                    reindex=not args.skip_reindex,
                    progress=_bootstrap_progress,
                )
            )
            return 0
        except (DownloadError, ValueError, OSError) as exc:
            _dump({"error": "bootstrap_failed", "detail": str(exc)})
            return 6

    if args.command == "reindex":
        db = CatalogDB(args.db, index_on_write=False)
        try:
            _dump(db.reindex())
            return 0
        finally:
            db.close()

    if args.command == "stats":
        db = CatalogDB(args.db)
        try:
            _dump(db.stats())
            return 0
        finally:
            db.close()

    if args.command == "resolve":
        service = CatalogService(args.cache, args.contact, args.db, not args.no_live, use_llm=not args.no_llm)
        try:
            mode = "auto" if args.analyze else args.analysis
            _dump(service.resolve_isbn(args.value, mode).to_dict())
            return 0
        except InvalidISBN as exc:
            _dump({"error": "invalid_isbn", "detail": str(exc)})
            return 2
        except NotFound:
            _dump({"error": "not_found"})
            return 3
        except SourceError as exc:
            _dump({"error": "upstream_error", "detail": str(exc)})
            return 4
        finally:
            service.close()

    if args.command == "search":
        service = CatalogService(args.cache, args.contact, args.db, not args.no_live, use_llm=False)
        try:
            _dump({"query": args.query, "results": service.search(args.query, limit=args.limit, category=args.category, language=args.language, year_from=args.year_from, year_to=args.year_to)})
            return 0
        except SourceError as exc:
            _dump({"error": "upstream_error", "detail": str(exc)})
            return 4
        finally:
            service.close()

    if args.command == "graph":
        service = CatalogService(args.cache, args.contact, args.db, not args.no_live, use_llm=not args.no_llm)
        try:
            _dump(service.graph(args.value))
            return 0
        except (InvalidISBN, NotFound, SourceError) as exc:
            _dump({"error": "graph_failed", "detail": str(exc)})
            return 4
        finally:
            service.close()

    if args.command == "analyze-file":
        try:
            document = extract_document(args.path, args.rights, args.title)
        except ContentError as exc:
            _dump({"error": "content_error", "detail": str(exc)})
            return 5
        service = CatalogService(args.cache, args.contact, args.db, not args.no_live, use_llm=not args.no_llm)
        try:
            _dump(service.analyze_document(document, isbn=args.isbn).to_dict())
            return 0
        except (InvalidISBN, NotFound, SourceError, ValueError) as exc:
            _dump({"error": "analysis_failed", "detail": str(exc)})
            return 4
        finally:
            service.close()

    if args.command == "serve":
        serve(args.host, args.port, args.web_root, args.cache, args.contact, args.db, not args.no_live, use_llm=not args.no_llm)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

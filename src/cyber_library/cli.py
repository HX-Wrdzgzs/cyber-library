from __future__ import annotations

import argparse
import json
from pathlib import Path

from .database import CatalogDB
from .dump import import_openlibrary_dump
from .identifiers import InvalidISBN, normalize_isbn
from .server import serve
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("isbn", help="validate and normalize an ISBN")
    cmd.add_argument("value")

    cmd = sub.add_parser("resolve", help="resolve one ISBN")
    cmd.add_argument("value")
    cmd.add_argument("--analyze", action="store_true")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db", help="optional local bulk catalog database")
    cmd.add_argument("--no-live", action="store_true", help="do not fall back to the Open Library API")
    cmd.add_argument("--contact", help="contact email used to identify low-volume API requests")

    cmd = sub.add_parser("import-dump", help="import an Open Library TSV/TSV.GZ dump")
    cmd.add_argument("path")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int)

    cmd = sub.add_parser("stats", help="show local catalog counts")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("inspect", help="pretty-print a normalized JSON record")
    cmd.add_argument("path")

    cmd = sub.add_parser("serve", help="run the local API + web explorer")
    cmd.add_argument("--host", default="127.0.0.1")
    cmd.add_argument("--port", type=int, default=8080)
    cmd.add_argument("--web-root", default="web")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--db", help="optional local bulk catalog database")
    cmd.add_argument("--no-live", action="store_true")
    cmd.add_argument("--contact")

    args = parser.parse_args()

    if args.command == "inspect":
        print(json.dumps(json.loads(Path(args.path).read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
        return 0

    if args.command == "isbn":
        try:
            print(normalize_isbn(args.value))
            return 0
        except InvalidISBN as exc:
            print(str(exc))
            return 2

    if args.command == "import-dump":
        print(json.dumps(import_openlibrary_dump(args.path, args.db, args.limit), ensure_ascii=False, indent=2))
        return 0

    if args.command == "stats":
        db = CatalogDB(args.db)
        try:
            print(json.dumps(db.stats(), ensure_ascii=False, indent=2))
            return 0
        finally:
            db.close()

    if args.command == "resolve":
        service = CatalogService(args.cache, args.contact, args.db, not args.no_live)
        try:
            print(json.dumps(service.resolve_isbn(args.value, args.analyze).to_dict(), ensure_ascii=False, indent=2))
            return 0
        except InvalidISBN as exc:
            print(json.dumps({"error": "invalid_isbn", "detail": str(exc)}))
            return 2
        except NotFound:
            print('{"error":"not_found"}')
            return 3
        except SourceError as exc:
            print(json.dumps({"error": "upstream_error", "detail": str(exc)}))
            return 4
        finally:
            service.close()

    if args.command == "serve":
        serve(args.host, args.port, args.web_root, args.cache, args.contact, args.db, not args.no_live)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

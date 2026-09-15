from __future__ import annotations

import argparse
import json

from .cache import JsonCache
from .database import CatalogDB
from .identifiers import InvalidISBN, normalize_isbn
from .reconciliation import links_for, reconcile_isbn
from .sources.registry import register_builtin_sources
from .sources.wikidata import WikidataError


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cyber-library-source",
        description="External source registry and entity reconciliation tools.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list registered external source adapters")

    cmd = sub.add_parser("status", help="show one source adapter's capabilities")
    cmd.add_argument("source", nargs="?", default="wikidata")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--contact")

    cmd = sub.add_parser("reconcile", help="reconcile a local ISBN against an external source")
    cmd.add_argument("isbn")
    cmd.add_argument("--source", default="wikidata")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--contact")

    cmd = sub.add_parser("links", help="show persisted external links for a local ISBN")
    cmd.add_argument("isbn")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    args = parser.parse_args()
    sources = register_builtin_sources()

    if args.command == "list":
        _dump({"sources": sources.names()})
        return 0

    if args.command == "status":
        cache = JsonCache(args.cache)
        try:
            adapter = sources.create(args.source, cache=cache, contact=args.contact)
            _dump(adapter.health())
            return 0
        except KeyError as exc:
            _dump({"error": "unknown_source", "detail": str(exc)})
            return 2
        finally:
            cache.close()

    if args.command == "reconcile":
        cache = JsonCache(args.cache)
        db = CatalogDB(args.db)
        try:
            adapter = sources.create(args.source, cache=cache, contact=args.contact)
            _dump(reconcile_isbn(db, adapter, args.isbn))
            return 0
        except KeyError as exc:
            _dump({"error": "unknown_source", "detail": str(exc)})
            return 2
        except InvalidISBN as exc:
            _dump({"error": "invalid_isbn", "detail": str(exc)})
            return 2
        except LookupError as exc:
            _dump({"error": "not_in_local_catalog", "detail": str(exc)})
            return 3
        except WikidataError as exc:
            _dump({"error": "source_error", "detail": str(exc)})
            return 4
        finally:
            db.close()
            cache.close()

    if args.command == "links":
        db = CatalogDB(args.db)
        try:
            isbn13 = normalize_isbn(args.isbn)
            record = db.lookup_isbn(isbn13)
            if record is None:
                _dump({"error": "not_in_local_catalog", "isbn13": isbn13})
                return 3
            _dump({"isbn13": isbn13, "edition_id": record.edition.id, "links": links_for(db, "edition", record.edition.id)})
            return 0
        except InvalidISBN as exc:
            _dump({"error": "invalid_isbn", "detail": str(exc)})
            return 2
        finally:
            db.close()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

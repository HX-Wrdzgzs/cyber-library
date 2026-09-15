from __future__ import annotations

import argparse
import json

from .cache import JsonCache
from .refresh import OpenLibraryRecentClient, get_refresh_checkpoint, refresh_openlibrary, set_refresh_checkpoint
from .sources.openlibrary import SourceError


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cyber-library-refresh",
        description="Bounded Open Library RecentChanges refresh for a dump-backed local catalog.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("status", help="show the stored Open Library refresh checkpoint")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("seed", help="set the refresh checkpoint after importing a known dump snapshot")
    cmd.add_argument("timestamp")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("run", help="apply a bounded recent-change window")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--cache", default=".cyber-library/cache.sqlite3")
    cmd.add_argument("--contact")
    cmd.add_argument("--since", help="override the stored checkpoint for this run")
    cmd.add_argument("--max-changes", type=int, default=250)
    cmd.add_argument("--max-documents", type=int, default=500)
    cmd.add_argument("--rebuild-universe", action="store_true")

    args = parser.parse_args()

    if args.command == "status":
        from .database import CatalogDB

        db = CatalogDB(args.db)
        try:
            _dump({"source": "openlibrary", "checkpoint": get_refresh_checkpoint(db)})
            return 0
        finally:
            db.close()

    if args.command == "seed":
        from .database import CatalogDB

        db = CatalogDB(args.db)
        try:
            _dump({"source": "openlibrary", "checkpoint": set_refresh_checkpoint(db, args.timestamp)})
            return 0
        except ValueError as exc:
            _dump({"error": "invalid_timestamp", "detail": str(exc)})
            return 2
        finally:
            db.close()

    if args.command == "run":
        cache = JsonCache(args.cache)
        try:
            client = OpenLibraryRecentClient(cache=cache, contact=args.contact)
            _dump(
                refresh_openlibrary(
                    args.db,
                    client=client,
                    since=args.since,
                    max_changes=args.max_changes,
                    max_documents=args.max_documents,
                    rebuild_universe=args.rebuild_universe,
                )
            )
            return 0
        except ValueError as exc:
            _dump({"error": "refresh_configuration", "detail": str(exc)})
            return 2
        except SourceError as exc:
            _dump({"error": "openlibrary_error", "detail": str(exc)})
            return 4
        finally:
            cache.close()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

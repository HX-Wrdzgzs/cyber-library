from __future__ import annotations

import argparse
import json

from .database import CatalogDB
from .navigation import author_timeline, concept_graph, publisher_map


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library-knowledge", description="Navigate the local cross-work knowledge space.")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("concept", help="build a cross-work concept graph")
    cmd.add_argument("subject")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int, default=40)

    cmd = sub.add_parser("author", help="build an author work timeline")
    cmd.add_argument("name")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int, default=100)

    cmd = sub.add_parser("publisher", help="build a publisher/category map")
    cmd.add_argument("name")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int, default=150)

    args = parser.parse_args()
    db = CatalogDB(args.db)
    try:
        if args.command == "concept":
            _dump(concept_graph(db, args.subject, args.limit))
        elif args.command == "author":
            _dump(author_timeline(db, args.name, args.limit))
        else:
            _dump(publisher_map(db, args.name, args.limit))
        return 0
    except ValueError as exc:
        _dump({"error": "invalid_query", "detail": str(exc)})
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

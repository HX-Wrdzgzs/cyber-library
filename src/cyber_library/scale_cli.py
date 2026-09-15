from __future__ import annotations

import argparse
import json

from .database import CatalogDB
from .scale import build_universe_tiles, universe_tile_status


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cyber-library-scale",
        description="Offline scale/index maintenance for large Cyber Library catalogs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("build-universe", help="build resumable ISBN-universe density tiles")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--max-level", type=int, default=8)
    cmd.add_argument("--force", action="store_true")

    cmd = sub.add_parser("rebuild", help="rebuild search/coordinates, then universe tiles")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--max-level", type=int, default=8)
    cmd.add_argument("--force-tiles", action="store_true")

    cmd = sub.add_parser("status", help="show scale-index status")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    args = parser.parse_args()
    db = CatalogDB(args.db, index_on_write=False)
    try:
        if args.command == "build-universe":
            _dump(build_universe_tiles(db, max_level=args.max_level, force=args.force))
            return 0
        if args.command == "rebuild":
            search = db.reindex()
            tiles = build_universe_tiles(db, max_level=args.max_level, force=args.force_tiles)
            _dump({"reindex": search, "universe": tiles})
            return 0
        if args.command == "status":
            _dump(universe_tile_status(db))
            return 0
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json

from .exporter import export_analysis_bundle, export_universe_static, import_analysis_bundle


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library-export", description="Export static/distributable Cyber Library artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("universe", help="export precomputed ISBN Universe JSON tiles")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--out", default=".cyber-library/public-universe")
    cmd.add_argument("--max-level", type=int, default=8)
    cmd.add_argument("--rebuild", action="store_true")

    cmd = sub.add_parser("analyses", help="export a verified analysis JSONL bundle")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--out", default=".cyber-library/analysis-bundle")

    cmd = sub.add_parser("import-analyses", help="verify and import an analysis bundle")
    cmd.add_argument("bundle")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    args = parser.parse_args()
    try:
        if args.command == "universe":
            _dump(export_universe_static(args.db, args.out, max_level=args.max_level, rebuild=args.rebuild))
        elif args.command == "analyses":
            _dump(export_analysis_bundle(args.db, args.out))
        else:
            _dump(import_analysis_bundle(args.db, args.bundle))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        _dump({"error": "export_failed", "detail": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

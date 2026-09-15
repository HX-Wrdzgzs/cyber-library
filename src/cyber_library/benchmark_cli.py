from __future__ import annotations

import argparse
import json

from .benchmark import run_bulk_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-library-benchmark", description="Synthetic Open Library bulk-import benchmark.")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("bulk", help="generate synthetic dumps and benchmark the real importer")
    cmd.add_argument("--records", type=int, default=10_000, help="number of synthetic editions")
    cmd.add_argument("--workdir", help="keep generated dumps/database in this directory")
    cmd.add_argument("--no-reindex", action="store_true")
    args = parser.parse_args()
    result = run_bulk_benchmark(args.records, args.workdir, reindex=not args.no_reindex)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json

from .database import CatalogDB
from .semantic import EmbeddingClient, EmbeddingError, build_embedding_index, embedding_status, semantic_search


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _client() -> EmbeddingClient:
    client = EmbeddingClient.from_env()
    if client is None:
        raise EmbeddingError(
            "Embedding backend is not configured. Set CYBER_LIBRARY_EMBEDDING_BASE_URL and CYBER_LIBRARY_EMBEDDING_MODEL."
        )
    return client


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cyber-library-semantic",
        description="Optional OpenAI-compatible embedding index and semantic search.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("index", help="incrementally embed local catalog editions")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int)
    cmd.add_argument("--batch-size", type=int, default=32)
    cmd.add_argument("--force", action="store_true")

    cmd = sub.add_parser("status", help="show embedding index status")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")

    cmd = sub.add_parser("search", help="semantic-only search over indexed editions")
    cmd.add_argument("query")
    cmd.add_argument("--db", default=".cyber-library/catalog.sqlite3")
    cmd.add_argument("--limit", type=int, default=20)
    cmd.add_argument("--category")
    cmd.add_argument("--language")
    cmd.add_argument("--year-from", type=int)
    cmd.add_argument("--year-to", type=int)

    args = parser.parse_args()
    db = CatalogDB(args.db, index_on_write=False)
    try:
        if args.command == "status":
            _dump(embedding_status(db))
            return 0
        client = _client()
        if args.command == "index":
            _dump(build_embedding_index(db, client, batch_size=args.batch_size, limit=args.limit, force=args.force))
            return 0
        if args.command == "search":
            _dump(
                {
                    "query": args.query,
                    "model": client.model_name,
                    "results": semantic_search(
                        db,
                        client,
                        args.query,
                        limit=args.limit,
                        category=args.category,
                        language=args.language,
                        year_from=args.year_from,
                        year_to=args.year_to,
                    ),
                }
            )
            return 0
        return 1
    except EmbeddingError as exc:
        _dump({"error": "embedding_error", "detail": str(exc)})
        return 6
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

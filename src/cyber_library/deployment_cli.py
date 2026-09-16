from __future__ import annotations

import argparse
import json
import os

from .database import CatalogDB
from .deployment import DeploymentError, OpenSearchAdapter, PostgresCatalogAdapter, QdrantAdapter, S3ArtifactPublisher
from .semantic import EmbeddingClient


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _required(value, name: str):
    if value is None:
        raise DeploymentError(f"{name} is not configured; see docs/deployment-adapters.md")
    return value


def main() -> int:
    parser=argparse.ArgumentParser(prog="cyber-library-deploy",description="Optional production deployment adapters.")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("status",help="show deployment adapter configuration without contacting services")

    p=sub.add_parser("postgres-sync",help="mirror canonical catalog records into PostgreSQL/PostGIS")
    p.add_argument("--db",default=".cyber-library/catalog.sqlite3");p.add_argument("--batch-size",type=int,default=1000);p.add_argument("--limit",type=int)
    p=sub.add_parser("postgres-search",help="query the PostgreSQL mirror")
    p.add_argument("query");p.add_argument("--limit",type=int,default=20)

    p=sub.add_parser("opensearch-sync",help="index canonical catalog records in OpenSearch")
    p.add_argument("--db",default=".cyber-library/catalog.sqlite3");p.add_argument("--batch-size",type=int,default=500);p.add_argument("--limit",type=int)
    p=sub.add_parser("opensearch-search",help="query the OpenSearch index")
    p.add_argument("query");p.add_argument("--limit",type=int,default=20)

    p=sub.add_parser("qdrant-sync",help="push an existing local embedding model into Qdrant")
    p.add_argument("--db",default=".cyber-library/catalog.sqlite3");p.add_argument("--model");p.add_argument("--batch-size",type=int,default=256);p.add_argument("--limit",type=int)
    p=sub.add_parser("qdrant-query",help="embed text with configured embedding endpoint and query Qdrant")
    p.add_argument("query");p.add_argument("--limit",type=int,default=20)

    p=sub.add_parser("publish-dir",help="publish a static artifact directory to S3-compatible object storage")
    p.add_argument("directory")

    args=parser.parse_args()
    try:
        postgres=PostgresCatalogAdapter.from_env();opensearch=OpenSearchAdapter.from_env();qdrant=QdrantAdapter.from_env();s3=S3ArtifactPublisher.from_env()
        if args.command=="status":
            _dump({"postgres":postgres.health() if postgres else {"name":"postgres","configured":False},"opensearch":opensearch.health() if opensearch else {"name":"opensearch","configured":False},"qdrant":qdrant.health() if qdrant else {"name":"qdrant","configured":False},"s3":s3.health() if s3 else {"name":"s3","configured":False}});return 0
        if args.command=="postgres-sync":
            adapter=_required(postgres,"CYBER_LIBRARY_POSTGRES_DSN");db=CatalogDB(args.db,index_on_write=False)
            try:_dump(adapter.sync_from_sqlite(db,batch_size=args.batch_size,limit=args.limit));return 0
            finally:db.close()
        if args.command=="postgres-search":_dump({"results":_required(postgres,"CYBER_LIBRARY_POSTGRES_DSN").search(args.query,limit=args.limit)});return 0
        if args.command=="opensearch-sync":
            adapter=_required(opensearch,"CYBER_LIBRARY_OPENSEARCH_URL");db=CatalogDB(args.db,index_on_write=False)
            try:_dump(adapter.sync_from_sqlite(db,batch_size=args.batch_size,limit=args.limit));return 0
            finally:db.close()
        if args.command=="opensearch-search":_dump({"results":_required(opensearch,"CYBER_LIBRARY_OPENSEARCH_URL").search(args.query,limit=args.limit)});return 0
        if args.command=="qdrant-sync":
            adapter=_required(qdrant,"CYBER_LIBRARY_QDRANT_URL");model=(args.model or os.getenv("CYBER_LIBRARY_EMBEDDING_MODEL","")).strip()
            if not model:raise DeploymentError("--model or CYBER_LIBRARY_EMBEDDING_MODEL is required")
            db=CatalogDB(args.db,index_on_write=False)
            try:_dump(adapter.sync_embeddings(db,model,batch_size=args.batch_size,limit=args.limit));return 0
            finally:db.close()
        if args.command=="qdrant-query":
            adapter=_required(qdrant,"CYBER_LIBRARY_QDRANT_URL");embedding=_required(EmbeddingClient.from_env(),"CYBER_LIBRARY_EMBEDDING_BASE_URL / CYBER_LIBRARY_EMBEDDING_MODEL")
            vector=embedding.embed([args.query])[0];_dump({"query":args.query,"model":embedding.model_name,"results":adapter.query(vector,limit=args.limit)});return 0
        if args.command=="publish-dir":_dump(_required(s3,"CYBER_LIBRARY_S3_BUCKET").publish_directory(args.directory));return 0
    except DeploymentError as exc:
        _dump({"error":"deployment_failed","detail":str(exc)});return 2
    return 1


if __name__=="__main__":raise SystemExit(main())

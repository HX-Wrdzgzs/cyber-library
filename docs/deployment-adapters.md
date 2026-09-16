# Deployment Adapters

Cyber Library keeps SQLite as the portable canonical core. Production services are optional mirrors/adapters, so losing OpenSearch, Qdrant, PostgreSQL or object storage does not make the canonical catalog unreadable.

## Status

```bash
cyber-library-deploy status
```

This command only inspects configuration; it does not contact remote services.

## PostgreSQL / PostGIS

Install the optional driver:

```bash
pip install -e '.[postgres]'
export CYBER_LIBRARY_POSTGRES_DSN='postgresql://user:pass@host/db'
cyber-library-deploy postgres-sync --db .cyber-library/catalog.sqlite3
```

The adapter creates `cyber_books`, a GIN full-text index, ISBN and coordinate indexes, and attempts to enable PostGIS. If the database role cannot create the PostGIS extension, numeric `space_x` / `space_y` remain fully usable and sync still works.

Query the mirror:

```bash
cyber-library-deploy postgres-search 'machine learning'
```

The PostgreSQL mirror is derived data. The SQLite catalog remains the provenance-bearing source of truth.

## OpenSearch

Cyber Library talks to the REST API directly, including the standard `_bulk` indexing and `_search` endpoints.

```bash
export CYBER_LIBRARY_OPENSEARCH_URL='https://search.example'
export CYBER_LIBRARY_OPENSEARCH_INDEX='cyber-library'
cyber-library-deploy opensearch-sync --db .cyber-library/catalog.sqlite3
cyber-library-deploy opensearch-search 'machine learning'
```

Optional authentication variables:

```text
CYBER_LIBRARY_OPENSEARCH_USERNAME
CYBER_LIBRARY_OPENSEARCH_PASSWORD
CYBER_LIBRARY_OPENSEARCH_BEARER_TOKEN
```

Bulk responses are checked for per-action failures. A partially failed bulk response is treated as an error instead of being silently accepted.

## Qdrant ANN backend

Qdrant is an optional large embedding-index backend. First create embeddings through the existing semantic pipeline, then push one model into Qdrant:

```bash
export CYBER_LIBRARY_QDRANT_URL='http://127.0.0.1:6333'
export CYBER_LIBRARY_QDRANT_COLLECTION='cyber_library'
cyber-library-deploy qdrant-sync \
  --db .cyber-library/catalog.sqlite3 \
  --model your-embedding-model
```

Edition IDs are converted to deterministic UUIDv5 point IDs; the original edition ID and model remain in Qdrant payloads.

To query using the configured OpenAI-compatible embedding endpoint:

```bash
cyber-library-deploy qdrant-query 'introductory machine learning books'
```

The adapter uses Qdrant's collection points upsert and universal points query REST endpoints.

## S3-compatible object storage

Install the optional publisher dependency:

```bash
pip install -e '.[s3]'
```

Configure standard AWS credentials through the environment/instance role, then Cyber Library-specific destination settings:

```bash
export CYBER_LIBRARY_S3_BUCKET='cyber-library-public'
export CYBER_LIBRARY_S3_PREFIX='universe/v1'
# Optional for R2, MinIO and other S3-compatible services:
export CYBER_LIBRARY_S3_ENDPOINT_URL='https://...'
export CYBER_LIBRARY_S3_REGION='auto'
```

Export and publish:

```bash
cyber-library-export universe \
  --db .cyber-library/catalog.sqlite3 \
  --out public-universe
cyber-library-deploy publish-dir public-universe
```

`manifest.json` is uploaded with `no-cache`; immutable-ish tile files use a longer cache lifetime. The publisher reports destination keys, byte sizes and SHA-256 digests.

## Failure boundaries

Deployment adapters never overwrite Open Library raw JSON or the evidence model. They are rebuildable projections. This is intentional:

```text
canonical SQLite catalog
        |
        +--> PostgreSQL/PostGIS mirror
        +--> OpenSearch lexical index
        +--> Qdrant vector index
        +--> static export --> S3/R2/MinIO
```

For large deployments, schedule these syncs after dump import / refresh completion and monitor their exit status independently.

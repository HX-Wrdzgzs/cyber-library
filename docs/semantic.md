# Semantic and Hybrid Search

Cyber Library can optionally use an OpenAI-compatible embeddings endpoint. The base
catalog remains usable without any embedding service.

## Configuration

```bash
export CYBER_LIBRARY_EMBEDDING_BASE_URL='http://127.0.0.1:8000/v1'
export CYBER_LIBRARY_EMBEDDING_MODEL='your-embedding-model'
export CYBER_LIBRARY_EMBEDDING_API_KEY='optional-key'
```

The endpoint is expected to implement the common `POST /embeddings` request shape.

## Incremental indexing

Embeddings are stored in the same local SQLite catalog, keyed by edition and model.
The indexer skips editions already indexed by that model, so interrupted or partial
runs can simply be started again.

```bash
cyber-library-semantic index \
  --db .cyber-library/catalog.sqlite3 \
  --batch-size 32
```

Limit a first pass to popular/test data if desired:

```bash
cyber-library-semantic index --limit 10000
```

Rebuild the selected model from scratch:

```bash
cyber-library-semantic index --force
```

Inspect stored models and counts:

```bash
cyber-library-semantic status
```

## Search behavior

Semantic-only CLI search:

```bash
cyber-library-semantic search 'introductory books about galaxies'
```

When the main Cyber Library service has both an embedding backend configured and at
least one stored vector for that model, normal `/api/search` and `cyber-library`
search requests use hybrid ranking automatically. Lexical and semantic rankings are
combined using Reciprocal Rank Fusion (RRF).

If the embedding service is unavailable, normal catalog search continues instead of
failing the whole request.

## Scale boundary

The built-in SQLite semantic backend deliberately does not pretend to be a
billion-vector database. It scans at most a bounded number of locally indexed
vectors per query and is intended for progressive/popular-book indexing, local
collections and development deployments.

For truly global dense-vector retrieval, the `EmbeddingClient` and persisted schema
provide a migration boundary for a dedicated vector database later. Bibliographic
truth remains in the canonical catalog; vectors are derived indexes.

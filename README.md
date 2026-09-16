# Cyber Library

> Explore humanity's published knowledge.

Cyber Library is an open, machine-readable and AI-assisted map of books and published knowledge. It separates bibliographic facts from generated interpretation, and separates physical publication identifiers from semantic knowledge navigation.

## What v3 includes

- Work / Edition / Author / Identifier separation
- ISBN-10 / ISBN-13 validation and normalization
- Open Library monthly-dump bootstrap with resumable downloads
- bounded, checkpointed Open Library incremental refresh between dump snapshots
- SQLite canonical catalog with FTS/fallback search
- optional OpenAI-compatible embeddings with lexical/semantic RRF ranking
- Wikidata ISBN/entity reconciliation and author authority candidates
- Crossref ISBN → DOI linking plus deposited citation/relation evidence
- Library of Congress LCDB ISBN and Name Authority File SRU adapters
- multilingual subject normalization while preserving upstream raw records
- L0/L1/L2/L3 evidence-aware book intelligence
- lawful TXT / Markdown / EPUB and optional PDF full-text analysis
- per-book graphs and mind maps
- cross-work Knowledge Space: concepts, author timelines and publisher views
- clean-room Hilbert ISBN Universe with scalable density tiles
- static Universe export and portable SHA-256-verified analysis bundles
- optional PostgreSQL/PostGIS, OpenSearch, Qdrant and S3-compatible deployment adapters
- browser explorer, REST API, Docker and Python 3.11–3.13 CI

Cyber Library does **not** claim ISBN, Open Library, Library of Congress, Wikidata or any other single source contains every book ever created. ISBN is an edition identifier, not a universal definition of a work and not a subject classification system.

## Install

```bash
pip install -e .
```

Optional features:

```bash
pip install -e '.[pdf]'
pip install -e '.[postgres]'
pip install -e '.[s3]'
pip install -e '.[deploy]'
```

## Quick start

```bash
cyber-library isbn 0-306-40615-2
cyber-library resolve 9780140328721 --analysis auto
cyber-library serve --db .cyber-library/catalog.sqlite3
```

Open `http://127.0.0.1:8080`.

## Build and refresh the local catalog

For bulk catalog creation use Open Library's official monthly dumps rather than API crawling:

```bash
cyber-library bootstrap-openlibrary
```

This downloads authors / works / editions with HTTP Range resume, imports them into SQLite, rebuilds search indexes, generates ISBN Universe density tiles and seeds the incremental-refresh checkpoint from dump `last_modified` timestamps.

Between snapshots, use the bounded RecentChanges bridge:

```bash
cyber-library-refresh status --db .cyber-library/catalog.sqlite3
cyber-library-refresh run --db .cyber-library/catalog.sqlite3
```

The checkpoint advances only after the complete selected window succeeds. See [`docs/refresh.md`](docs/refresh.md).

## Search and semantic retrieval

```bash
cyber-library search "machine learning" \
  --db .cyber-library/catalog.sqlite3 \
  --no-live
```

Optional embeddings:

```bash
export CYBER_LIBRARY_EMBEDDING_BASE_URL='http://127.0.0.1:8000/v1'
export CYBER_LIBRARY_EMBEDDING_MODEL='your-embedding-model'
cyber-library-semantic index --db .cyber-library/catalog.sqlite3
```

When an embedding index exists, normal search can use hybrid Reciprocal Rank Fusion. Embedding-service failures fall back to lexical search. See [`docs/semantic.md`](docs/semantic.md).

## Knowledge Space

Knowledge Space is separate from ISBN Universe and derives relations from explicit catalog facts rather than model association.

```bash
cyber-library-knowledge concept "Machine learning" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge author "Author Name" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge publisher "Publisher Name" --db .cyber-library/catalog.sqlite3
```

The browser includes a **知识空间** tab. See [`docs/knowledge-space.md`](docs/knowledge-space.md).

## External sources and authority evidence

```bash
cyber-library-source list
cyber-library-source reconcile-all 9780306406157 --db .cyber-library/catalog.sqlite3
cyber-library-source authority "Author Name" --source wikidata
cyber-library-source authority "Author Name" --source loc
cyber-library-source citations 10.xxxx/example --source crossref
```

Successful source matches are kept as provenance-bearing external links rather than silently overwriting canonical bibliographic fields. Authority candidates never auto-merge same-name people. See [`docs/sources.md`](docs/sources.md).

## ISBN Universe and portable artifacts

```bash
cyber-library space 9780306406157
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
cyber-library-export universe --db .cyber-library/catalog.sqlite3 --out public-universe
```

The Hilbert mapping is an independent implementation; no `phiresky/isbn-visualization` source is copied. See [`docs/universe.md`](docs/universe.md) and [`docs/export.md`](docs/export.md).

Portable analysis cache:

```bash
cyber-library-export analyses --db .cyber-library/catalog.sqlite3 --out analysis-bundle
cyber-library-export import-analyses analysis-bundle --db another-catalog.sqlite3
```

## Evidence-aware book intelligence

```text
L0  bibliographic metadata only
L1  catalog-derived interpretation
L2  source-backed structured material
L3  lawful full-text analysis
```

A metadata-only record must not pretend to have chapter-level understanding.

Analyze a file you are allowed to process:

```bash
cyber-library analyze-file book.epub --rights user-provided --isbn 9780140328721
```

Supported rights declarations include `public-domain`, `open-license`, `licensed` and `user-provided`.

## Production deployment adapters

The portable SQLite catalog remains the source of truth. v3 adds rebuildable production mirrors:

```text
SQLite canonical catalog
        |
        +--> PostgreSQL / optional PostGIS
        +--> OpenSearch
        +--> Qdrant
        +--> static exports --> S3 / R2 / MinIO
```

Inspect configuration without contacting services:

```bash
cyber-library-deploy status
```

Examples:

```bash
export CYBER_LIBRARY_POSTGRES_DSN='postgresql://user:pass@host/db'
cyber-library-deploy postgres-sync --db .cyber-library/catalog.sqlite3

export CYBER_LIBRARY_OPENSEARCH_URL='https://search.example'
cyber-library-deploy opensearch-sync --db .cyber-library/catalog.sqlite3

export CYBER_LIBRARY_QDRANT_URL='http://127.0.0.1:6333'
cyber-library-deploy qdrant-sync --db .cyber-library/catalog.sqlite3 --model your-embedding-model

export CYBER_LIBRARY_S3_BUCKET='cyber-library-public'
cyber-library-deploy publish-dir public-universe
```

See [`docs/deployment-adapters.md`](docs/deployment-adapters.md).

## Bulk-import benchmark

```bash
cyber-library-benchmark bulk --records 10000
```

This generates deterministic synthetic Open Library-style dumps and runs the real importer. It is a regression/hardware-sizing tool, not a synthetic throughput guarantee for the full corpus.

## REST API

```text
GET  /api/health
GET  /api/stats
GET  /api/categories
GET  /api/resolve?isbn=...&analysis=auto
GET  /api/search?q=...
GET  /api/graph?isbn=...
GET  /api/knowledge/concept?subject=...
GET  /api/knowledge/author?name=...
GET  /api/knowledge/publisher?name=...
GET  /api/universe?min_x=...&max_x=...&min_y=...&max_y=...&z=...
POST /api/analyze-text
```

## Docker

```bash
docker compose up --build
```

See [`docs/deployment.md`](docs/deployment.md).

## Data model

```text
Author ─────┐
            ▼
           Work ─── Subject / Concept
          /  |  \
         ▼   ▼   ▼
   Edition Edition Edition
      │       │       │
     ISBN    ISBN   other IDs
      │
      └── Wikidata / DOI / LoC / other external links
```

## Repository layout

```text
src/cyber_library/   catalog, analysis, search, sources, refresh, exports and deployment adapters
web/                 browser explorer
schemas/             machine-readable entity/analysis schemas
docs/                architecture, data, search, scaling, sources and deployment docs
tests/               unit/regression tests
references/          prior-art references
```

## Licensing and data rights

Original Cyber Library source in this repository is MIT licensed. Third-party metadata, covers, book text and referenced projects can have separate licenses or terms. See [`docs/licensing.md`](docs/licensing.md) and [`NOTICE.md`](NOTICE.md).

## Project status

The planned repository roadmap is complete at **v3.0.0**. The canonical local/portable core is functional, and production deployment/source extensions are implemented behind replaceable adapters. Future connectors can be added without changing the Work / Edition / Evidence model. See [`ROADMAP.md`](ROADMAP.md).

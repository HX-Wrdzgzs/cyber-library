# Cyber Library

> Explore humanity's published knowledge.

Cyber Library is an open, machine-readable and AI-assisted map of books and published knowledge.

This repository contains an end-to-end local system: bibliographic ingestion, ISBN/Work/Edition normalization, evidence-aware analysis, lexical + semantic retrieval, source reconciliation, knowledge graphs, a scalable ISBN Universe, a web explorer, and offline scale/index tooling.

## Highlights

- Work / Edition / Identifier separation
- ISBN-10 / ISBN-13 validation and normalization
- Open Library low-volume resolver
- Resumable Open Library monthly dump bootstrap
- SQLite catalog with FTS fallback search
- Optional OpenAI-compatible embeddings and hybrid lexical/semantic ranking
- Pluggable external-source registry and persisted entity links
- Wikidata ISBN reconciliation
- Subject taxonomy and provenance/evidence tracking
- Catalog/source/full-text analysis with explicit evidence levels
- Optional OpenAI-compatible LLM enhancement
- TXT / Markdown / EPUB ingestion and optional PDF extraction
- Mind maps and knowledge graphs
- Clean-room ISBN Hilbert-space visualization
- Progressive ISBN Universe rendering with precomputed density tiles
- REST API and browser explorer
- Docker / Compose deployment
- Python 3.11–3.13 CI

## Install

```bash
pip install -e .
```

Optional PDF support:

```bash
pip install -e '.[pdf]'
```

## Quick start

```bash
cyber-library isbn 0-306-40615-2
cyber-library resolve 9780140328721 --analysis auto
cyber-library serve --db .cyber-library/catalog.sqlite3
```

Then open `http://127.0.0.1:8080`.

## Build a local Open Library catalog

The recommended bulk path is the official monthly dumps, not aggressive API crawling.

```bash
cyber-library bootstrap-openlibrary
```

The command downloads the latest authors / works / editions dumps with HTTP Range resume support, imports them into SQLite, rebuilds the search/ISBN indexes, and generates scalable ISBN Universe density tiles. Files are stored under `.cyber-library/` by default.

To import already-downloaded dumps:

```bash
cyber-library import-dump \
  ol_dump_authors_latest.txt.gz \
  ol_dump_works_latest.txt.gz \
  ol_dump_editions_latest.txt.gz \
  --db .cyber-library/catalog.sqlite3
```

## Scale maintenance

```bash
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
cyber-library-scale status --db .cyber-library/catalog.sqlite3
```

See [`docs/scale.md`](docs/scale.md).

## Search

```bash
cyber-library search "machine learning" \
  --db .cyber-library/catalog.sqlite3 \
  --no-live
```

The local catalog uses SQLite FTS when available and a fallback query path otherwise.

## Optional semantic / hybrid search

```bash
export CYBER_LIBRARY_EMBEDDING_BASE_URL='http://127.0.0.1:8000/v1'
export CYBER_LIBRARY_EMBEDDING_MODEL='your-embedding-model'
export CYBER_LIBRARY_EMBEDDING_API_KEY='optional-key'

cyber-library-semantic index --db .cyber-library/catalog.sqlite3
cyber-library-semantic status --db .cyber-library/catalog.sqlite3
cyber-library-semantic search "introductory books about galaxies" \
  --db .cyber-library/catalog.sqlite3
```

When embeddings are configured and the selected model has indexed editions, normal Cyber Library search combines lexical and semantic ranking using Reciprocal Rank Fusion. If the embedding backend is unavailable, search falls back to the local lexical index. The built-in SQLite vector path is deliberately bounded; see [`docs/semantic.md`](docs/semantic.md).

## External sources and entity reconciliation

Cyber Library keeps external entity systems separate from canonical bibliographic records. Source adapters expose a common contract and external links are persisted with their own provenance.

List built-in sources:

```bash
cyber-library-source list
```

Inspect Wikidata support without making a network request:

```bash
cyber-library-source status wikidata
```

Reconcile an ISBN that already exists in the local catalog:

```bash
cyber-library-source reconcile 9780306406157 \
  --source wikidata \
  --db .cyber-library/catalog.sqlite3
```

Read the stored external links later without contacting Wikidata:

```bash
cyber-library-source links 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

The Wikidata adapter uses ISBN-13 property `P212` and ISBN-10 property `P957`. See [`docs/sources.md`](docs/sources.md).

## ISBN Universe

```bash
cyber-library space 9780306406157
```

The browser Universe uses precomputed density tiles for distant views and concrete edition points for close or filtered views. Cyber Library does not copy `phiresky/isbn-visualization` source code; it uses its own ISBN-space implementation while retaining that project as prior art.

## Evidence-aware intelligence

AI/algorithmic output is kept separate from bibliographic facts:

```text
L0  bibliographic metadata only
L1  catalog-derived interpretation
L2  source-backed structured material
L3  lawful full-text analysis
```

A system must not claim chapter-level understanding when the available evidence is only metadata.

Analyze a local file you are allowed to process:

```bash
cyber-library analyze-file book.epub \
  --rights user-provided \
  --isbn 9780140328721
```

Accepted rights declarations include public-domain, open-license, licensed and user-provided.

## Optional LLM

```bash
export CYBER_LIBRARY_LLM_BASE_URL='http://127.0.0.1:8000/v1'
export CYBER_LIBRARY_LLM_MODEL='your-model'
export CYBER_LIBRARY_LLM_API_KEY='optional-key'
```

Without an LLM endpoint, deterministic local analysis remains available.

## API

```text
GET  /api/health
GET  /api/stats
GET  /api/categories
GET  /api/resolve?isbn=...&analysis=auto
GET  /api/search?q=...
GET  /api/graph?isbn=...
GET  /api/universe?min_x=...&max_x=...&min_y=...&max_y=...&z=...
POST /api/analyze-text
```

`/api/search` automatically becomes hybrid when a configured embedding model has a local index. `/api/universe` can return either `mode: "tiles"` or `mode: "points"`.

## Docker

```bash
docker compose up --build
```

See [`docs/deployment.md`](docs/deployment.md).

## Data model

```text
Author ─────┐
            ▼
           Work
          /  |  \
         /   |   \
        ▼    ▼    ▼
   Edition Edition Edition
      │       │       │
     ISBN    ISBN   other IDs
```

ISBN is an edition identifier, not a universal definition of a book and not a subject classification system. External identifiers such as Wikidata IDs are linked rather than silently merged into source records.

## Repository layout

```text
src/cyber_library/   catalog, analysis, retrieval, sources, API and scale tooling
web/                 browser explorer
schemas/             machine-readable entity/analysis schemas
docs/                architecture, API, scaling, semantic search, sources and deployment
tests/               unit tests
references/          upstream/prior-art references
```

## Licensing and data rights

The original Cyber Library source in this repository is MIT licensed. Third-party data, cover images, book text, metadata sources and referenced projects can have separate licenses or terms. See [`docs/licensing.md`](docs/licensing.md) and [`NOTICE.md`](NOTICE.md).

## Project status

The local end-to-end architecture is functional. It does not claim that Open Library, Wikidata, ISBN, or any other single source contains every book ever created. Coverage grows by adding legitimate sources and identifiers while keeping provenance explicit.

# Cyber Library

> Explore humanity's published knowledge.

Cyber Library is an open, machine-readable and AI-assisted map of books and published knowledge. It separates bibliographic facts from generated interpretation and separates physical publication identifiers from semantic knowledge navigation.

## What v2.1 includes

- Work / Edition / Author / Identifier separation
- ISBN-10 / ISBN-13 validation and normalization
- Open Library monthly-dump bootstrap with resumable downloads
- bounded, checkpointed Open Library incremental refresh between dump snapshots
- SQLite catalog with FTS/fallback search
- optional OpenAI-compatible embeddings with lexical/semantic RRF ranking
- Wikidata ISBN reconciliation and Crossref ISBN → DOI linking
- Wikidata author authority candidates with ISNI / VIAF / LCNAF / GND identifiers
- Crossref deposited DOI references and relation evidence
- conservative multilingual subject normalization while preserving upstream raw records
- L0/L1/L2/L3 evidence-aware book intelligence
- lawful TXT / Markdown / EPUB and optional PDF full-text analysis
- per-book graphs and mind maps
- cross-work Knowledge Space: concepts, author timelines and publisher views
- clean-room Hilbert ISBN Universe with scalable density tiles
- static Universe export for CDN/static hosting
- portable, SHA-256-verified analysis bundles
- browser explorer, REST API, Docker and Python 3.11–3.13 CI

Cyber Library does **not** claim ISBN or Open Library contains every book ever created. ISBN is an edition identifier, not a universal definition of a work and not a subject classification system.

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

Open `http://127.0.0.1:8080`.

## Build the local catalog

For bulk catalog creation use Open Library's official monthly dumps rather than API crawling:

```bash
cyber-library bootstrap-openlibrary
```

This downloads authors / works / editions with HTTP Range resume, imports them into SQLite, rebuilds search indexes, generates ISBN Universe density tiles and seeds the incremental-refresh checkpoint from dump `last_modified` timestamps.

Import already-downloaded dumps:

```bash
cyber-library import-dump \
  ol_dump_authors_latest.txt.gz \
  ol_dump_works_latest.txt.gz \
  ol_dump_editions_latest.txt.gz \
  --db .cyber-library/catalog.sqlite3
```

## Incremental refresh

Monthly dumps remain the bulk baseline. RecentChanges is only a bounded bridge between snapshots:

```bash
cyber-library-refresh status --db .cyber-library/catalog.sqlite3
cyber-library-refresh run \
  --db .cyber-library/catalog.sqlite3 \
  --max-changes 250 \
  --max-documents 500
```

The checkpoint advances only after the full selected window is observed and every selected document succeeds. Truncated windows or failures keep the checkpoint unchanged. See [`docs/refresh.md`](docs/refresh.md).

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
export CYBER_LIBRARY_EMBEDDING_API_KEY='optional-key'

cyber-library-semantic index --db .cyber-library/catalog.sqlite3
cyber-library-semantic search "introductory books about galaxies" \
  --db .cyber-library/catalog.sqlite3
```

When an embedding index exists, normal search automatically uses hybrid Reciprocal Rank Fusion. Embedding-service failures fall back to lexical search.

## Knowledge Space

Knowledge Space is separate from ISBN Universe. It derives relations from explicit catalog facts, not LLM association.

```bash
cyber-library-knowledge concept "Machine learning" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge author "Author Name" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge publisher "Publisher Name" --db .cyber-library/catalog.sqlite3
```

The browser includes a **知识空间** tab. See [`docs/knowledge-space.md`](docs/knowledge-space.md).

## External identifiers, authority and citation evidence

```bash
cyber-library-source list
cyber-library-source reconcile-all 9780306406157 \
  --db .cyber-library/catalog.sqlite3
cyber-library-source links 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

Find same-label author authority candidates without auto-merging them:

```bash
cyber-library-source authority "Author Name" --source wikidata
```

Inspect Crossref-deposited DOI references/relations without recursively crawling targets:

```bash
cyber-library-source citations 10.xxxx/example --source crossref
```

Successful ISBN matches are persisted independently. Authority candidates stay candidates (`auto_merge=false`). Citation relationships remain source-labelled evidence. See [`docs/sources.md`](docs/sources.md).

## ISBN Universe

```bash
cyber-library space 9780306406157
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
```

The browser uses density tiles at distant zooms and concrete edition points at close/filtered zooms. The Hilbert mapping is an independent implementation; no `phiresky/isbn-visualization` source is copied.

Export static map data:

```bash
cyber-library-export universe \
  --db .cyber-library/catalog.sqlite3 \
  --out public-universe
```

See [`docs/universe.md`](docs/universe.md) and [`docs/export.md`](docs/export.md).

## Book intelligence

Generated output is explicitly bounded by evidence:

```text
L0  bibliographic metadata only
L1  catalog-derived interpretation
L2  source-backed structured material
L3  lawful full-text analysis
```

A metadata-only record must not pretend to have chapter-level understanding.

Analyze a file you are allowed to process:

```bash
cyber-library analyze-file book.epub \
  --rights user-provided \
  --isbn 9780140328721
```

Supported rights declarations include `public-domain`, `open-license`, `licensed` and `user-provided`.

Optional OpenAI-compatible LLM:

```bash
export CYBER_LIBRARY_LLM_BASE_URL='http://127.0.0.1:8000/v1'
export CYBER_LIBRARY_LLM_MODEL='your-model'
export CYBER_LIBRARY_LLM_API_KEY='optional-key'
```

Without an LLM, deterministic local analysis remains available.

## Portable analysis cache

```bash
cyber-library-export analyses \
  --db .cyber-library/catalog.sqlite3 \
  --out analysis-bundle

cyber-library-export import-analyses analysis-bundle \
  --db another-catalog.sqlite3
```

The bundle manifest contains record count, source references and SHA-256 integrity data. See [`docs/export.md`](docs/export.md).

## Bulk-import benchmark

```bash
cyber-library-benchmark bulk --records 10000
```

This generates deterministic synthetic Open Library-style dumps and runs the real importer. It is a regression/hardware-sizing tool, not a synthetic throughput guarantee for the full corpus. See [`docs/benchmark.md`](docs/benchmark.md).

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
      └── Wikidata / DOI / other external links
```

## Repository layout

```text
src/cyber_library/   catalog, analysis, search, sources, refresh, exports and navigation
web/                 browser explorer
schemas/             machine-readable entity/analysis schemas
docs/                architecture, data, search, scaling, refresh and deployment docs
tests/               unit/regression tests
references/          prior-art references
```

## Licensing and data rights

Original Cyber Library source in this repository is MIT licensed. Third-party metadata, covers, book text and referenced projects can have separate licenses or terms. See [`docs/licensing.md`](docs/licensing.md) and [`NOTICE.md`](NOTICE.md).

## Project status

The local/portable v2.1 core is functional. PostgreSQL/PostGIS, OpenSearch, object-storage publishing, national-library connectors and large-scale ANN backends are optional deployment/source adapters, not prerequisites for the core catalog and knowledge-navigation model. See [`ROADMAP.md`](ROADMAP.md).

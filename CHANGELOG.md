# Changelog

## 3.0.0 — 2026-09-16

- Added PostgreSQL catalog mirroring with GIN full-text indexes and optional PostGIS point materialization.
- Added OpenSearch REST indexing/search adapter using `_bulk` and `_search`.
- Added Qdrant vector adapter for large embedding indexes using collection upsert and points query APIs.
- Added S3-compatible static artifact publishing for Universe/analysis exports.
- Added Library of Congress LCDB ISBN reconciliation through SRU `bath.isbn`.
- Added Library of Congress Name Authority File candidate lookup through SRU `bath.personalName` with `auto_merge=false`.
- Added `cyber-library-deploy`, deployment extras, environment configuration, documentation and offline adapter tests.
- Closed the planned repository roadmap while keeping adapter contracts open for future sources/backends.

## 2.1.0 — 2026-09-16

- Added exact-label Wikidata author authority candidate lookup.
- Added ISNI (`P213`), VIAF (`P214`), LCNAF (`P244`) and GND (`P227`) identifiers to authority candidates when present.
- Authority candidates are explicitly non-automatic (`auto_merge=false`) to avoid same-name person merges.
- Added Crossref deposited DOI reference graphs, relation metadata and `is-referenced-by-count` signal.
- Added `cyber-library-source authority` and `cyber-library-source citations` commands.
- Added mocked source tests so CI does not depend on Wikidata or Crossref uptime.

## 2.0.0 — 2026-09-16

- Added Knowledge Space navigation built from catalog facts rather than model guesses.
- Added cross-work concept graphs, author timelines and publisher/category views.
- Added Knowledge Space REST endpoints, CLI and browser view.
- Added conservative Chinese/Japanese subject normalization at Open Library bulk/live/refresh ingestion boundaries while preserving upstream `raw_json`.
- Added synthetic bulk-import benchmarking using the real dump importer.
- Added static ISBN Universe JSON export and portable SHA-256-verified analysis-cache bundles.

## 1.3.0 — 2026-09-16

- Added bounded Open Library RecentChanges refresh for dump-backed catalogs.
- Added fail-safe refresh checkpoints and dependent search reindexing.
- Added dump `last_modified` checkpoint seeding.

## 1.2.1 — 2026-09-16

- Added Crossref ISBN reconciliation and DOI links.
- Added multi-source reconciliation with isolated upstream failures.

## 1.2.0 — 2026-09-16

- Added external source registry, Wikidata ISBN reconciliation and persistent entity links.

## 1.1.1 — 2026-09-16

- Added optional embeddings, incremental semantic indexing and RRF hybrid search.

## 1.1.0 — 2026-09-16

- Added resumable Open Library bootstrap and scalable ISBN Universe density tiles.

## 1.0.0 — 2026-09-15

- Added the evidence-aware local catalog, analysis engine, graphs, ISBN Universe, web explorer, REST API, Docker deployment and Python 3.11–3.13 CI.

## 0.1.0 — 2026-09-15

- Initial catalog prototype, Open Library dump import and Work / Edition model.

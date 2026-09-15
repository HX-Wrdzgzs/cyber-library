# Changelog

## 2.0.0 — 2026-09-16

- Added Knowledge Space navigation built from catalog facts rather than model guesses.
- Added cross-work concept graphs with co-subject relationships.
- Added author timelines based on linked local editions and publication years.
- Added publisher/category/subject/year/language aggregation views.
- Added Knowledge Space REST endpoints, CLI and browser view.
- Added conservative Chinese/Japanese subject alias normalization at Open Library bulk/live/refresh ingestion boundaries while preserving upstream `raw_json`.
- Added synthetic bulk-import benchmarking that exercises the real dump importer.
- Added static ISBN Universe JSON export for CDN/static hosting.
- Added portable analysis-cache bundles with source manifests and SHA-256 integrity validation.
- Added tests and CI smoke coverage for the new v2 commands.

## 1.3.0 — 2026-09-16

- Added bounded Open Library RecentChanges refresh for dump-backed catalogs.
- Added persistent refresh checkpoints with fail-safe advancement rules.
- Added Work/Author dependent search reindexing during incremental refresh.
- Added optional Universe tile rebuild after edition changes.
- Added dump `last_modified` tracking and automatic checkpoint seeding after complete bootstrap imports.
- Added `cyber-library-refresh` CLI with `status`, `seed` and `run` commands.
- Added refresh, dump timestamp and bootstrap checkpoint tests.

## 1.2.1 — 2026-09-16

- Added Crossref ISBN reconciliation using the public REST `filter=isbn:` path.
- Added DOI links, Crossref title/type/publisher/author/date metadata and polite-pool contact support.
- Added `reconcile-all` so registered ISBN sources can run in one pass while isolating individual source failures.
- Added shared `ExternalSourceError` base class and Crossref/Wikidata adapter tests with mocked HTTP responses.

## 1.2.0 — 2026-09-16

- Added reusable external source adapter/registry contracts.
- Added Wikidata ISBN entity reconciliation and persistent external links.
- Added `cyber-library-source` CLI for discovery, health, reconciliation and local link inspection.

## 1.1.1 — 2026-09-16

- Added optional OpenAI-compatible embeddings, incremental semantic indexing and RRF hybrid search.
- Added graceful lexical fallback when the embedding service is unavailable.

## 1.1.0 — 2026-09-16

- Added resumable Open Library bootstrap downloads and one-command catalog creation.
- Added resumable ISBN-Universe density tile generation and progressive browser rendering.

## 1.0.0 — 2026-09-15

- Added the evidence-aware local catalog, analysis engine, knowledge graph, ISBN Universe, web explorer, REST API, Docker deployment and Python 3.11–3.13 CI.

## 0.1.0 — 2026-09-15

- Initial catalog prototype, Open Library dump import and Work / Edition model.

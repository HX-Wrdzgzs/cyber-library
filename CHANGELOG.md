# Changelog

## 3.1.0 — 2026-09-16

- Made GitHub-only operation a first-class public deployment path using repository data, GitHub Actions and GitHub Pages.
- Added `cyber-library-github build` to generate a Pages-ready static site with `.nojekyll`, static catalog, project metadata and reference data.
- Added `cyber-library-github check` to validate repository-local Markdown links.
- Added a browser static API shim so the shared UI can search committed records, resolve committed ISBNs, render Knowledge Space and ISBN Universe views, and perform deterministic browser-local text analysis without a server.
- Added automatic fallback to the normal Python REST API when static site data is absent.
- Added a GitHub Pages workflow and CI-built static-site artifact.
- Added machine-readable `references/sources.json`, human-readable `docs/references.md`, and `docs/github-only.md`.
- Added a sourced committed Open Library ISBN record under `data/catalog/`.

## 3.0.0 — 2026-09-16

- Added PostgreSQL mirror support with GIN search indexes and optional PostGIS point materialization.
- Added OpenSearch REST `_bulk` indexing and `_search` support.
- Added Qdrant collection/upsert/query adapter for large embedding indexes.
- Added S3-compatible publisher for static Universe and analysis artifacts.
- Added Library of Congress LCDB ISBN and Name Authority File SRU adapters.
- Added `cyber-library-deploy` and offline deployment adapter tests.

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

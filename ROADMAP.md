# Roadmap

## v1.0 — End-to-end local Cyber Library

- [x] Work / Edition / Identifier model
- [x] Open Library low-volume resolver and monthly dump importer
- [x] SQLite catalog with FTS / fallback search
- [x] subject taxonomy, provenance and evidence model
- [x] L0/L1/L2/L3 catalog/source/full-text intelligence
- [x] optional OpenAI-compatible LLM
- [x] TXT / Markdown / EPUB and optional PDF ingestion
- [x] mind map and per-book knowledge graph
- [x] clean-room ISBN Hilbert space
- [x] web explorer, REST API, Docker and Python 3.11–3.13 CI

## v1.1–v1.3 — Scale, retrieval and sources

- [x] one-command resumable Open Library dump bootstrap
- [x] resumable offline ISBN-universe density index
- [x] optional OpenAI-compatible embedding backend and RRF hybrid search
- [x] bounded checkpointed Open Library incremental refresh pipeline
- [x] pluggable source adapter / registry contract
- [x] Wikidata ISBN reconciliation and persisted external links
- [x] Crossref ISBN → DOI reconciliation
- [x] multi-source reconciliation with isolated source failures

## v2.0 — Knowledge navigation and portable deployment

- [x] dedicated synthetic bulk-import benchmark using the real importer
- [x] multilingual subject normalization at ingestion and query boundaries
- [x] cross-work concept graph
- [x] author timeline
- [x] publisher/category map
- [x] browser Knowledge Space view and REST endpoints
- [x] precomputed public static ISBN Universe JSON export
- [x] portable analysis cache bundle with source manifest and SHA-256 validation

## v2.1 — Authority and relationship evidence

- [x] Wikidata author authority candidates with ISNI / VIAF / LCNAF / GND identifiers
- [x] ambiguity-safe authority policy (`auto_merge=false`)
- [x] Crossref deposited DOI references
- [x] Crossref relation metadata and `is-referenced-by-count` influence signal
- [x] source CLI commands for authority and citation evidence

## v3.0 — Production deployment adapters and additional library authority

- [x] PostgreSQL mirror with GIN search indexes and optional PostGIS point materialization
- [x] OpenSearch REST adapter using `_bulk` and `_search`
- [x] S3-compatible object-storage publisher for static Universe / analysis artifacts
- [x] Qdrant ANN/vector adapter using collection upsert and points query APIs
- [x] Library of Congress LCDB ISBN adapter over SRU (`bath.isbn`)
- [x] Library of Congress Name Authority File candidate adapter over SRU (`bath.personalName`)
- [x] isolated deployment CLI, environment configuration and offline adapter tests

## v3.1 — GitHub-only public deployment

- [x] serverless GitHub Pages build from the shared `web/` UI
- [x] browser static API shim with automatic fallback to the Python REST API
- [x] committed sourced catalog records under `data/catalog/`
- [x] deterministic static search, details, knowledge views and ISBN Universe points
- [x] browser-local text analysis without a Cyber Library server
- [x] `cyber-library-github build` static-site generator
- [x] `cyber-library-github check` repository Markdown-link validation
- [x] machine-readable `references/sources.json` and human-readable reference index
- [x] GitHub Pages workflow plus normal CI static-site artifact build
- [x] Pages-safe relative asset paths and `.nojekyll` output

## v3.2 — GitHub-native static catalog scaling

- [x] lightweight `site-data/index.json` for search/navigation
- [x] one complete JSON shard per catalog record under `site-data/records/`
- [x] lazy full-record fetching on ISBN/detail navigation
- [x] deterministic record shard filenames
- [x] `site-data/manifest.json` with byte sizes and SHA-256 digests
- [x] static build regression tests for index/shard/manifest consistency
- [x] backward-compatible browser probe for the v3.1 static catalog format

## Completion boundary

The planned repository roadmap is complete through v3.2. GitHub-only mode is the first-class public deployment path and requires no separately managed server. The repository remains the reproducible source of truth for code, sourced static records, references, build rules and tests.

Large third-party bulk datasets are intentionally not committed wholesale into Git. The v3.2 index/shard/manifest format provides a verifiable GitHub-native distribution boundary that can later be partitioned into additional Actions or Release assets without changing the canonical model.

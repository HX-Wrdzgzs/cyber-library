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

## Optional deployment adapters

These are deployment extensions rather than blockers for the completed local/portable core:

- [ ] PostgreSQL/PostGIS backend adapter
- [ ] OpenSearch backend adapter
- [ ] external object-storage publisher for static Universe artifacts
- [ ] ANN/vector-database adapter for very large embedding indexes
- [ ] additional national-library / authority-file adapters

Cyber Library intentionally does not claim that any single catalog contains every book ever created. Coverage grows by legitimate sources and identifiers while provenance remains explicit.

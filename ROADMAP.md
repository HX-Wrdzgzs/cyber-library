# Roadmap

## v1.0 — End-to-end local Cyber Library

- [x] Work / Edition / Identifier model
- [x] Open Library low-volume resolver
- [x] Open Library monthly dump importer
- [x] SQLite catalog
- [x] FTS / fallback search
- [x] subject taxonomy
- [x] provenance + evidence model
- [x] catalog/source/full-text intelligence
- [x] optional OpenAI-compatible LLM
- [x] TXT / Markdown / EPUB ingestion
- [x] optional PDF extraction
- [x] mind map
- [x] knowledge graph
- [x] clean-room ISBN Hilbert space
- [x] web explorer
- [x] REST API
- [x] Docker
- [x] Python 3.11–3.13 CI

## v1.1 — Scale and retrieval

- [x] one-command resumable Open Library dump bootstrap
- [x] resumable offline ISBN-universe index builder
- [x] precomputed spatial density tiles and progressive map rendering
- [x] optional OpenAI-compatible vector embedding backend
- [x] incremental embedding index and hybrid lexical/semantic ranking
- [ ] dedicated bulk importer benchmarks for tens of millions of editions
- [ ] PostgreSQL/PostGIS backend option
- [ ] OpenSearch backend option
- [ ] incremental Open Library refresh pipeline

## v1.2 — More identifiers / sources

- [x] configurable source adapter / registry contract
- [x] Wikidata ISBN entity reconciliation and persisted external links
- [ ] DOI / Crossref adapter for book-like scholarly works
- [ ] library authority records
- [ ] multilingual subject normalization

## v2 — Global knowledge navigation

- [ ] cross-work concept graph
- [ ] author timeline
- [ ] publisher map
- [ ] citation / influence relationships when reliable sources exist
- [ ] precomputed public static ISBN map tiles
- [ ] distributed analysis cache with reproducible source manifests

The roadmap intentionally does not claim that any single catalog can contain every
book ever created. Coverage should grow by source and identifier, not by pretending
ISBN is universal.

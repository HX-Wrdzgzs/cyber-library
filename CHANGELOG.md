# Changelog

## 1.1.1 — 2026-09-16

- Added optional OpenAI-compatible embedding client.
- Added persistent per-edition SQLite embedding index keyed by model.
- Added resumable/incremental semantic indexing CLI.
- Added semantic-only search and RRF hybrid lexical/semantic ranking.
- Added graceful lexical fallback when the embedding service is unavailable.
- Added embedding status reporting, environment template and CI coverage.

## 1.1.0 — 2026-09-16

- Added resumable Open Library bootstrap downloads and one-command catalog creation.
- Added offline scale maintenance CLI: `cyber-library-scale`.
- Added resumable, checkpointed ISBN-universe density tile generation.
- Added progressive Universe API output: density tiles at distant zooms and edition points at close/filtered zooms.
- Updated the web ISBN Universe to drill from aggregate cells into individual books.
- Integrated universe tile generation into the standard Open Library bootstrap pipeline.

## 1.0.0 — 2026-09-15

- Added evidence-aware L0/L1/L2/L3 analysis.
- Added full-text TXT, Markdown and EPUB ingestion plus optional PDF extraction.
- Added optional OpenAI-compatible LLM enhancement with deterministic fallback.
- Added subject taxonomy and top-level categories.
- Added SQLite FTS search and live Open Library search fallback.
- Added knowledge graph generation.
- Added clean-room Hilbert ISBN Universe coordinates and API.
- Added interactive web search, book intelligence view, graph and ISBN universe.
- Added Docker / Compose deployment.
- Fixed SQLite thread-safety for the threaded web server.
- Added migration-safe catalog schema and expanded tests.
- Tightened ISBN-13 validation to the 978/979 book namespace.

## 0.1.0 — 2026-09-15

- Initial catalog prototype.
- Open Library dump import.
- Work / Edition model.
- Low-volume ISBN resolution.

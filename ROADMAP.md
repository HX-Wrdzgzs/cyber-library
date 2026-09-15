# Roadmap

Cyber Library is developed in vertical slices: each milestone should remain runnable and testable.

## v0.1 — Catalog foundation

- [x] Work / Edition / Identifier separation
- [x] ISBN-10 and ISBN-13 validation / normalization
- [x] low-volume Open Library resolver
- [x] SQLite response cache
- [x] evidence-bounded L1 catalog analysis
- [x] local JSON API
- [x] minimal web explorer
- [x] CI on Python 3.11–3.13
- [x] JSON Schemas and sample record
- [x] Open Library dump importer foundation
- [x] local catalog lookup by ISBN

## v0.2 — Catalog quality

- [ ] multi-source entity reconciliation
- [ ] author identity reconciliation
- [ ] redirects / merged records
- [ ] publisher normalization
- [ ] language normalization
- [ ] field-level provenance
- [ ] cover rights / provenance metadata
- [ ] incremental dump refresh pipeline

## v0.3 — Search

- [ ] lexical search over titles / authors / subjects
- [ ] filters for language / year / publisher / subject
- [ ] semantic embeddings
- [ ] hybrid retrieval and ranking
- [ ] related-work recommendations

## v0.4 — Book Intelligence

- [ ] model-provider abstraction
- [ ] source-backed L2 analysis
- [ ] structured table-of-contents ingestion
- [ ] mind-map generation from evidence
- [ ] concept extraction
- [ ] analysis cache + versioning
- [ ] citation / provenance UI

## v0.5 — ISBN Universe

- [ ] define renderer boundary with `phiresky/isbn-visualization`
- [ ] map normalized editions to ISBN coordinates
- [ ] dataset tile generation
- [ ] highlight search result sets
- [ ] color by year / language / publisher / subject
- [ ] ISBN → Edition → Work navigation

## v0.6 — Knowledge Space

- [ ] subject hierarchy
- [ ] concept graph
- [ ] author graph
- [ ] timeline
- [ ] cross-space navigation between semantic graph and ISBN map

## v1.0 — Public explorer

A production deployment needs its own database/search/object-storage infrastructure, observability, backups, source-rights review and abuse controls. The repository intentionally does not claim that v0.x is a complete mirror of every book ever published.

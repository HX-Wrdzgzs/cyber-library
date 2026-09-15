# External Sources and Entity Reconciliation

Cyber Library keeps its canonical catalog separate from external entity systems. External sources are adapters: they can identify or enrich an entity, but they do not silently overwrite bibliographic truth.

## Source adapter contract

Adapters implement `SourceAdapter` from `cyber_library.sources.base`:

```python
class SourceAdapter(Protocol):
    name: str

    @property
    def capabilities(self) -> tuple[str, ...]: ...
    def reconcile_isbn(self, isbn: str) -> list[SourceMatch]: ...
    def health(self) -> dict: ...
```

`SourceRegistry` lets additional packages or deployments register adapters without adding source-specific conditionals to the catalog core.

## Built-in Wikidata adapter

The Wikidata adapter uses the Wikidata Query Service and reconciles ISBN-13 (`P212`) and, when an ISBN-10 was supplied, ISBN-10 (`P957`). Matches are stored as external entity links with source ID, URL, confidence and normalized identifiers.

Default endpoint:

```text
https://query.wikidata.org/sparql
```

Override with:

```bash
export CYBER_LIBRARY_WIKIDATA_SPARQL_URL='https://query.wikidata.org/sparql'
```

## Built-in Crossref adapter

The Crossref adapter queries the public REST `/works` endpoint with the exact ISBN filter. It retains DOI, title, work type, publisher, authors and issued date as a source-specific match rather than merging them into the canonical record automatically.

Default endpoint:

```text
https://api.crossref.org
```

Override with:

```bash
export CYBER_LIBRARY_CROSSREF_BASE_URL='https://api.crossref.org'
```

Set `CYBER_LIBRARY_CONTACT` so Crossref can route requests through its polite pool. Crossref recommends identifying clients and caching repeated responses; Cyber Library's source adapters use the shared SQLite JSON cache.

## CLI

List adapters:

```bash
cyber-library-source list
```

Inspect one adapter without a network request:

```bash
cyber-library-source status wikidata
cyber-library-source status crossref
```

Reconcile against one source:

```bash
cyber-library-source reconcile 9780306406157 \
  --source wikidata \
  --db .cyber-library/catalog.sqlite3
```

Run all currently registered ISBN-capable sources:

```bash
cyber-library-source reconcile-all 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

A failure from one external source is reported separately and does not discard matches returned by another source.

Read stored links without contacting any upstream service:

```bash
cyber-library-source links 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

## Persistence

External links live in an `entity_links` table rather than inside Open Library raw records. This preserves provenance and allows multiple systems to point at the same local Edition independently.

ISBN reconciliation is edition-oriented because an ISBN identifies a publication manifestation. Work-level reconciliation should use stronger authority identifiers or several corroborating fields; Cyber Library intentionally does not auto-merge Works from fuzzy title similarity alone.

## Adding another source

Implement the adapter contract, then register a factory:

```python
from cyber_library.sources.registry import registry

registry().register("example", ExampleAdapter)
```

This gives future DOI registries, authority files and national-library adapters a stable boundary without changing canonical catalog storage.

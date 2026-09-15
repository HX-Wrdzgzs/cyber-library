# External Sources and Entity Reconciliation

Cyber Library keeps its canonical catalog separate from external entity systems.
External sources are adapters: they can identify or enrich an entity, but they do
not silently overwrite bibliographic truth.

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

`SourceRegistry` lets additional packages or deployments register adapters without
adding source-specific conditionals to the catalog core.

## Built-in Wikidata adapter

The first entity-linking adapter uses the Wikidata Query Service. It reconciles
ISBN-13 (`P212`) and, when an ISBN-10 was supplied, ISBN-10 (`P957`). The result is
stored as an external entity link with source ID, URL, confidence and the raw
normalized match payload.

Wikidata's machine SPARQL endpoint is currently:

```text
https://query.wikidata.org/sparql
```

Override it when necessary:

```bash
export CYBER_LIBRARY_WIKIDATA_SPARQL_URL='https://query.wikidata.org/sparql'
```

Low-volume reconciliation should identify the application with
`CYBER_LIBRARY_CONTACT`.

## CLI

List adapters:

```bash
cyber-library-source list
```

Inspect one adapter without making a network request:

```bash
cyber-library-source status wikidata
```

Reconcile a book already present in the local catalog:

```bash
cyber-library-source reconcile 9780306406157 \
  --source wikidata \
  --db .cyber-library/catalog.sqlite3
```

Read links already stored locally:

```bash
cyber-library-source links 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

## Persistence

External links live in an `entity_links` table rather than inside the Open Library
raw record. This preserves provenance and allows multiple sources to point at the
same local Edition independently.

ISBN reconciliation is edition-oriented because an ISBN identifies a publication
manifestation. A future Work-level reconciler can use title/author/authority IDs,
but it should not merge Works from fuzzy title similarity alone.

## Adding another source

Implement the adapter contract, then register a factory:

```python
from cyber_library.sources.registry import registry

registry().register("example", ExampleAdapter)
```

The next source integrations can therefore add capabilities such as DOI resolution,
authority records or national-library identifiers without changing the storage
contract used by the rest of Cyber Library.

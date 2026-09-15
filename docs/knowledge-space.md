# Knowledge Space

Cyber Library has two separate navigation spaces:

1. **ISBN Universe** — physical publication/edition identifier space.
2. **Knowledge Space** — relationships derived from canonical catalog facts such as subjects, authors, works, editions and publishers.

Knowledge Space does not invent factual links with an LLM. The current graph/timeline views are computed from catalog data.

## Concept graph

```bash
cyber-library-knowledge concept "Machine learning" \
  --db .cyber-library/catalog.sqlite3
```

Returns matching Works plus frequently co-occurring normalized subjects.

API:

```text
GET /api/knowledge/concept?subject=Machine%20learning&limit=40
```

## Author timeline

```bash
cyber-library-knowledge author "Author Name" \
  --db .cyber-library/catalog.sqlite3
```

Works are ordered by the earliest year available from their local editions. Each item keeps edition, publisher and language context.

API:

```text
GET /api/knowledge/author?name=Author%20Name&limit=100
```

## Publisher view

```bash
cyber-library-knowledge publisher "Publisher Name" \
  --db .cyber-library/catalog.sqlite3
```

Aggregates editions, top subjects, categories, years and languages without treating a publisher name as a subject classification.

API:

```text
GET /api/knowledge/publisher?name=Publisher%20Name&limit=150
```

## Multilingual subjects

Ingestion normalizes a bounded set of high-value Chinese/Japanese aliases to stable canonical subject labels before storing Works. The original upstream record remains preserved in `raw_json`, so normalization does not destroy provenance.

The alias table is intentionally conservative. Unknown labels are preserved rather than guessed.

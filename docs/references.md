# References and Source Index

Cyber Library keeps implementation claims tied to explicit upstream documentation. This page is the human-readable companion to [`references/sources.json`](../references/sources.json).

## GitHub-native hosting

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — build and deploy a static site from GitHub Actions. Cyber Library's GitHub-only mode uses this model and does not require a separately managed server.

## Catalog and bibliographic sources

- [Open Library API documentation](https://openlibrary.org/developers/api) — low-volume, human-triggered API usage, caching and identification guidance.
- [Open Library monthly data dumps](https://openlibrary.org/developers/dumps) — bulk catalog snapshots. Bulk corpus data is intentionally not committed to the Git repository.
- [Library of Congress Z39.50/SRU](https://www.loc.gov/z3950/) — bibliographic and authority access used by the LoC source adapter.

## Identifier, entity and relationship sources

- [Wikidata Query Service help](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Wikidata_Query_Help) — entity and authority reconciliation.
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) — DOI metadata and deposited relations.
- [Crossref REST API filters](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/) — documents the `isbn` filter used by the Crossref adapter.

## Optional deployment backends

These remain optional adapters. GitHub-only mode does not require them.

- [OpenSearch Bulk API](https://docs.opensearch.org/latest/api-reference/document-apis/bulk/) — rebuildable search mirror.
- [Qdrant Upsert Points API](https://api.qdrant.tech/api-reference/points/upsert-points) — rebuildable ANN/vector mirror.

## Prior art

- [phiresky/isbn-visualization](https://github.com/phiresky/isbn-visualization) — prior-art reference for large-scale ISBN-space visualization. Cyber Library does not copy its implementation; see [`references/isbn-visualization.md`](../references/isbn-visualization.md) and [`docs/licensing.md`](licensing.md).

## Repository evidence rules

1. Bibliographic facts should carry provenance in their record or source adapter.
2. Generated interpretation must remain separate from bibliographic facts.
3. A Markdown claim about an external API or platform should link to the upstream project or official documentation where practical.
4. Local Markdown paths are validated in CI by `cyber-library-github check`.
5. The GitHub Pages build publishes [`references/sources.json`](../references/sources.json) as machine-readable `site-data/references.json`.

# References and Source Index

Cyber Library keeps implementation claims tied to explicit upstream documentation. The canonical machine-readable list is [`references/sources.json`](../references/sources.json). The root [`REFERENCES.md`](../REFERENCES.md) is generated from that JSON and checked in CI.

## Repository citation

Cyber Library itself provides [`CITATION.cff`](../CITATION.cff). GitHub recognizes this file on the default branch and exposes the repository's citation metadata through **Cite this repository**, including supported citation renderings such as APA and BibTeX.

The CFF file uses Citation File Format 1.2.0 and tracks the current Cyber Library release version.

## GitHub-native hosting

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) — build and deploy a static site from GitHub Actions.
- [GitHub citation files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) — repository citation behavior and `CITATION.cff` support.
- [Citation File Format](https://citation-file-format.github.io/) — human- and machine-readable software citation metadata.

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

## Reference maintenance

```bash
cyber-library-references check
cyber-library-references render
```

`render` deterministically generates root `REFERENCES.md` from `references/sources.json`. `check` validates required fields, unique reference IDs/URLs, HTTPS source URLs, and byte-for-byte synchronization of the generated Markdown.

CI, Pages, and GitHub-native catalog maintenance all run the reference check before accepting or publishing output.

## Evidence rules

1. Bibliographic facts should carry provenance in their record or source adapter.
2. Generated interpretation must remain separate from bibliographic facts.
3. A claim about an external API/platform should link to upstream or official documentation where practical.
4. Local Markdown paths are validated in CI by `cyber-library-github check`.
5. The static Pages build publishes the machine-readable source list as `site-data/references.json`.
6. Third-party references document provenance and interfaces; they do not change the MIT license of original Cyber Library source code.

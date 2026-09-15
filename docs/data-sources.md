# Data sources

## Open Library

Cyber Library currently treats Open Library as its primary bibliographic source.

Use cases:

- Works
- Editions
- Authors
- Subjects
- identifiers
- descriptions
- tables of contents
- covers

Official resources:

- Developer center: https://openlibrary.org/developers
- APIs: https://openlibrary.org/developers/api
- Dumps: https://openlibrary.org/developers/dumps
- Licensing: https://openlibrary.org/developers/licensing
- Covers: https://openlibrary.org/dev/docs/api/covers

### Bulk rule

Do not build a giant catalog by looping over the live APIs.

Use monthly dumps. Open Library explicitly publishes them for bulk access.

### Live rule

Live endpoints are used only for low-volume, human-triggered resolution/search.
Cyber Library sends an identifying User-Agent and supports a contact header.

### Covers

The web UI links to Open Library cover URLs rather than bulk-crawling the Covers
API. Large cover mirrors should use the bulk resources Open Library documents.

## Future sources

The data model can add:

- Wikidata
- authority files
- DOI/Crossref data for book-like scholarly publications
- publisher feeds
- national-library catalogs

Each adapter must retain provenance and source-specific rights/terms.

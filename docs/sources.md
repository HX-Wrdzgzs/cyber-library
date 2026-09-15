# External Sources and Entity Reconciliation

Cyber Library keeps its canonical catalog separate from external entity systems. External adapters may identify or enrich an entity, but they do not silently overwrite bibliographic truth.

## Source adapter contract

The required protocol remains intentionally small: source name, capabilities, ISBN reconciliation and health. Concrete adapters may advertise additional optional capabilities such as authority lookup or citation relations. This lets deployments add source-specific features without putting source conditionals into the catalog core.

## Wikidata

The built-in Wikidata adapter reconciles ISBN-13 (`P212`) and ISBN-10 (`P957`) through the Wikidata Query Service.

It also supports **author authority candidates** by exact label. Candidate results can include:

- ISNI (`P213`)
- VIAF (`P214`)
- Library of Congress Authorities ID (`P244`)
- GND ID (`P227`)

Authority results are candidates only. They carry `auto_merge: false`; Cyber Library does not attach a same-name person to a local Author automatically.

```bash
cyber-library-source authority "Author Name" \
  --source wikidata
```

Default endpoint:

```text
https://query.wikidata.org/sparql
```

Override with `CYBER_LIBRARY_WIKIDATA_SPARQL_URL`.

## Crossref

The Crossref adapter uses the public REST API and exact `filter=isbn:` matching to link eligible book-like records to deposited DOIs. Source metadata remains an external link rather than silently replacing the canonical record.

It can also retrieve the metadata for one DOI and expose **deposited citation/relation evidence**:

```bash
cyber-library-source citations 10.xxxx/example \
  --source crossref
```

The returned graph contains DOI references that are actually present in the Crossref deposit, deposited relation objects, and Crossref's `is-referenced-by-count` signal. It does not recursively crawl every referenced work and does not invent missing influence edges.

Default endpoint:

```text
https://api.crossref.org
```

Override with `CYBER_LIBRARY_CROSSREF_BASE_URL`. Set `CYBER_LIBRARY_CONTACT` so requests can identify the client; the shared JSON cache avoids unnecessary repeated requests.

## General CLI

```bash
cyber-library-source list
cyber-library-source status wikidata
cyber-library-source status crossref
```

ISBN reconciliation against one source:

```bash
cyber-library-source reconcile 9780306406157 \
  --source wikidata \
  --db .cyber-library/catalog.sqlite3
```

Run all ISBN-capable sources independently:

```bash
cyber-library-source reconcile-all 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

A failure from one upstream is reported separately and does not discard another source's successful matches.

Read persisted ISBN/entity links without network access:

```bash
cyber-library-source links 9780306406157 \
  --db .cyber-library/catalog.sqlite3
```

## Persistence and merge policy

External ISBN links live in `entity_links`, preserving source, external ID, URL, confidence and source-specific metadata. ISBN reconciliation is edition-oriented because ISBN identifies a publication manifestation.

Authority-name matching is deliberately not persisted as an automatic Author merge because names are not unique identifiers. A future curator/UI may choose a candidate after inspecting its authority identifiers.

Likewise, Crossref citation edges remain source-labelled evidence. A citation count is not treated as a universal measure of importance, and absent Crossref references are not interpreted as evidence that no relationship exists.

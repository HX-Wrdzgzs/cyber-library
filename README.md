# Cyber Library

> Explore humanity's published knowledge — directly from GitHub.

Cyber Library is an open, evidence-aware map of books and published knowledge. It separates Work, Edition, identifiers, provenance and generated interpretation. The default public deployment is **GitHub-only**: repository + GitHub Actions + GitHub Pages. No separately managed server is required.

## GitHub-only quick start

Everything needed for the public project lives in this repository.

```bash
python -m pip install -e .
cyber-library-catalog validate
cyber-library-github check
cyber-library-github build --out _site
```

One-time Pages setup remains inside GitHub:

1. Repository **Settings → Pages**.
2. **Build and deployment → Source → GitHub Actions**.
3. **Actions → GitHub Pages → Run workflow**.

The deployment workflow is [`.github/workflows/pages.yml`](.github/workflows/pages.yml). See [`docs/github-only.md`](docs/github-only.md).

## Add books without leaving GitHub

Routine catalog maintenance does not require a local checkout or a server.

Open **Actions → Add ISBN to Catalog → Run workflow**, enter an ISBN, and GitHub Actions will:

1. validate and normalize the ISBN;
2. resolve the Edition / Work through the existing rate-safe Open Library client;
3. generate a metadata-only L0 record with explicit provenance;
4. validate the complete sourced catalog, Markdown links and browser JavaScript;
5. build and upload a validated GitHub-only site artifact;
6. direct-commit the new JSON record to `main`.

The workflow is [`.github/workflows/catalog.yml`](.github/workflows/catalog.yml). The same operation is exposed as:

```bash
cyber-library-catalog add-isbn 9780141439518 --contact you@example.com
cyber-library-catalog validate
```

Existing ISBN records are not overwritten unless overwrite is explicitly requested. See [`docs/github-only.md`](docs/github-only.md).

## GitHub static data model

The Pages build avoids one ever-growing full-record JSON file:

```text
site-data/
  index.json             lightweight search/navigation index
  records/
    <hash>.json          one complete book record per file
  references.json        upstream/reference index
  project.json           project/build metadata
  manifest.json          file sizes + SHA-256 integrity digests
```

Search, Knowledge Space and ISBN Universe load only `index.json`. Opening a book lazily fetches its full record shard. The manifest gives every generated data file an integrity digest for GitHub Actions / Release distribution.

## What GitHub Pages mode supports

- committed catalog search;
- ISBN resolution for committed records;
- Work / Edition details and provenance;
- Knowledge Space concept / author / publisher views;
- ISBN Universe points for committed ISBN records;
- browser-local deterministic text analysis — pasted text is not uploaded to a Cyber Library server;
- machine-readable source/reference index;
- GitHub-native ISBN catalog ingestion and validation;
- the same shared UI used by the optional Python REST API.

Static source records live under [`data/catalog/`](data/catalog/). [`data/catalog/pride-and-prejudice.json`](data/catalog/pride-and-prejudice.json) is a sourced real-ISBN example; [`data/samples/book.sample.json`](data/samples/book.sample.json) is a synthetic model example.

## Evidence and references

Generated interpretation is not bibliographic fact. Metadata, authority candidates, external identifiers and generated interpretation remain separate.

- Human-readable source index: [`docs/references.md`](docs/references.md)
- Machine-readable source index: [`references/sources.json`](references/sources.json)
- Licensing and data-rights notes: [`docs/licensing.md`](docs/licensing.md)
- ISBN visualization prior-art note: [`references/isbn-visualization.md`](references/isbn-visualization.md)

`cyber-library-github check` validates repository-local Markdown links; `cyber-library-catalog validate` enforces sourced-catalog requirements.

## GitHub Actions artifacts

Normal CI validates Python 3.11–3.13, JavaScript syntax, catalog records, Markdown links and the complete GitHub-only build. The Python 3.13 job uploads `_site` as `cyber-library-github-site`, so a deployable build exists entirely in GitHub before Pages is enabled.

The Add ISBN workflow also builds and uploads a validated site artifact before it commits catalog changes. This is deliberate because GitHub prevents pushes made with the workflow `GITHUB_TOKEN` from recursively starting another push workflow.

## Large catalog boundary

Open Library's public API is for low-volume human-facing lookups; bulk users are directed to monthly dumps. Those dumps are too large for an ordinary Git repository and are intentionally not committed wholesale.

Cyber Library keeps the reproducible catalog model, importer, references, bounded sourced records and generated static format in GitHub. Larger generated catalogs can use further index/record sharding plus GitHub Release/Actions assets rather than a separately managed backend.

See [`docs/data-sources.md`](docs/data-sources.md) and [`docs/github-only.md`](docs/github-only.md).

## Optional local full catalog

The GitHub-only path is the default public deployment, but the portable local catalog remains available for bulk data:

```bash
cyber-library bootstrap-openlibrary
cyber-library serve --db .cyber-library/catalog.sqlite3
```

The shared browser UI automatically falls back to the real `/api/*` endpoints when generated Pages data is absent.

## Search and knowledge navigation

```bash
cyber-library search "machine learning" --db .cyber-library/catalog.sqlite3 --no-live
cyber-library-semantic index --db .cyber-library/catalog.sqlite3
cyber-library-knowledge concept "Machine learning" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge author "Author Name" --db .cyber-library/catalog.sqlite3
cyber-library-knowledge publisher "Publisher Name" --db .cyber-library/catalog.sqlite3
```

See [`docs/semantic.md`](docs/semantic.md) and [`docs/knowledge-space.md`](docs/knowledge-space.md).

## External sources

```bash
cyber-library-source list
cyber-library-source reconcile-all 9780306406157 --db .cyber-library/catalog.sqlite3
cyber-library-source authority "Author Name" --source wikidata
cyber-library-source authority "Author Name" --source loc
cyber-library-source citations 10.xxxx/example --source crossref
```

Built-in adapters cover Open Library, Wikidata, Crossref and Library of Congress with explicit provenance and ambiguity-safe authority handling. See [`docs/sources.md`](docs/sources.md).

## ISBN Universe

```bash
cyber-library space 9780306406157
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
cyber-library-export universe --db .cyber-library/catalog.sqlite3 --out public-universe
```

The mapping is an independent Cyber Library Hilbert implementation; no `phiresky/isbn-visualization` implementation is copied. See [`docs/universe.md`](docs/universe.md).

## Book intelligence

```text
L0  bibliographic metadata only
L1  catalog-derived interpretation
L2  source-backed structured material
L3  lawful full-text analysis
```

Local file analysis supports TXT / Markdown / EPUB and optional PDF when the user has rights to process the content. GitHub Pages mode uses deterministic browser-local text analysis. See [`docs/book-intelligence.md`](docs/book-intelligence.md).

## Optional deployment adapters

PostgreSQL/PostGIS, OpenSearch, Qdrant and S3-compatible adapters remain available but are **not required** by GitHub-only public deployment.

```bash
cyber-library-deploy status
```

See [`docs/deployment-adapters.md`](docs/deployment-adapters.md).

## Install

```bash
pip install -e .
pip install -e '.[pdf]'
pip install -e '.[postgres]'
pip install -e '.[s3]'
pip install -e '.[deploy]'
```

## Repository layout

```text
.github/workflows/      CI, catalog maintenance and GitHub Pages workflows
data/catalog/           sourced records included in GitHub builds
data/samples/           synthetic schema examples
docs/                   architecture, operation and source references
references/             machine-readable sources and prior-art notes
src/cyber_library/      catalog, analysis, source and GitHub build/ingest code
tests/                  deterministic unit/regression tests
web/                    shared browser explorer and GitHub static API shim
```

## Project status

The planned repository roadmap is complete through **v3.3.0**. GitHub-only mode now covers both serving and routine ISBN catalog maintenance: source resolution, validation, static build, artifact generation and direct catalog commit all execute inside GitHub.

See [`ROADMAP.md`](ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md).

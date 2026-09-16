# Cyber Library

> Explore humanity's published knowledge — directly from GitHub.

Cyber Library is an open, evidence-aware map of books and published knowledge. It separates Work, Edition, identifiers, provenance and generated interpretation. The default public deployment is **GitHub-only**: repository + GitHub Actions + GitHub Pages. No separately managed server is required.

## GitHub-only quick start

```bash
python -m pip install -e .
cyber-library-github check
cyber-library-github build --out _site
```

One-time Pages setup remains inside GitHub:

1. Repository **Settings → Pages**.
2. **Build and deployment → Source → GitHub Actions**.
3. **Actions → GitHub Pages → Run workflow**.

The deployment workflow is [`.github/workflows/pages.yml`](.github/workflows/pages.yml). See [`docs/github-only.md`](docs/github-only.md).

## v3.2 GitHub static data model

The Pages build does not put every full book object into one giant JSON file. It emits:

```text
site-data/
  index.json             lightweight search/navigation index
  records/
    <hash>.json          one complete book record per file
  references.json        upstream/reference index
  project.json           project/build metadata
  manifest.json          file sizes + SHA-256 integrity digests
```

Search, Knowledge Space and ISBN Universe load only `index.json`. Opening a specific book lazily fetches its full record shard. This keeps the browser startup bounded as committed catalog coverage grows.

The SHA-256 manifest also gives later GitHub Actions / Release asset workflows a verifiable static format without requiring a Cyber Library backend service.

## What GitHub Pages mode supports

- committed catalog search
- ISBN resolution for committed records
- Work / Edition details and provenance
- Knowledge Space concept / author / publisher views
- ISBN Universe points for committed ISBN records
- browser-local deterministic text analysis; pasted text is not uploaded to a Cyber Library server
- machine-readable source/reference index
- one shared UI that automatically falls back to the optional Python REST API when static data is absent

Static source records live under [`data/catalog/`](data/catalog/). [`data/catalog/pride-and-prejudice.json`](data/catalog/pride-and-prejudice.json) is a sourced real-ISBN example; [`data/samples/book.sample.json`](data/samples/book.sample.json) remains a synthetic model example.

## Evidence and references

Cyber Library does not treat generated text as bibliographic fact. Metadata, authority candidates, external identifiers and generated interpretation are kept in separate evidence/provenance layers.

- Human-readable source index: [`docs/references.md`](docs/references.md)
- Machine-readable source index: [`references/sources.json`](references/sources.json)
- Licensing and data-rights notes: [`docs/licensing.md`](docs/licensing.md)
- ISBN visualization prior-art note: [`references/isbn-visualization.md`](references/isbn-visualization.md)

`cyber-library-github check` validates repository-local Markdown links in CI.

## GitHub Actions artifacts

The normal CI validates Python 3.11–3.13, JavaScript syntax, repository Markdown links and the complete GitHub-only build. The Python 3.13 job uploads `_site` as the `cyber-library-github-site` Actions artifact, so a deployable static build exists entirely within GitHub even before Pages is switched on.

## Large catalog boundary

Open Library's public API is for low-volume human-facing lookups; bulk users are directed to monthly dumps. Those dumps are too large for an ordinary Git repository and are intentionally not committed wholesale.

Cyber Library keeps the reproducible catalog model, importer, source references, build rules, bounded committed records and generated static format in GitHub. Larger generated catalogs can use the same index/record/manifest model with additional sharding and GitHub Release/Actions assets rather than a separately managed server.

See [`docs/data-sources.md`](docs/data-sources.md) and [`docs/github-only.md`](docs/github-only.md).

## Optional local full catalog

GitHub-only is the default public path, but the original portable local catalog remains useful for bulk data on a machine someone controls:

```bash
cyber-library bootstrap-openlibrary
cyber-library serve --db .cyber-library/catalog.sqlite3
```

The shared browser UI automatically uses the real `/api/*` endpoints when generated Pages data is absent.

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
.github/workflows/      CI and GitHub Pages workflows
data/catalog/           sourced records included in GitHub builds
data/samples/           synthetic schema examples
docs/                   architecture, operation and source references
references/             machine-readable sources and prior-art notes
src/cyber_library/      catalog, analysis, source, build and deployment code
tests/                  deterministic unit/regression tests
web/                    shared browser explorer and GitHub static API shim
```

## Project status

The planned repository roadmap is complete through **v3.2.0**. GitHub-only mode now has a lazy static catalog format, independently addressable record shards and an integrity manifest in addition to the Pages runtime and Actions artifact build.

See [`ROADMAP.md`](ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md).

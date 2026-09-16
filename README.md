# Cyber Library

> Explore humanity's published knowledge — directly from GitHub.

Cyber Library is an open, evidence-aware map of books and published knowledge. It separates Work, Edition, identifiers, provenance and generated interpretation, and it can now run publicly with **GitHub only**: repository + GitHub Actions + GitHub Pages. No VPS, database server, reverse proxy or always-on process is required for the public static mode.

## GitHub-only quick start

The repository contains a serverless site builder and a Pages workflow.

```bash
python -m pip install -e .
cyber-library-github check
cyber-library-github build --out _site
```

For public hosting, perform the one-time GitHub setting:

1. Repository **Settings → Pages**.
2. **Build and deployment → Source → GitHub Actions**.
3. **Actions → GitHub Pages → Run workflow**.

The workflow lives at [`.github/workflows/pages.yml`](.github/workflows/pages.yml). The resulting site is built entirely from this repository. See [`docs/github-only.md`](docs/github-only.md).

## What GitHub Pages mode supports

- committed catalog search
- ISBN resolution for committed records
- Work / Edition details and provenance
- Knowledge Space concept / author / publisher views
- ISBN Universe points for committed ISBN records
- browser-local deterministic text analysis; user text is not uploaded by the static mode
- machine-readable source/reference index
- the same shared `web/` interface used by the optional local Python API

Static catalog records live under [`data/catalog/`](data/catalog/). A build generates `site-data/catalog.json`, `site-data/references.json` and `site-data/project.json` inside the Pages artifact.

## Evidence and references

Cyber Library does not treat generated text as bibliographic fact. Metadata, external links, authority candidates and analysis evidence remain separate.

- Human-readable source index: [`docs/references.md`](docs/references.md)
- Machine-readable source index: [`references/sources.json`](references/sources.json)
- Licensing and data-rights notes: [`docs/licensing.md`](docs/licensing.md)
- ISBN visualization prior-art note: [`references/isbn-visualization.md`](references/isbn-visualization.md)

`cyber-library-github check` validates repository-local Markdown links in CI.

## Add a book to the GitHub catalog

Add a sourced JSON record under `data/catalog/` using the normal Cyber Library shape:

```text
Work
  └─ Edition
       ├─ identifiers
       ├─ provenance
       └─ evidence / analysis (only when supported)
```

Do not commit copyrighted full text merely to make the static site richer. Metadata-only records should remain L0/L1 unless lawful source-backed material exists.

The repository includes [`data/catalog/pride-and-prejudice.json`](data/catalog/pride-and-prejudice.json) as a real sourced ISBN example and [`data/samples/book.sample.json`](data/samples/book.sample.json) as a synthetic schema demonstration.

## GitHub Actions artifacts

The normal CI validates Python 3.11–3.13, JavaScript syntax, Markdown links and the GitHub-only site builder. The Python 3.13 job also builds `_site` and uploads it as a GitHub Actions artifact, so even before Pages is enabled the complete static site remains inside GitHub.

## Large catalog boundary

Open Library's public API is intended for low-volume human-facing lookup; bulk users are directed to monthly data dumps. Those dumps are too large for a normal Git repository and should not be committed wholesale.

Cyber Library therefore keeps the **reproducible catalog model, importer, provenance rules, static-site generator and bounded committed records in GitHub**. Large generated catalogs can later be sharded into GitHub-managed artifacts/releases without introducing a separately managed server.

See [`docs/data-sources.md`](docs/data-sources.md) and [`docs/github-only.md`](docs/github-only.md).

## Full local catalog remains available

GitHub-only is now the default public deployment path, but the original local/portable core remains available when you want a large catalog on a machine you control:

```bash
cyber-library bootstrap-openlibrary
cyber-library serve --db .cyber-library/catalog.sqlite3
```

The shared front end automatically falls back to the real `/api/*` endpoints when `site-data/catalog.json` is absent.

## Search and knowledge navigation

Local lexical / semantic search:

```bash
cyber-library search "machine learning" --db .cyber-library/catalog.sqlite3 --no-live
cyber-library-semantic index --db .cyber-library/catalog.sqlite3
```

Knowledge Space:

```bash
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

Built-in sources include Open Library, Wikidata, Crossref and Library of Congress adapters with explicit provenance and ambiguity-safe authority behavior. See [`docs/sources.md`](docs/sources.md).

## ISBN Universe

```bash
cyber-library space 9780306406157
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
cyber-library-export universe --db .cyber-library/catalog.sqlite3 --out public-universe
```

The mapping is an independent Cyber Library Hilbert implementation. No `phiresky/isbn-visualization` implementation is copied. See [`docs/universe.md`](docs/universe.md).

## Book intelligence

```text
L0  bibliographic metadata only
L1  catalog-derived interpretation
L2  source-backed structured material
L3  lawful full-text analysis
```

Local file analysis remains available for TXT / Markdown / EPUB and optional PDF when the user has rights to process the content. GitHub Pages mode uses a deterministic browser-local text analyzer and does not send pasted text to a Cyber Library server.

See [`docs/book-intelligence.md`](docs/book-intelligence.md).

## Optional deployment adapters

v3 added PostgreSQL/PostGIS, OpenSearch, Qdrant and S3-compatible adapters. They are **not required** by the GitHub-only public mode.

```bash
cyber-library-deploy status
```

See [`docs/deployment-adapters.md`](docs/deployment-adapters.md).

## Install

Core:

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e '.[pdf]'
pip install -e '.[postgres]'
pip install -e '.[s3]'
pip install -e '.[deploy]'
```

## Repository layout

```text
.github/workflows/      CI and GitHub Pages workflows
data/catalog/           sourced records published by GitHub-only builds
data/samples/           synthetic schema examples
docs/                   architecture, operation and references
references/             machine-readable sources and prior-art notes
src/cyber_library/      catalog, analysis, source, build and deployment code
tests/                  deterministic unit/regression tests
web/                    shared browser explorer + GitHub static API shim
```

## Project status

The planned repository roadmap is complete through **v3.1.0**. v3.1 makes GitHub-only operation the first-class public deployment: static catalog, browser-local functionality, Pages workflow, Actions artifact build, machine-readable references and Markdown-link validation all live in this repository.

See [`ROADMAP.md`](ROADMAP.md) and [`CHANGELOG.md`](CHANGELOG.md).

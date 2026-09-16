# GitHub-only Mode

Cyber Library can run publicly without a separately managed server. The public deployment is GitHub repository + GitHub Actions + GitHub Pages.

```text
main branch
  ├─ data/catalog/*.json        sourced records committed to Git
  ├─ references/sources.json    machine-readable source index
  ├─ web/                       shared browser UI
  ├─ cyber-library-github       builder / Markdown checker
  └─ GitHub Actions
        └─ Pages / Actions artifact
             └─ static browser application
```

## Static data layout

v3.2 avoids one ever-growing full-record `catalog.json`. A build produces a small search/navigation index and lazy-loaded record shards:

```text
_site/site-data/
  index.json                    lightweight Work / Edition search fields
  records/
    <content-key>.json          one complete record per file
  references.json               machine-readable upstream reference index
  project.json                  project/build metadata
  manifest.json                 bytes + SHA-256 for every generated data file
```

The browser loads `index.json` first. Searching, Knowledge Space and ISBN Universe use only this lightweight index. Opening a specific ISBN lazily fetches the corresponding `records/<hash>.json`, so provenance, evidence and analysis are not downloaded for every book at page load.

`manifest.json` is reproducible build metadata. It contains the relative path, byte size and SHA-256 digest for every generated data file. It is intended for integrity checks and later GitHub Release/Actions distribution workflows.

## What works without a server

- committed catalog search
- ISBN resolution for committed records
- Work / Edition detail views
- provenance and evidence display
- Knowledge Space views derived from committed facts
- ISBN Universe points for committed ISBN records
- deterministic browser-local text analysis
- source/reference index

The same `web/` UI remains compatible with the Python REST server. `web/github.js` only intercepts `/api/*` when generated static data exists; otherwise it falls back to the real network API.

## Build and validate inside GitHub

```bash
cyber-library-github check
cyber-library-github build --out _site
```

`check` validates repository-local Markdown links. `build` copies the shared UI and creates the static data layout above plus `.nojekyll` and `404.html`.

The normal CI builds `_site` under Python 3.13 and uploads the result as the `cyber-library-github-site` GitHub Actions artifact. This means the complete deployable output remains inside GitHub even before Pages is enabled.

## Publish with GitHub Pages

The repository contains [`.github/workflows/pages.yml`](../.github/workflows/pages.yml). GitHub requires Pages to be enabled for the repository before the official Pages deployment actions can publish using the normal workflow token.

One-time GitHub UI action:

1. Open repository **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions**.
3. Open **Actions → GitHub Pages → Run workflow**.

No VPS, external database, reverse proxy or long-running application process is required for this public mode.

## Add books

Add one sourced JSON record under `data/catalog/` using the normal Cyber Library Work / Edition / Analysis / Provenance shape. Bibliographic facts and provenance should be explicit; copyrighted full text should not be committed merely to make static analysis richer.

The next Actions/Pages build automatically emits one lightweight index entry and one independently addressable full-record shard. ISBN records also receive deterministic Cyber Library Hilbert coordinates at build time.

## Large corpus boundary

Open Library provides monthly bulk dumps that are far larger than an ordinary Git repository should contain. GitHub-only mode therefore keeps code, references, sourced records, rebuild rules and bounded static indexes in Git.

For substantially larger generated catalogs, the same `index + records + manifest` format can be partitioned further and distributed as GitHub Release assets or Actions artifacts. That scaling path still does not require a separately managed Cyber Library server.

See also [`references.md`](references.md), [`data-sources.md`](data-sources.md), and [`../ROADMAP.md`](../ROADMAP.md).

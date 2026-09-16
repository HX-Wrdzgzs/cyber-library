# GitHub-only Mode

Cyber Library can run publicly without a separately managed server. The GitHub-only deployment is composed of:

```text
main branch
  ├─ data/catalog/*.json        committed sourced records
  ├─ references/sources.json    machine-readable source index
  ├─ web/                       shared browser UI
  ├─ cyber-library-github       static site builder / Markdown checker
  └─ GitHub Actions
        └─ GitHub Pages artifact
             └─ static browser application
```

## What works without a server

- committed catalog search
- ISBN resolution for committed records
- Work / Edition detail pages
- provenance and evidence display
- Knowledge Space views derived from committed facts
- ISBN Universe points for committed ISBN records
- browser-local deterministic text analysis
- source/reference index

The same `web/` UI remains compatible with the Python REST server. `web/github.js` intercepts `/api/*` only when the static catalog is available, so the project does not maintain two separate interfaces.

## Build locally or in Actions

```bash
cyber-library-github check
cyber-library-github build --out _site
```

`check` validates repository-local Markdown links. `build` copies the shared web application and generates:

```text
_site/
  index.html
  404.html
  .nojekyll
  site-data/
    catalog.json
    project.json
    references.json
```

## Publish with GitHub Pages

The repository contains [`.github/workflows/pages.yml`](../.github/workflows/pages.yml). GitHub requires Pages to be enabled for the repository before the official Pages actions can deploy with the normal `GITHUB_TOKEN`.

One-time GitHub UI action:

1. Open repository **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions**.
3. Open **Actions → GitHub Pages → Run workflow**.

No VPS, database server, reverse proxy or long-running process is required for this public mode. The Pages workflow builds from the repository and deploys inside GitHub.

## Add books to the GitHub catalog

Add one JSON record under `data/catalog/` using the normal Cyber Library Work / Edition / Analysis / Provenance shape. At minimum, keep bibliographic metadata and provenance explicit. Do not add copyrighted full text merely to make static analysis richer.

The next Pages build automatically folds committed records into `site-data/catalog.json`. ISBN records also receive deterministic Cyber Library Hilbert coordinates at build time.

## Large corpus boundary

Open Library explicitly provides monthly dumps for bulk use; these can be many gigabytes and do not belong in an ordinary Git repository. GitHub-only mode therefore treats the repository as the reproducible source/configuration layer and publishes bounded static catalog data suitable for Pages.

For larger GitHub-hosted datasets, shard generated static JSON and publish them as GitHub-managed artifacts/releases rather than adding a separately managed server. The canonical source and rebuild rules remain in this repository.

See also [`references.md`](references.md), [`data-sources.md`](data-sources.md), and [`../ROADMAP.md`](../ROADMAP.md).

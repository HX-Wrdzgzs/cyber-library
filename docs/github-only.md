# GitHub-only Mode

Cyber Library can run publicly without a separately managed server. The public deployment is GitHub repository + GitHub Actions + GitHub Pages.

```text
main branch
  ├─ data/catalog/*.json        sourced records committed to Git
  ├─ references/sources.json    machine-readable source index
  ├─ web/                       shared browser UI
  ├─ cyber-library-github       static builder / Markdown checker
  ├─ cyber-library-catalog      sourced catalog maintenance
  └─ GitHub Actions
        ├─ CI
        ├─ Add ISBN to Catalog
        └─ GitHub Pages
```

## Static data layout

A build produces a lightweight index and lazy-loaded record shards:

```text
_site/site-data/
  index.json                    lightweight Work / Edition search fields
  records/
    <content-key>.json          one complete record per file
  references.json               machine-readable upstream reference index
  project.json                  project/build metadata
  manifest.json                 bytes + SHA-256 for every generated data file
```

The browser loads `index.json` first. Searching, Knowledge Space and ISBN Universe use only the lightweight index. Opening a specific ISBN lazily fetches its `records/<hash>.json` shard.

`manifest.json` contains the relative path, byte size and SHA-256 digest of every generated data file.

## Add an ISBN entirely inside GitHub

The repository includes [`.github/workflows/catalog.yml`](../.github/workflows/catalog.yml). No local checkout is required for routine catalog additions.

1. Open **Actions → Add ISBN to Catalog**.
2. Choose **Run workflow**.
3. Enter an ISBN-10 or ISBN-13.
4. Optionally provide a contact email so the Open Library request is identified.
5. Use `overwrite` only when intentionally refreshing an existing committed record.

The workflow:

```text
workflow_dispatch input
  → normalize / validate ISBN
  → resolve through the rate-safe Open Library client
  → generate L0 Work / Edition / provenance JSON
  → validate every data/catalog record
  → validate Markdown links and browser JavaScript
  → build the complete GitHub-only site
  → upload a validated GitHub Actions site artifact
  → direct commit of data/catalog change to main
```

Workflow inputs are passed through environment variables rather than interpolated directly into shell commands.

GitHub intentionally prevents a push performed with the workflow `GITHUB_TOKEN` from recursively starting another push workflow. For that reason the catalog workflow performs its own validation and static-site build before committing instead of relying on a later CI run.

The command used by the workflow is also available from any checkout:

```bash
cyber-library-catalog add-isbn 9780141439518 --contact you@example.com
cyber-library-catalog validate
```

Repeated additions are idempotent by default. An ISBN already present under `data/catalog/` is left unchanged unless `--overwrite` is explicitly supplied.

## Catalog validation policy

Every JSON file under `data/catalog/` must have:

- a Work object;
- an Edition with an ID;
- at least one checksum-valid ISBN-10 or ISBN-13;
- non-empty provenance with a named source;
- a structurally valid Analysis object when analysis is present.

Synthetic schema examples belong under `data/samples/` and are not held to the sourced-catalog ISBN rule.

## What works without a server

- committed catalog search
- ISBN resolution for committed records
- Work / Edition detail views
- provenance and evidence display
- Knowledge Space views derived from committed facts
- ISBN Universe points for committed ISBN records
- deterministic browser-local text analysis
- source/reference index
- GitHub-native catalog maintenance through Actions

The same `web/` UI remains compatible with the Python REST server. `web/github.js` only intercepts `/api/*` when generated static data exists; otherwise it falls back to the real network API.

## Build and validate inside GitHub

```bash
cyber-library-catalog validate
cyber-library-github check
cyber-library-github build --out _site
```

The normal CI builds `_site` under Python 3.13 and uploads the result as the `cyber-library-github-site` GitHub Actions artifact.

## Publish with GitHub Pages

The repository contains [`.github/workflows/pages.yml`](../.github/workflows/pages.yml). GitHub requires Pages to be enabled for the repository before the official Pages deployment actions can publish using the normal workflow token.

One-time GitHub UI action:

1. Open repository **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions**.
3. Open **Actions → GitHub Pages → Run workflow**.

No VPS, external database, reverse proxy or long-running application process is required for this public mode.

## Large corpus boundary

Open Library provides monthly bulk dumps that are far larger than an ordinary Git repository should contain. GitHub-only mode therefore keeps code, references, sourced records, rebuild rules and bounded static indexes in Git.

For substantially larger generated catalogs, the same `index + records + manifest` format can be partitioned further and distributed as GitHub Release assets or Actions artifacts without introducing a separately managed Cyber Library server.

See also [`references.md`](references.md), [`data-sources.md`](data-sources.md), and [`../ROADMAP.md`](../ROADMAP.md).

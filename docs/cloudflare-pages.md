# Cloudflare Pages deployment

Cyber Library can run as a static, serverless site on Cloudflare Pages while GitHub remains the canonical source repository and catalog-maintenance surface.

```text
GitHub main
   │
   ├── data/catalog/ + references/ + web/
   │
   ▼
Cloudflare Pages Git integration
   │
   ├── validate catalog
   ├── validate references / Markdown
   └── cyber-library-github build --out _site
   │
   ▼
*.pages.dev / custom domain
```

No separately managed VPS, database server, API server, object store or runtime process is required for the public static deployment.

## Recommended Pages project settings

In the Cloudflare dashboard open **Workers & Pages → Create application → Pages → Connect to Git** and authorize the GitHub repository `HX-Wrdzgzs/cyber-library`.

Use these build settings:

| Setting | Value |
| --- | --- |
| Framework preset | None |
| Production branch | `main` |
| Root directory | `/` |
| Build command | `python -m pip install -e . && cyber-library-catalog validate && cyber-library-references check && cyber-library-github check && cyber-library-github build --out _site` |
| Build output directory | `_site` |

Recommended build environment variables:

| Variable | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.13.3` |
| `SKIP_DEPENDENCY_INSTALL` | `1` |

The project has no required deployment secret for the static site. Cloudflare receives the repository through its GitHub App and runs the build in the Pages build environment.

## What happens after setup

Every push to `main` rebuilds the production deployment. Other enabled branches can receive preview deployments without replacing production.

The build creates the same static output already validated by GitHub CI:

```text
_site/
  index.html
  404.html
  app.js
  github.js
  knowledge.js
  styles.css
  _headers
  site-data/
    index.json
    project.json
    references.json
    manifest.json
    records/*.json
```

`web/_headers` is copied into the output automatically and lets Cloudflare Pages apply the repository-defined security/cache headers to static responses.

## Custom domain

After the first successful deployment, open the Pages project and use **Custom domains → Set up a domain**. If the domain is already managed by Cloudflare, DNS can be created automatically. For external DNS, associate the custom domain in the Pages project first and then point the requested subdomain to the project's `*.pages.dev` hostname as documented by Cloudflare.

Do not create only a raw CNAME without associating the custom domain in the Pages project first; Cloudflare documents that this can fail to resolve correctly.

## Repository data model on Pages

Cloudflare Pages serves only generated static artifacts. The source-of-truth records stay in GitHub:

- `data/catalog/*.json` — committed sourced book records;
- `references/sources.json` — machine-readable upstream source registry;
- `REFERENCES.md` — generated human-readable reference index;
- `CITATION.cff` — repository citation metadata;
- `web/` — shared browser application;
- GitHub Actions — validation and ISBN maintenance.

The browser uses `site-data/index.json` for lightweight search/navigation and lazily fetches per-record JSON shards for detail views. No dynamic backend is required.

## GitHub Pages fallback

The existing GitHub Pages workflow remains in the repository as a backup deployment path. Cloudflare Pages and GitHub Pages consume the same `_site` build and therefore do not require two separate front-end implementations.

## Upstream documentation

- [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/)
- [Cloudflare Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/)
- [Cloudflare Pages build image](https://developers.cloudflare.com/pages/configuration/build-image/)
- [Cloudflare Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/)
- [Cloudflare Pages custom headers](https://developers.cloudflare.com/pages/configuration/headers/)

These upstream references are also registered in [`../references/sources.json`](../references/sources.json) and rendered into [`../REFERENCES.md`](../REFERENCES.md).

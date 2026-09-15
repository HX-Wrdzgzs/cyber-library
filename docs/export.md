# Portable exports

Cyber Library can export two deployment artifacts without coupling consumers to a live SQLite database.

## Static ISBN Universe

```bash
cyber-library-export universe \
  --db .cyber-library/catalog.sqlite3 \
  --out public-universe
```

The output contains `z0.json` … `z8.json` plus `manifest.json`. Each zoom file contains precomputed density cells, and the manifest records SHA-256 digests. The directory can be served from ordinary static hosting/CDN infrastructure.

## Analysis bundle

```bash
cyber-library-export analyses \
  --db .cyber-library/catalog.sqlite3 \
  --out analysis-bundle
```

The bundle contains deterministic, key-sorted `analyses.jsonl` plus a manifest with format version, SHA-256, record count and the union of analysis source references.

Import on another node:

```bash
cyber-library-export import-analyses analysis-bundle \
  --db .cyber-library/catalog.sqlite3
```

Import refuses a bundle whose data digest does not match the manifest. This is a portable cache/interchange mechanism, not a trust signature: SHA-256 verifies integrity, not authorship.

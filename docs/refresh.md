# Incremental Open Library refresh

Cyber Library uses the official Open Library monthly dumps as the bulk/catalog baseline. The RecentChanges API is used only to keep an already imported dump-backed catalog warm between dump snapshots.

## Bootstrap

A complete bootstrap imports authors, works and editions, records the newest `last_modified` timestamp present in the imported dump records, and stores that timestamp as the Open Library refresh checkpoint.

```bash
cyber-library bootstrap-openlibrary
cyber-library-refresh status --db .cyber-library/catalog.sqlite3
```

Partial imports (`--limit-each`) and incomplete dump sets do not seed a checkpoint because they are not a safe representation of a complete catalog snapshot.

## Run a bounded refresh

```bash
cyber-library-refresh run \
  --db .cyber-library/catalog.sqlite3 \
  --cache .cyber-library/cache.sqlite3 \
  --max-changes 250 \
  --max-documents 500
```

The refresher applies changed Author, Work and Edition documents to the local catalog. Work and Author changes trigger search-index refreshes for linked editions. Edition changes are indexed through the normal database upsert path.

The hard limits are intentional: at most 1,000 change sets and 1,000 changed documents are accepted per run. RecentChanges is not a replacement for monthly dumps.

## Checkpoint safety

The stored checkpoint advances only when all of these are true:

- the requested RecentChanges window reaches the previous checkpoint;
- the window is not truncated by `--max-changes`;
- changed document keys are not truncated by `--max-documents`;
- every selected document is fetched and applied without an error.

If any condition fails, the checkpoint remains unchanged. This prevents silently skipping catalog changes.

If `truncated=true` or `documents_truncated=true`, fetch/import a newer monthly dump instead of repeatedly widening RecentChanges into a bulk crawler.

## Manual seed

For an existing catalog built from a known snapshot, a checkpoint can be seeded explicitly:

```bash
cyber-library-refresh seed 2026-08-31T23:59:59Z \
  --db .cyber-library/catalog.sqlite3
```

Use this only when the timestamp genuinely represents the catalog snapshot boundary.

## Universe tiles

Edition updates change ISBN spatial density. Pass `--rebuild-universe` when a refresh should rebuild the precomputed density tiles immediately:

```bash
cyber-library-refresh run --rebuild-universe
```

For frequent refreshes, it is usually cheaper to rebuild the Universe index on a separate maintenance cadence with `cyber-library-scale rebuild`.

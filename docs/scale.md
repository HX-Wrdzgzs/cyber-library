# Scaling the ISBN Universe

Cyber Library v1.1 adds a second rendering path for very large local catalogs.

## Why tiles are needed

A catalog with millions of editions should not return thousands of arbitrary raw
points for a full-world view. That produces biased sampling and unnecessary SQLite
work. Cyber Library therefore precomputes density tiles for zoom levels 0 through 8.

At a distant zoom, the web explorer requests density cells. When the view becomes
sufficiently close, or when a subject/query filter is active, the API switches back
to individual edition points.

## Build or rebuild the scale indexes

```bash
cyber-library-scale rebuild --db .cyber-library/catalog.sqlite3
```

This performs the existing catalog reindex first and then creates universe tiles.
Tile levels are committed independently and carry a source revision marker, so a
rerun after interruption skips levels that are already complete for the same local
catalog revision.

To build only the universe tiles:

```bash
cyber-library-scale build-universe --db .cyber-library/catalog.sqlite3
```

Force every tile level to be regenerated:

```bash
cyber-library-scale build-universe --force
```

Inspect the current tile/index state:

```bash
cyber-library-scale status
```

## Bootstrap integration

`cyber-library bootstrap-openlibrary` automatically builds the universe density
tiles after the dump import and normal reindex, unless reindexing is explicitly
skipped.

## API behavior

`GET /api/universe` accepts an optional integer `z` parameter.

- Unfiltered distant views use `mode: "tiles"` when precomputed data exists.
- Filtered views and close views use `mode: "points"`.
- Clients should handle both modes.

The tile representation is an acceleration structure only. It does not change the
ISBN-to-Hilbert coordinate mapping and it is not a subject classification system.

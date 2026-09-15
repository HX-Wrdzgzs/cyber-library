# Bulk importer benchmark

`cyber-library-benchmark` exercises the real Open Library dump importer against deterministic synthetic gzip TSV dumps. It is intended for regression measurement and hardware sizing; synthetic throughput is not a promise of production throughput for the full Open Library corpus.

```bash
cyber-library-benchmark bulk --records 10000
```

Keep generated data for inspection:

```bash
cyber-library-benchmark bulk \
  --records 100000 \
  --workdir .cyber-library/bench
```

Output includes imported record counts, elapsed seconds, editions/second and resulting SQLite size. `--no-reindex` isolates ingestion throughput from final search-index construction.

For very large real imports, benchmark on the actual target filesystem because storage latency, WAL behavior, decompression speed and SQLite build options materially affect throughput.

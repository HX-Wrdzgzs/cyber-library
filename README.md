# Cyber Library

> Explore humanity's published knowledge.

[![CI](https://github.com/HX-Wrdzgzs/cyber-library/actions/workflows/ci.yml/badge.svg)](https://github.com/HX-Wrdzgzs/cyber-library/actions/workflows/ci.yml)

Cyber Library is a GitHub-first, machine-readable and AI-assisted book knowledge project. The long-term goal is not a giant folder of PDFs: it is a navigable catalog and knowledge layer connecting **Works, Editions, Authors, identifiers, subjects, analysis and visualization**.

The first runnable version already supports ISBN normalization, low-volume Open Library resolution, bulk Open Library dump ingestion into SQLite, local lookup, evidence-bounded catalog analysis, a JSON API and a minimal browser explorer.

## Why this model

`book == ISBN` is wrong. One intellectual Work may have many editions, translations, publishers and ISBNs.

```text
Author ─────┐
            ▼
           Work
          /  |  \
         ▼   ▼   ▼
    Edition Edition Edition
       │       │       │
      ISBN    ISBN    other identifiers
```

Cyber Library also keeps bibliographic facts separate from generated interpretation.

## Book Intelligence

```text
L0  Metadata only
L1  Catalog analysis
L2  Source-backed analysis
L3  Full-text analysis
```

L1 may generate a short overview, tags and a metadata-derived mind map. It must not invent chapter contents. Detailed interpretation, chapter summaries, table of contents and structural outlines stay empty until the evidence level supports them.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
# activate the environment
python -m pip install -e .
python -m unittest discover -s tests -v
```

Normalize an ISBN:

```bash
cyber-library isbn 0-306-40615-2
# 9780306406157
```

Resolve one book using the low-volume Open Library API:

```bash
cyber-library resolve 9780140328721 --analyze --contact you@example.com
```

Run the local explorer:

```bash
cyber-library serve --port 8080 --contact you@example.com
```

Open `http://127.0.0.1:8080`.

## Bulk catalog mode

Do **not** build a large catalog by firing millions of single-book API calls. Open Library explicitly provides monthly data dumps for bulk access.

Import a Work / Edition / Author dump file (plain TSV or `.gz`):

```bash
cyber-library import-dump /path/to/ol_dump_editions_latest.txt.gz --db data/catalog.sqlite3
cyber-library import-dump /path/to/ol_dump_works_latest.txt.gz --db data/catalog.sqlite3
cyber-library import-dump /path/to/ol_dump_authors_latest.txt.gz --db data/catalog.sqlite3
```

Inspect counts:

```bash
cyber-library stats --db data/catalog.sqlite3
```

Resolve from local data only:

```bash
cyber-library resolve 9780140328721 --db data/catalog.sqlite3 --no-live --analyze
```

Or let the local catalog take priority and use the live source only for misses:

```bash
cyber-library serve --db data/catalog.sqlite3 --contact you@example.com
```

Open Library's current API guidance describes its web API as low-volume, human-facing access, asks applications to cache results and identify themselves, and directs bulk projects to monthly dumps. Current documented rate limits are 1 request/second by default and 3 requests/second for identified requests. See: https://openlibrary.org/developers/api and https://openlibrary.org/developers/dumps

## Current repository

```text
cyber-library/
├─ src/cyber_library/
│  ├─ identifiers.py       # ISBN validation / normalization
│  ├─ models.py            # Work / Edition / Analysis
│  ├─ sources/openlibrary.py
│  ├─ database.py          # local bulk catalog
│  ├─ dump.py              # Open Library dump ingestion
│  ├─ intelligence.py      # evidence-bounded L1 analysis
│  ├─ service.py           # local-first resolver
│  ├─ server.py            # JSON API + static UI
│  └─ cli.py
├─ web/                    # minimal explorer
├─ schemas/                # JSON schemas
├─ docs/                   # architecture / data / licensing
├─ references/             # upstream project references
└─ tests/
```

## ISBN Universe

The original inspiration is [`phiresky/isbn-visualization`](https://github.com/phiresky/isbn-visualization). Cyber Library currently references it but does not copy its source code.

The intended future bridge is:

```text
ISBN coordinate
      ↓
Edition resolver
      ↓
Work
      ↓
subjects / tags / analysis / related concepts
```

ISBN-space coordinates and semantic categories remain separate. That lets the future renderer highlight "all books about X" across the ISBN universe without pretending ISBN ranges are subject classes.

The upstream repository contains an AGPLv3 license file. This repository's original code is MIT-licensed; see [NOTICE.md](NOTICE.md) and [docs/licensing.md](docs/licensing.md) before any code-level integration.

## What this project does not claim

- It does not currently contain every book in existence.
- ISBN does not cover every historical or modern text.
- It does not mirror copyrighted full text by default.
- Metadata availability does not imply full-text redistribution rights.
- AI output is not stored as bibliographic fact.

## Roadmap

See [ROADMAP.md](ROADMAP.md). The next major layers are entity reconciliation, search, source-backed L2 analysis, knowledge graphs, and the ISBN Universe renderer.

## License

Cyber Library's original code: [MIT](LICENSE).

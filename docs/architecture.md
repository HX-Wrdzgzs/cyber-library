# Architecture

Cyber Library keeps five concerns separate:

```text
Sources
  │
  ├─ Open Library dumps ───────────┐
  ├─ low-volume live APIs          │
  └─ authorized local content      │
                                   ▼
                         Normalized Catalog
                       Work / Edition / IDs
                                   │
           ┌───────────────────────┼──────────────────────┐
           ▼                       ▼                      ▼
        Search                  Evidence              ISBN Space
      FTS / SQL            descriptions / TOC       Hilbert coords
           │                       │                      │
           └──────────────┬────────┴─────────┬────────────┘
                          ▼                  ▼
                    Intelligence       Knowledge Graph
                          │                  │
                          └────────┬─────────┘
                                   ▼
                              HTTP API
                                   ▼
                             Web Explorer
```

## Catalog layer

SQLite is the default zero-dependency backend. It stores:

- works;
- editions;
- authors;
- identifiers;
- generated analysis records;
- content metadata/hashes.

Raw Open Library JSON is retained inside catalog rows so later versions can
reconstruct fields without re-downloading the dump.

## Search layer

FTS5 is used when the Python SQLite build includes it. Otherwise, Cyber Library
falls back to SQL `LIKE` queries. The fallback is slower but keeps the project
portable.

## Evidence layer

Evidence is separate from bibliographic truth. Examples:

- description;
- first sentence;
- notes;
- excerpts;
- table of contents;
- user-authorized full text.

Analysis may only claim what the available evidence can support.

## Intelligence layer

The deterministic engine works without external AI:

- extractive summaries;
- keyword/theme extraction;
- structure detection;
- chapter/section summaries;
- mind-map construction.

An optional OpenAI-compatible chat-completions endpoint can improve prose and
synthesis. LLM output is constrained to evidence already collected by the
pipeline.

## Visualization layer

Cyber Library does not include `isbn-visualization` source code. It independently
maps the ISBN namespace onto a Hilbert plane and exposes viewport queries through
`/api/universe`.

At large production scale, the next step is precomputed spatial tiles rather than
returning individual points directly.

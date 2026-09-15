# Architecture

The visualization is a client of the catalog, not the catalog itself.

```text
External metadata / dumps
          │
          ▼
      Ingestion
          │
          ▼
     Normalization
          │
          ▼
   Entity Resolution
    Work / Edition
          │
   ┌──────┼─────────┐
   ▼      ▼         ▼
Catalog  Search  Intelligence
   │      │         │
   └──────┼─────────┘
          ▼
         API
          │
    ┌─────┴──────────┐
    ▼                ▼
ISBN Universe   Knowledge Space
```

## Catalog

Owns bibliographic truth: works, editions, authors, identifiers, publishers, publication metadata and provenance.

## Search

Will own lexical indexes, facets, semantic vectors and ranking signals. ISBN prefixes are not subject classification.

## Intelligence

Owns generated interpretation. Generated analysis never silently overwrites catalog facts.

## Visualization

Two orthogonal views are planned:

- **ISBN Space**: publication / identifier topology.
- **Knowledge Space**: semantic subject / concept topology.

## Online vs bulk data

Low-volume interactive lookups may use source APIs. Large imports use source-provided dumps. A public deployment must not turn a third-party public API into its high-traffic database backend.

# Cyber Library

> Explore humanity's published knowledge.

Cyber Library is an open project for building a machine-readable, AI-assisted map of books and published knowledge.

The project starts as a GitHub-first specification and prototype. A web interface can be added later without changing the core data model.

## Goals

Cyber Library aims to combine:

- global bibliographic metadata;
- Work / Edition / Author separation;
- ISBN-space visualization;
- subject classification and tags;
- AI-assisted brief and detailed interpretation;
- tables of contents and structural outlines when legitimate source material is available;
- mind maps and knowledge graphs;
- semantic search;
- transparent provenance and analysis confidence.

The project does **not** assume that `book == ISBN`. ISBN is one identifier for an edition. A single intellectual work can have many editions, languages and identifiers.

## Core idea

```text
                      CYBER LIBRARY

                    Published Knowledge
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       Catalog        Intelligence       Graph
          │                │                │
   Work / Edition      Brief / Deep      Concepts
   Author / IDs         Outline / TOC      Tags
   Publisher / Date     Mind Map          Relations
          │                │                │
          └────────────────┼────────────────┘
                           │
                       Exploration
                           │
             ┌─────────────┴─────────────┐
             │                           │
        ISBN Universe              Knowledge Space
```

## Project status

**Stage: specification + prototype**

Current priorities:

1. stabilize the canonical data model;
2. define provenance and AI-analysis levels;
3. implement metadata ingestion;
4. resolve ISBN/edition/work relationships;
5. build search and graph indexes;
6. integrate an ISBN visualization layer;
7. build the web explorer.

See [ROADMAP.md](ROADMAP.md).

## Canonical entities

### Work

The abstract intellectual or creative work.

### Edition

A concrete published manifestation of a Work.

### Analysis

AI-generated material is stored separately from bibliographic truth.

## AI analysis levels

```text
L0  Metadata only
L1  Catalog analysis
L2  Source-backed analysis
L3  Full-text analysis
```

A system must never claim chapter-level or full-book understanding when it only has metadata.

## ISBN Visualization

The visual concept is inspired by / intended to interoperate with:

- `phiresky/isbn-visualization`
- https://github.com/phiresky/isbn-visualization

Cyber Library does **not** currently copy that repository's source code. The upstream repository contains an AGPLv3 license file, so any future code-level integration must be reviewed for license compatibility before merging.

## Non-goals for the first version

- mirroring every book's full text;
- bypassing publisher or library access controls;
- pretending all books have ISBNs;
- pre-generating AI summaries for every known edition;
- storing unverifiable AI output as bibliographic fact.

## License

A final project license has intentionally **not** been selected in this bootstrap commit.

Reason: the project may later interoperate with or derive code from AGPL-licensed `isbn-visualization`. The license boundary should be decided before third-party source code is imported.

Until a license is added, normal copyright rules apply to this repository's original material.

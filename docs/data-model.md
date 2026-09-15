# Data model

## Work

An abstract intellectual or creative work.

Key fields:

- id
- canonical title
- authors
- subjects
- normalized categories
- description
- first sentence
- source references

## Edition

A concrete published manifestation of a Work.

Key fields:

- id
- work_id
- edition title
- language
- publisher
- publication date
- page count
- physical format
- cover
- table of contents
- identifiers

## Identifier

Current built-in schemes include:

- ISBN-13
- ISBN-10
- OCLC
- LCCN
- Internet Archive identifier

The model is deliberately open to DOI, Wikidata IDs and other identifiers.

## Evidence

`EvidenceItem` records:

- kind
- text
- source_ref
- title
- URL

Evidence is never silently promoted into a catalog fact.

## Analysis

Analysis stores generated interpretation separately from the Work/Edition record:

- level
- brief
- summary
- detailed
- tags
- categories
- themes
- key points
- table of contents
- outline
- chapter summaries
- mind map
- confidence
- sources
- warnings
- generation model/time

## Full text

Raw full text is not stored by default. The local database can retain:

- SHA-256 content hash
- associated Work/Edition
- rights declaration
- source path
- character count
- generated analysis

This design keeps the catalog usable without turning it into a content mirror.

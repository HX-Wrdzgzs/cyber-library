# Data Model

## Work

The abstract intellectual or creative work. Typical fields: canonical title, authors, subjects, concepts, related works and source references.

## Edition

A concrete published manifestation of a Work. Typical fields: ISBNs, language, publisher, publication date, translator, page count, cover and format.

## Identifier

ISBN is not universal. Cyber Library can attach ISBN-10, ISBN-13, Open Library IDs, OCLC, LCCN, DOI, Wikidata identifiers and internal IDs.

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

The system must never use a single ISBN row as the canonical identity of the intellectual Work.

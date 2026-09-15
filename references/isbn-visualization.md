# ISBN Visualization reference

Upstream:
https://github.com/phiresky/isbn-visualization

Cyber Library started from the product question: what if a global ISBN map were
connected to a normalized catalog, evidence-aware book analysis and a knowledge
graph?

## Boundary

Cyber Library v1.0 does not vendor, copy or modify upstream source code.

Instead:

```text
Cyber Library catalog
        │
        ├─ semantic categories
        ├─ search
        ├─ analysis
        └─ ISBN Hilbert coordinate
                │
                ▼
          independent canvas UI
```

This keeps the original project as a reference while avoiding an accidental
license mismatch between an AGPL-derived visualization and Cyber Library's MIT
codebase.

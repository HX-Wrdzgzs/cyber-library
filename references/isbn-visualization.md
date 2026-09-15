# ISBN Visualization reference

Upstream: https://github.com/phiresky/isbn-visualization

Cyber Library currently treats this project as a reference and potential future renderer. No upstream source code is included here.

The integration concept is:

```text
ISBN coordinate
      ↓
Edition resolver
      ↓
Work
      ↓
subjects / tags / analysis / related concepts
```

ISBN-space position is not semantic classification. A future UI can color/highlight ISBN regions using Cyber Library's semantic metadata while keeping the two coordinate systems separate.

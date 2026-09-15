# Book Intelligence

The analysis pipeline is evidence-driven.

## L0 — catalog fact only

No interpretation.

## L1 — catalog analysis

Evidence:

- title
- author
- subjects
- publisher
- edition metadata

Possible output:

- broad overview
- categories
- tags

It must not invent chapter structure or plot/argument details.

## L2 — source-backed analysis

Evidence may include:

- description
- table of contents
- first sentence
- notes
- excerpts

Possible output:

- source-bounded summary
- detailed interpretation
- structural outline
- themes
- key points
- mind map

The system records source references and warns when evidence is incomplete.

## L3 — full-text analysis

Requires content the caller is entitled to analyze:

- public domain
- open license
- licensed
- user-provided

The local engine reads the full supplied text, makes section/chapter summaries,
extracts themes and produces a global synthesis.

When an LLM is enabled, long books are not simply truncated at the beginning.
Cyber Library first derives summaries across the text and then sends a bounded
whole-book digest for synthesis.

## LLM boundary

The configured model is optional. If it fails or is disabled, deterministic
analysis remains available.

The model prompt explicitly forbids adding facts outside supplied evidence.

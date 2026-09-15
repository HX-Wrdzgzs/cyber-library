# Contributing

## Core rules

1. Work, Edition and Identifier must remain separate concepts.
2. Bibliographic facts and generated interpretation must not be mixed.
3. Every new source adapter must preserve provenance.
4. Bulk data should use source-provided dumps/feeds, not abusive API crawling.
5. Full text must have a clear rights basis.
6. Do not import third-party source code without reviewing license compatibility.
7. Tests must cover schema or behavior changes.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src
node --check web/app.js
```

No pull-request workflow is required by the software itself; repository maintainers
may choose their own contribution policy.

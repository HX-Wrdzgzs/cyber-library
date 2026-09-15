# Contributing

## Core rules

1. Bibliographic facts and AI-generated interpretation stay separate.
2. Work, Edition and Identifier are distinct entities.
3. Imported data keeps provenance.
4. AI output states its evidence level.
5. Unsupported chapter/full-text claims are rejected rather than invented.
6. Do not add copyrighted full text unless redistribution is clearly permitted.
7. Review third-party software and data terms before importing them.

## Development

```bash
python -m venv .venv
# activate the environment
python -m pip install -e .
python -m unittest discover -s tests -v
```

Run the local explorer:

```bash
cyber-library serve --port 8080 --contact you@example.com
```

For schema changes, update the schema, sample data, docs and tests in the same commit.

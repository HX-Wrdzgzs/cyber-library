# Security

Report security issues privately to the repository owner rather than publishing
credentials or exploit details in a public issue.

## Secrets

Never commit:

- LLM API keys;
- private catalog credentials;
- licensed book text;
- private user documents.

Use environment variables for model credentials.

## Full-text endpoint

`POST /api/analyze-text` accepts user-provided content. The built-in server limits
request size but is not intended to be exposed as an unauthenticated public
large-file ingestion service.

If deploying publicly, add authentication, rate limiting and reverse-proxy request
limits.

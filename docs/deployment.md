# Deployment

## Local

```bash
cyber-library serve --host 127.0.0.1 --port 8080
```

## With catalog

```bash
cyber-library serve \
  --host 0.0.0.0 \
  --port 8080 \
  --db data/catalog.sqlite3 \
  --contact you@example.com
```

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

## LLM

Optional:

```env
CYBER_LIBRARY_LLM_BASE_URL=http://host.docker.internal:8000/v1
CYBER_LIBRARY_LLM_MODEL=your-model
CYBER_LIBRARY_LLM_API_KEY=
```

On Linux Docker, access to host services may require an explicit host-gateway
mapping depending on your Docker setup.

## Production notes

The built-in HTTP server is useful for a single-node deployment and development.

At much larger scale:

- put a reverse proxy in front;
- move catalog/search to dedicated stores;
- build universe density tiles offline;
- isolate full-text analysis workers;
- set request size/time limits;
- preserve source provenance and audit logs.

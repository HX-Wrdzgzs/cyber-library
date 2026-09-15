# REST API

The bundled HTTP server is intentionally dependency-light and serves both the browser explorer and JSON API.

## Catalog

```text
GET /api/health
GET /api/stats
GET /api/categories
GET /api/resolve?isbn=978...&analysis=auto
GET /api/search?q=machine+learning&limit=20
GET /api/graph?isbn=978...
```

Search becomes hybrid automatically when a configured embedding model has locally indexed editions.

## Knowledge Space

```text
GET /api/knowledge/concept?subject=Machine%20learning&limit=40
GET /api/knowledge/author?name=Author%20Name&limit=100
GET /api/knowledge/publisher?name=Publisher%20Name&limit=150
```

These endpoints require a local catalog and derive their relationships from stored catalog facts.

## ISBN Universe

```text
GET /api/universe?min_x=0&max_x=1&min_y=0&max_y=1&z=0&limit=5000
```

Responses use `mode: "tiles"` for available low-zoom precomputed density data and `mode: "points"` for close/filtered views.

## Lawful text analysis

```text
POST /api/analyze-text
Content-Type: application/json

{
  "title": "optional",
  "isbn": "optional",
  "rights": "user-provided",
  "text": "..."
}
```

Accepted rights values are defined by the content subsystem. The API refuses empty/oversized payloads and does not imply permission to process text the caller is not entitled to use.

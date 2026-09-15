# HTTP API

The built-in server is intentionally small and dependency-free.

## Health

```http
GET /api/health
```

## Stats

```http
GET /api/stats
```

## Categories

```http
GET /api/categories
```

## Resolve

```http
GET /api/resolve?isbn=9780306406157&analysis=auto
```

`analysis` values:

- `none`
- `catalog`
- `source`
- `auto`

## Search

```http
GET /api/search?q=machine+learning&limit=20
```

Optional filters:

- `category`
- `language`
- `year_from`
- `year_to`

## Knowledge graph

```http
GET /api/graph?isbn=9780306406157
```

Returns `nodes`, `edges`, and a root Work ID.

## ISBN Universe

```http
GET /api/universe?min_x=0&max_x=1&min_y=0&max_y=1&limit=2500
```

Optional:

- `category`
- `q`

## Analyze authorized text

```http
POST /api/analyze-text
Content-Type: application/json

{
  "title": "Example",
  "isbn": "9780306406157",
  "rights": "user-provided",
  "text": "...",
  "headings": ["Chapter 1", "Chapter 2"]
}
```

Maximum request body: 16 MiB in the built-in server.

For larger production workloads, put a dedicated API server / job system in front
of the analysis engine rather than increasing the synchronous limit indefinitely.

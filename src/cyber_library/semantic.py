from __future__ import annotations

import hashlib
import heapq
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .database import CatalogDB


class EmbeddingError(RuntimeError):
    pass


@dataclass(slots=True)
class EmbeddingConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "EmbeddingConfig | None":
        base_url = os.getenv("CYBER_LIBRARY_EMBEDDING_BASE_URL", "").strip()
        model = os.getenv("CYBER_LIBRARY_EMBEDDING_MODEL", "").strip()
        if not base_url or not model:
            return None
        return cls(
            base_url=base_url,
            model=model,
            api_key=os.getenv("CYBER_LIBRARY_EMBEDDING_API_KEY") or None,
            timeout=float(os.getenv("CYBER_LIBRARY_EMBEDDING_TIMEOUT", "60")),
        )


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "EmbeddingClient | None":
        config = EmbeddingConfig.from_env()
        return cls(config) if config else None

    @property
    def model_name(self) -> str:
        return self.config.model

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return base if base.endswith("/embeddings") else base + "/embeddings"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = json.dumps({"model": self.config.model, "input": texts}, ensure_ascii=False).encode("utf-8")
        request = Request(self._endpoint(), data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                body = json.load(response)
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(2000).decode("utf-8", "replace")
            except Exception:
                pass
            raise EmbeddingError(f"Embedding HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise EmbeddingError(f"Embedding request failed: {exc}") from exc

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list):
            raise EmbeddingError("Embedding response did not contain a data array")
        ordered = sorted(
            (item for item in data if isinstance(item, dict)),
            key=lambda item: int(item.get("index", 0)),
        )
        vectors: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise EmbeddingError("Embedding response contained an invalid vector")
            try:
                vectors.append([float(value) for value in vector])
            except (TypeError, ValueError) as exc:
                raise EmbeddingError("Embedding vector contained a non-numeric value") from exc
        if len(vectors) != len(texts):
            raise EmbeddingError(f"Embedding count mismatch: expected {len(texts)}, got {len(vectors)}")
        return vectors


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_embedding_schema(catalog: CatalogDB) -> None:
    with catalog._lock:
        catalog.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS embeddings(
              edition_id TEXT NOT NULL,
              model TEXT NOT NULL,
              dimensions INTEGER NOT NULL,
              vector_json TEXT NOT NULL,
              text_hash TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(edition_id,model)
            );
            CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
            """
        )
        catalog.db.commit()


def embedding_count(catalog: CatalogDB, model: str | None = None) -> int:
    ensure_embedding_schema(catalog)
    with catalog._lock:
        if model:
            row = catalog.db.execute("SELECT COUNT(*) AS n FROM embeddings WHERE model=?", (model,)).fetchone()
        else:
            row = catalog.db.execute("SELECT COUNT(*) AS n FROM embeddings").fetchone()
        return int(row["n"])


def embedding_status(catalog: CatalogDB) -> dict[str, object]:
    ensure_embedding_schema(catalog)
    with catalog._lock:
        rows = catalog.db.execute(
            "SELECT model,COUNT(*) AS items,MIN(dimensions) AS min_dimensions,MAX(dimensions) AS max_dimensions "
            "FROM embeddings GROUP BY model ORDER BY model"
        ).fetchall()
    return {
        "models": [
            {
                "model": str(row["model"]),
                "items": int(row["items"]),
                "dimensions": int(row["min_dimensions"]) if row["min_dimensions"] == row["max_dimensions"] else None,
                "min_dimensions": int(row["min_dimensions"]),
                "max_dimensions": int(row["max_dimensions"]),
            }
            for row in rows
        ]
    }


def _embedding_text(catalog: CatalogDB, row) -> str:
    try:
        authors = catalog._author_names(json.loads(row["authors"] or "[]"))
    except (TypeError, json.JSONDecodeError):
        authors = []
    try:
        subjects = [str(x) for x in json.loads(row["subjects"] or "[]")]
    except (TypeError, json.JSONDecodeError):
        subjects = []
    try:
        categories = [str(x) for x in json.loads(row["categories"] or "[]")]
    except (TypeError, json.JSONDecodeError):
        categories = []
    try:
        publishers = [str(x) for x in json.loads(row["publishers"] or "[]")]
    except (TypeError, json.JSONDecodeError):
        publishers = []
    parts = [
        f"Title: {row['title'] or ''}",
        "Authors: " + "; ".join(authors),
        "Subjects: " + "; ".join(subjects[:32]),
        "Categories: " + "; ".join(categories[:16]),
        "Publishers: " + "; ".join(publishers[:8]),
        f"Language: {row['language'] or ''}",
        f"Published: {row['publish_date'] or ''}",
    ]
    return "\n".join(parts)[:12000]


def build_embedding_index(
    catalog: CatalogDB,
    client: EmbeddingClient,
    *,
    batch_size: int = 32,
    limit: int | None = None,
    force: bool = False,
) -> dict[str, object]:
    ensure_embedding_schema(catalog)
    batch_size = max(1, min(int(batch_size), 256))
    remaining = None if limit is None else max(0, int(limit))
    indexed = 0

    if force:
        with catalog._lock:
            catalog.db.execute("DELETE FROM embeddings WHERE model=?", (client.model_name,))
            catalog.db.commit()

    while remaining is None or remaining > 0:
        take = batch_size if remaining is None else min(batch_size, remaining)
        with catalog._lock:
            rows = catalog.db.execute(
                "SELECT e.id,COALESCE(w.title,e.title) AS title,w.authors,w.subjects,w.categories,e.publishers,e.language,e.publish_date "
                "FROM editions e LEFT JOIN works w ON w.id=e.work_id "
                "LEFT JOIN embeddings em ON em.edition_id=e.id AND em.model=? "
                "WHERE em.edition_id IS NULL ORDER BY e.rowid LIMIT ?",
                (client.model_name, take),
            ).fetchall()
        if not rows:
            break

        texts = [_embedding_text(catalog, row) for row in rows]
        vectors = client.embed(texts)
        now = _now()
        with catalog._lock:
            for row, text, vector in zip(rows, texts, vectors):
                catalog.db.execute(
                    "INSERT INTO embeddings(edition_id,model,dimensions,vector_json,text_hash,updated_at) VALUES(?,?,?,?,?,?) "
                    "ON CONFLICT(edition_id,model) DO UPDATE SET dimensions=excluded.dimensions,vector_json=excluded.vector_json,text_hash=excluded.text_hash,updated_at=excluded.updated_at",
                    (
                        str(row["id"]),
                        client.model_name,
                        len(vector),
                        json.dumps(vector, separators=(",", ":")),
                        hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        now,
                    ),
                )
            catalog.db.commit()
        indexed += len(rows)
        if remaining is not None:
            remaining -= len(rows)

    return {"model": client.model_name, "indexed": indexed, "total": embedding_count(catalog, client.model_name)}


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


def _hydrate_result(catalog: CatalogDB, edition_id: str, score: float) -> dict | None:
    with catalog._lock:
        row = catalog.db.execute(
            "SELECT e.id AS edition_id,e.work_id,COALESCE(w.title,e.title) AS title,w.authors AS author_ids,w.subjects,e.publishers,w.categories,e.language,e.publish_date "
            "FROM editions e LEFT JOIN works w ON w.id=e.work_id WHERE e.id=?",
            (edition_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["authors"] = " | ".join(catalog._author_names(json.loads(row["author_ids"] or "[]")))
        data["subjects"] = " | ".join(json.loads(row["subjects"] or "[]"))
        data["publishers"] = " | ".join(json.loads(row["publishers"] or "[]"))
        data["categories"] = " | ".join(json.loads(row["categories"] or "[]"))
        result = catalog._result(data, score)
        result["semantic_score"] = score
        result["rank_source"] = "semantic"
        return result


def semantic_search(
    catalog: CatalogDB,
    client: EmbeddingClient,
    query: str,
    *,
    limit: int = 20,
    max_scan: int = 50000,
    category: str | None = None,
    language: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    ensure_embedding_schema(catalog)
    query_vector = client.embed([query.strip()])[0]
    limit = max(1, min(int(limit), 100))
    max_scan = max(limit, min(int(max_scan), 500000))
    heap: list[tuple[float, str]] = []

    with catalog._lock:
        cursor = catalog.db.execute(
            "SELECT edition_id,vector_json FROM embeddings WHERE model=? LIMIT ?",
            (client.model_name, max_scan),
        )
        for row in cursor:
            try:
                vector = [float(x) for x in json.loads(row["vector_json"])]
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            score = _cosine(query_vector, vector)
            item = (score, str(row["edition_id"]))
            if len(heap) < max(limit * 6, 50):
                heapq.heappush(heap, item)
            elif score > heap[0][0]:
                heapq.heapreplace(heap, item)

    ranked = sorted(heap, reverse=True)
    out: list[dict] = []
    for score, edition_id in ranked:
        result = _hydrate_result(catalog, edition_id, score)
        if not result:
            continue
        if category and category not in result.get("categories", []):
            continue
        if language and result.get("language") != language:
            continue
        year_text = str(result.get("publish_date") or "")[:4]
        year = int(year_text) if year_text.isdigit() else None
        if year_from and (year is None or year < year_from):
            continue
        if year_to and (year is None or year > year_to):
            continue
        out.append(result)
        if len(out) >= limit:
            break
    return out


def hybrid_search(
    catalog: CatalogDB,
    client: EmbeddingClient,
    query: str,
    lexical: list[dict],
    *,
    limit: int = 20,
    category: str | None = None,
    language: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    semantic = semantic_search(
        catalog,
        client,
        query,
        limit=max(limit * 2, 30),
        category=category,
        language=language,
        year_from=year_from,
        year_to=year_to,
    )
    by_id: dict[str, dict] = {}
    rrf: dict[str, float] = {}
    for rank, item in enumerate(lexical, 1):
        key = str(item.get("edition_id") or "")
        if not key:
            continue
        by_id[key] = dict(item)
        rrf[key] = rrf.get(key, 0.0) + 1.0 / (60 + rank)
    for rank, item in enumerate(semantic, 1):
        key = str(item.get("edition_id") or "")
        if not key:
            continue
        by_id.setdefault(key, dict(item))
        by_id[key]["semantic_score"] = item.get("semantic_score")
        rrf[key] = rrf.get(key, 0.0) + 1.0 / (60 + rank)
    ordered = sorted(rrf, key=lambda key: rrf[key], reverse=True)[: max(1, min(limit, 100))]
    result = []
    for key in ordered:
        item = by_id[key]
        item["hybrid_score"] = rrf[key]
        item["rank_source"] = "hybrid"
        result.append(item)
    return result

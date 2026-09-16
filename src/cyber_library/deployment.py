from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .database import CatalogDB


class DeploymentError(RuntimeError):
    pass


def _catalog_documents(catalog: CatalogDB, limit: int | None = None) -> Iterable[dict]:
    sql = (
        "SELECT e.id,e.work_id,COALESCE(w.title,e.title) AS title,w.authors,w.subjects,w.categories,"
        "e.publishers,e.language,e.publish_date,e.cover_url,e.space_x,e.space_y "
        "FROM editions e LEFT JOIN works w ON w.id=e.work_id ORDER BY e.rowid"
    )
    params: tuple[object, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (max(0, int(limit)),)
    with catalog._lock:
        rows = catalog.db.execute(sql, params).fetchall()
        for row in rows:
            try:
                authors = catalog._author_names(json.loads(row["authors"] or "[]"))
            except (TypeError, json.JSONDecodeError):
                authors = []
            def values(name: str) -> list[str]:
                try:
                    raw = json.loads(row[name] or "[]")
                except (TypeError, json.JSONDecodeError):
                    return []
                return [str(x) for x in raw if str(x).strip()] if isinstance(raw, list) else []
            isbn = catalog.db.execute(
                "SELECT value FROM identifiers WHERE edition_id=? AND scheme='isbn13' LIMIT 1",
                (row["id"],),
            ).fetchone()
            yield {
                "edition_id": str(row["id"]),
                "work_id": str(row["work_id"]) if row["work_id"] else None,
                "title": str(row["title"] or ""),
                "authors": authors,
                "subjects": values("subjects"),
                "categories": values("categories"),
                "publishers": values("publishers"),
                "language": row["language"],
                "publish_date": row["publish_date"],
                "cover_url": row["cover_url"],
                "isbn13": str(isbn["value"]) if isbn else None,
                "space_x": float(row["space_x"]) if row["space_x"] is not None else None,
                "space_y": float(row["space_y"]) if row["space_y"] is not None else None,
            }


@dataclass(slots=True)
class PostgresConfig:
    dsn: str

    @classmethod
    def from_env(cls) -> "PostgresConfig | None":
        dsn = os.getenv("CYBER_LIBRARY_POSTGRES_DSN", "").strip()
        return cls(dsn) if dsn else None


class PostgresCatalogAdapter:
    def __init__(self, config: PostgresConfig, connect_factory=None) -> None:
        self.config = config
        self._connect_factory = connect_factory

    @classmethod
    def from_env(cls) -> "PostgresCatalogAdapter | None":
        config = PostgresConfig.from_env()
        return cls(config) if config else None

    def health(self) -> dict[str, object]:
        return {"name": "postgres", "configured": bool(self.config.dsn), "postgis_optional": True}

    def _connect(self):
        if self._connect_factory:
            return self._connect_factory(self.config.dsn)
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise DeploymentError("PostgreSQL adapter requires: pip install -e '.[postgres]'") from exc
        return psycopg.connect(self.config.dsn)

    def ensure_schema(self) -> dict[str, object]:
        conn = self._connect()
        postgis = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cyber_books(
                      edition_id TEXT PRIMARY KEY,
                      work_id TEXT,
                      title TEXT NOT NULL,
                      authors JSONB NOT NULL DEFAULT '[]'::jsonb,
                      subjects JSONB NOT NULL DEFAULT '[]'::jsonb,
                      categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                      publishers JSONB NOT NULL DEFAULT '[]'::jsonb,
                      language TEXT,
                      publish_date TEXT,
                      isbn13 TEXT,
                      cover_url TEXT,
                      space_x DOUBLE PRECISION,
                      space_y DOUBLE PRECISION,
                      search_document TSVECTOR GENERATED ALWAYS AS (
                        to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(authors::text,'') || ' ' ||
                          coalesce(subjects::text,'') || ' ' || coalesce(categories::text,'') || ' ' ||
                          coalesce(publishers::text,''))
                      ) STORED
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_cyber_books_search ON cyber_books USING GIN(search_document)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_cyber_books_isbn13 ON cyber_books(isbn13)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_cyber_books_space ON cyber_books(space_x,space_y)")
            conn.commit()
            try:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                    cur.execute("ALTER TABLE cyber_books ADD COLUMN IF NOT EXISTS space_point geometry(Point,0)")
                conn.commit(); postgis = True
            except Exception:
                conn.rollback()
            return {"schema": "cyber_books", "postgis": postgis}
        finally:
            conn.close()

    def sync_from_sqlite(self, catalog: CatalogDB, *, batch_size: int = 1000, limit: int | None = None) -> dict[str, int | bool]:
        self.ensure_schema()
        conn = self._connect(); synced = 0; batch_size = max(1, min(int(batch_size), 5000))
        sql = """
          INSERT INTO cyber_books(edition_id,work_id,title,authors,subjects,categories,publishers,language,publish_date,isbn13,cover_url,space_x,space_y)
          VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s)
          ON CONFLICT(edition_id) DO UPDATE SET
            work_id=excluded.work_id,title=excluded.title,authors=excluded.authors,subjects=excluded.subjects,
            categories=excluded.categories,publishers=excluded.publishers,language=excluded.language,
            publish_date=excluded.publish_date,isbn13=excluded.isbn13,cover_url=excluded.cover_url,
            space_x=excluded.space_x,space_y=excluded.space_y
        """
        try:
            pending: list[tuple] = []
            for doc in _catalog_documents(catalog, limit):
                pending.append((
                    doc["edition_id"], doc["work_id"], doc["title"], json.dumps(doc["authors"]),
                    json.dumps(doc["subjects"]), json.dumps(doc["categories"]), json.dumps(doc["publishers"]),
                    doc["language"], doc["publish_date"], doc["isbn13"], doc["cover_url"], doc["space_x"], doc["space_y"],
                ))
                if len(pending) >= batch_size:
                    with conn.cursor() as cur: cur.executemany(sql, pending)
                    conn.commit(); synced += len(pending); pending.clear()
            if pending:
                with conn.cursor() as cur: cur.executemany(sql, pending)
                conn.commit(); synced += len(pending)
            postgis = False
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='cyber_books' AND column_name='space_point')")
                    row = cur.fetchone(); postgis = bool(row and row[0])
                    if postgis:
                        cur.execute("UPDATE cyber_books SET space_point=ST_SetSRID(ST_MakePoint(space_x,space_y),0) WHERE space_x IS NOT NULL AND space_y IS NOT NULL")
                conn.commit()
            except Exception:
                conn.rollback()
            return {"synced": synced, "postgis": postgis}
        finally:
            conn.close()

    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        conn = self._connect(); limit = max(1, min(int(limit), 100))
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT edition_id,work_id,title,authors,subjects,categories,publishers,language,publish_date,isbn13,cover_url,"
                    "ts_rank_cd(search_document,plainto_tsquery('simple',%s)) AS score "
                    "FROM cyber_books WHERE search_document @@ plainto_tsquery('simple',%s) ORDER BY score DESC,title LIMIT %s",
                    (query, query, limit),
                )
                columns = [item.name if hasattr(item, "name") else item[0] for item in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        finally:
            conn.close()


@dataclass(slots=True)
class OpenSearchConfig:
    base_url: str
    index: str = "cyber-library"
    username: str | None = None
    password: str | None = None
    bearer_token: str | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenSearchConfig | None":
        base = os.getenv("CYBER_LIBRARY_OPENSEARCH_URL", "").strip()
        if not base: return None
        return cls(base.rstrip("/"), os.getenv("CYBER_LIBRARY_OPENSEARCH_INDEX", "cyber-library"), os.getenv("CYBER_LIBRARY_OPENSEARCH_USERNAME") or None, os.getenv("CYBER_LIBRARY_OPENSEARCH_PASSWORD") or None, os.getenv("CYBER_LIBRARY_OPENSEARCH_BEARER_TOKEN") or None, float(os.getenv("CYBER_LIBRARY_OPENSEARCH_TIMEOUT", "30")))


class OpenSearchAdapter:
    def __init__(self, config: OpenSearchConfig) -> None: self.config = config

    @classmethod
    def from_env(cls) -> "OpenSearchAdapter | None":
        config = OpenSearchConfig.from_env(); return cls(config) if config else None

    def health(self) -> dict[str, object]:
        return {"name":"opensearch","configured":bool(self.config.base_url),"index":self.config.index,"endpoint":self.config.base_url}

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        headers = {"Accept":"application/json","Content-Type":content_type,"User-Agent":"CyberLibrary/3.0"}
        if self.config.bearer_token: headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        elif self.config.username is not None:
            token = base64.b64encode(f"{self.config.username}:{self.config.password or ''}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    def _request(self, method: str, path: str, payload=None, *, content_type: str = "application/json", allow_404: bool = False):
        data = None
        if payload is not None: data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        request = Request(self.config.base_url + path, data=data, headers=self._headers(content_type), method=method)
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if allow_404 and exc.code == 404: return None
            detail = exc.read(2000).decode("utf-8", "replace")
            raise DeploymentError(f"OpenSearch HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DeploymentError(f"OpenSearch request failed: {exc}") from exc

    def ensure_index(self) -> dict:
        path = "/" + quote(self.config.index, safe="")
        existing = self._request("GET", path, allow_404=True)
        if existing is not None: return {"index":self.config.index,"created":False}
        body = {"mappings":{"properties":{
            "edition_id":{"type":"keyword"},"work_id":{"type":"keyword"},"title":{"type":"text"},
            "authors":{"type":"text"},"subjects":{"type":"text"},"categories":{"type":"keyword"},
            "publishers":{"type":"text"},"language":{"type":"keyword"},"publish_date":{"type":"keyword"},
            "isbn13":{"type":"keyword"},"cover_url":{"type":"keyword","index":False},
            "space_x":{"type":"float"},"space_y":{"type":"float"}
        }}}
        self._request("PUT", path, body); return {"index":self.config.index,"created":True}

    def sync_from_sqlite(self, catalog: CatalogDB, *, batch_size: int = 500, limit: int | None = None) -> dict[str, int]:
        self.ensure_index(); batch_size = max(1, min(int(batch_size), 5000)); indexed = 0; batch: list[dict] = []
        def flush(items: list[dict]) -> int:
            if not items: return 0
            lines=[]
            for doc in items:
                lines.append(json.dumps({"index":{"_index":self.config.index,"_id":doc["edition_id"]}}, separators=(",",":")))
                lines.append(json.dumps(doc, ensure_ascii=False, separators=(",",":")))
            payload=("\n".join(lines)+"\n").encode()
            result=self._request("POST","/_bulk",payload,content_type="application/x-ndjson")
            if isinstance(result,dict) and result.get("errors"):
                failures=[]
                for item in result.get("items") or []:
                    action=item.get("index") if isinstance(item,dict) else None
                    if isinstance(action,dict) and int(action.get("status",200))>=300: failures.append(action)
                raise DeploymentError(f"OpenSearch bulk indexing reported {len(failures)} failed actions")
            return len(items)
        for doc in _catalog_documents(catalog, limit):
            batch.append(doc)
            if len(batch)>=batch_size: indexed += flush(batch); batch=[]
        indexed += flush(batch)
        self._request("POST", "/"+quote(self.config.index,safe="")+"/_refresh")
        return {"indexed":indexed}

    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        body={"size":max(1,min(int(limit),100)),"query":{"multi_match":{"query":query,"fields":["title^4","authors^3","subjects^2","publishers","categories"]}}}
        result=self._request("POST","/"+quote(self.config.index,safe="")+"/_search",body)
        hits=result.get("hits",{}).get("hits",[]) if isinstance(result,dict) else []
        out=[]
        for hit in hits if isinstance(hits,list) else []:
            if not isinstance(hit,dict): continue
            source=dict(hit.get("_source") or {}); source["score"]=hit.get("_score"); source["source"]="opensearch"; out.append(source)
        return out


@dataclass(slots=True)
class QdrantConfig:
    base_url: str
    collection: str = "cyber_library"
    api_key: str | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "QdrantConfig | None":
        base=os.getenv("CYBER_LIBRARY_QDRANT_URL","").strip()
        if not base:return None
        return cls(base.rstrip("/"),os.getenv("CYBER_LIBRARY_QDRANT_COLLECTION","cyber_library"),os.getenv("CYBER_LIBRARY_QDRANT_API_KEY") or None,float(os.getenv("CYBER_LIBRARY_QDRANT_TIMEOUT","30")))


class QdrantAdapter:
    def __init__(self, config: QdrantConfig) -> None:self.config=config

    @classmethod
    def from_env(cls) -> "QdrantAdapter | None":
        config=QdrantConfig.from_env();return cls(config) if config else None

    def health(self)->dict[str,object]:return {"name":"qdrant","configured":bool(self.config.base_url),"collection":self.config.collection,"endpoint":self.config.base_url}

    def _request(self,method:str,path:str,payload=None,*,allow_404:bool=False):
        headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"CyberLibrary/3.0"}
        if self.config.api_key:headers["api-key"]=self.config.api_key
        data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
        request=Request(self.config.base_url+path,data=data,headers=headers,method=method)
        try:
            with urlopen(request,timeout=self.config.timeout) as response:
                raw=response.read();return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if allow_404 and exc.code==404:return None
            detail=exc.read(2000).decode("utf-8","replace");raise DeploymentError(f"Qdrant HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError,TimeoutError,json.JSONDecodeError) as exc:raise DeploymentError(f"Qdrant request failed: {exc}") from exc

    def ensure_collection(self,dimensions:int)->dict:
        path="/collections/"+quote(self.config.collection,safe="")
        existing=self._request("GET",path,allow_404=True)
        if existing is not None:return {"collection":self.config.collection,"created":False}
        self._request("PUT",path,{"vectors":{"size":int(dimensions),"distance":"Cosine"}})
        return {"collection":self.config.collection,"created":True}

    @staticmethod
    def _point_id(edition_id:str)->str:return str(uuid.uuid5(uuid.NAMESPACE_URL,"cyber-library:"+edition_id))

    def sync_embeddings(self,catalog:CatalogDB,model:str,*,batch_size:int=256,limit:int|None=None)->dict[str,int]:
        with catalog._lock:
            rows=catalog.db.execute("SELECT edition_id,dimensions,vector_json FROM embeddings WHERE model=? ORDER BY edition_id"+(" LIMIT ?" if limit is not None else ""),(model,max(0,int(limit))) if limit is not None else (model,)).fetchall()
        if not rows:return {"indexed":0}
        dimensions=int(rows[0]["dimensions"]);self.ensure_collection(dimensions);batch_size=max(1,min(int(batch_size),1000));indexed=0
        for start in range(0,len(rows),batch_size):
            points=[]
            for row in rows[start:start+batch_size]:
                try:vector=[float(x) for x in json.loads(row["vector_json"])]
                except (TypeError,ValueError,json.JSONDecodeError):continue
                edition_id=str(row["edition_id"])
                points.append({"id":self._point_id(edition_id),"vector":vector,"payload":{"edition_id":edition_id,"model":model}})
            if points:
                self._request("PUT","/collections/"+quote(self.config.collection,safe="")+"/points?wait=true",{"points":points});indexed+=len(points)
        return {"indexed":indexed}

    def query(self,vector:list[float],*,limit:int=20)->list[dict]:
        result=self._request("POST","/collections/"+quote(self.config.collection,safe="")+"/points/query",{"query":[float(x) for x in vector],"limit":max(1,min(int(limit),100)),"with_payload":True})
        raw=result.get("result") if isinstance(result,dict) else None
        points=raw.get("points",[]) if isinstance(raw,dict) else []
        return [{"id":item.get("id"),"score":item.get("score"),"payload":item.get("payload") or {}} for item in points if isinstance(item,dict)]


@dataclass(slots=True)
class S3Config:
    bucket: str
    prefix: str = ""
    endpoint_url: str | None = None
    region: str | None = None

    @classmethod
    def from_env(cls)->"S3Config | None":
        bucket=os.getenv("CYBER_LIBRARY_S3_BUCKET","").strip()
        if not bucket:return None
        return cls(bucket,os.getenv("CYBER_LIBRARY_S3_PREFIX","").strip("/"),os.getenv("CYBER_LIBRARY_S3_ENDPOINT_URL") or None,os.getenv("CYBER_LIBRARY_S3_REGION") or None)


class S3ArtifactPublisher:
    def __init__(self,config:S3Config,client=None)->None:self.config=config;self._client=client

    @classmethod
    def from_env(cls)->"S3ArtifactPublisher | None":
        config=S3Config.from_env();return cls(config) if config else None

    def health(self)->dict[str,object]:return {"name":"s3","configured":bool(self.config.bucket),"bucket":self.config.bucket,"prefix":self.config.prefix,"endpoint":self.config.endpoint_url}

    def _get_client(self):
        if self._client is not None:return self._client
        try:import boto3  # type: ignore
        except ImportError as exc:raise DeploymentError("S3 publisher requires: pip install -e '.[s3]'") from exc
        self._client=boto3.client("s3",endpoint_url=self.config.endpoint_url,region_name=self.config.region);return self._client

    def publish_directory(self,directory:str|Path)->dict[str,object]:
        root=Path(directory)
        if not root.is_dir():raise DeploymentError(f"artifact directory does not exist: {root}")
        client=self._get_client();uploaded=[]
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            relative=path.relative_to(root).as_posix();key="/".join(x for x in (self.config.prefix,relative) if x)
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            cache_control="no-cache" if path.name=="manifest.json" else "public, max-age=86400"
            extra={"ContentType":content_type,"CacheControl":cache_control}
            client.upload_file(str(path),self.config.bucket,key,ExtraArgs=extra)
            digest=hashlib.sha256(path.read_bytes()).hexdigest();uploaded.append({"path":relative,"key":key,"sha256":digest,"bytes":path.stat().st_size})
        return {"bucket":self.config.bucket,"prefix":self.config.prefix,"uploaded":len(uploaded),"files":uploaded}

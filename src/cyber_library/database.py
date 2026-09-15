from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .evidence import openlibrary_evidence, text_value, toc_titles
from .identifiers import compact, is_valid_isbn13
from .models import Analysis, BookRecord, Edition, Provenance, Work
from .taxonomy import classify
from .universe import isbn_space_point


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wid(key: str) -> str:
    return f"openlibrary:work:{key.rsplit('/', 1)[-1]}"


def _eid(key: str) -> str:
    return f"openlibrary:edition:{key.rsplit('/', 1)[-1]}"


def _author_ids(raw: dict) -> list[str]:
    out = []
    for item in raw.get("authors") or []:
        if not isinstance(item, dict):
            continue
        candidate = item.get("author", item)
        if isinstance(candidate, dict) and candidate.get("key"):
            out.append(str(candidate["key"]))
    return list(dict.fromkeys(out))


def _cover_url(raw: dict, isbns: list[str]) -> str | None:
    covers = raw.get("covers") or []
    if covers and str(covers[0]).lstrip("-").isdigit() and int(covers[0]) > 0:
        return f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg?default=false"
    if isbns:
        return f"https://covers.openlibrary.org/b/isbn/{isbns[0]}-L.jpg?default=false"
    return None


class CatalogDB:
    def __init__(self, path: str | Path, index_on_write: bool = True) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.index_on_write = index_on_write
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=60)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA busy_timeout=60000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS works(
          id TEXT PRIMARY KEY,title TEXT NOT NULL,subjects TEXT NOT NULL DEFAULT '[]',
          authors TEXT NOT NULL DEFAULT '[]',description TEXT,categories TEXT NOT NULL DEFAULT '[]',raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS authors(id TEXT PRIMARY KEY,name TEXT NOT NULL,raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS editions(
          id TEXT PRIMARY KEY,work_id TEXT,title TEXT NOT NULL,language TEXT,publishers TEXT NOT NULL DEFAULT '[]',
          publish_date TEXT,page_count INTEGER,cover_url TEXT,table_of_contents TEXT NOT NULL DEFAULT '[]',
          physical_format TEXT,space_x REAL,space_y REAL,raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS identifiers(
          scheme TEXT NOT NULL,value TEXT NOT NULL,edition_id TEXT NOT NULL,PRIMARY KEY(scheme,value,edition_id));
        CREATE TABLE IF NOT EXISTS analyses(
          analysis_key TEXT PRIMARY KEY,edition_id TEXT,level TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(
          content_hash TEXT PRIMARY KEY,edition_id TEXT,work_id TEXT,rights TEXT NOT NULL,source_path TEXT,chars INTEGER NOT NULL,imported_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_identifiers_lookup ON identifiers(scheme,value);
        CREATE INDEX IF NOT EXISTS idx_editions_work ON editions(work_id);
        CREATE INDEX IF NOT EXISTS idx_editions_space ON editions(space_x,space_y);
        CREATE INDEX IF NOT EXISTS idx_works_title ON works(title);
        """)
        self._migrate()
        self.has_fts = self._ensure_search()
        self.db.commit()

    def _columns(self, table: str) -> set[str]:
        return {str(r["name"]) for r in self.db.execute(f"PRAGMA table_info({table})")}

    def _ensure_column(self, table: str, name: str, kind: str, default: str | None = None) -> None:
        if name in self._columns(table):
            return
        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}" + (f" DEFAULT {default}" if default else ""))

    def _migrate(self) -> None:
        for table, name, kind, default in [
            ("works","description","TEXT",None),("works","categories","TEXT","'[]'"),
            ("editions","cover_url","TEXT",None),("editions","table_of_contents","TEXT","'[]'"),
            ("editions","physical_format","TEXT",None),("editions","space_x","REAL",None),("editions","space_y","REAL",None),
        ]:
            self._ensure_column(table,name,kind,default)

    def _ensure_search(self) -> bool:
        try:
            self.db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
              edition_id UNINDEXED,work_id UNINDEXED,title,authors,subjects,publishers,categories,identifiers,
              language UNINDEXED,publish_date UNINDEXED,tokenize='unicode61 remove_diacritics 2')""")
            return True
        except sqlite3.OperationalError:
            self.db.execute("""CREATE TABLE IF NOT EXISTS search_index(
              edition_id TEXT PRIMARY KEY,work_id TEXT,title TEXT,authors TEXT,subjects TEXT,publishers TEXT,
              categories TEXT,identifiers TEXT,language TEXT,publish_date TEXT)""")
            return False

    def upsert_author(self, key: str, raw: dict) -> None:
        with self._lock:
            self.db.execute("INSERT INTO authors(id,name,raw_json) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,raw_json=excluded.raw_json", (key,str(raw.get("name") or ""),json.dumps(raw,ensure_ascii=False)))

    def upsert_work(self, key: str, raw: dict) -> None:
        authors=_author_ids(raw); subjects=[str(x) for x in (raw.get("subjects") or []) if isinstance(x,str)]
        description=text_value(raw.get("description")); title=str(raw.get("title") or ""); cats=classify(subjects,title,description or "")
        with self._lock:
            self.db.execute("""INSERT INTO works(id,title,subjects,authors,description,categories,raw_json) VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title,subjects=excluded.subjects,authors=excluded.authors,
            description=excluded.description,categories=excluded.categories,raw_json=excluded.raw_json""",
            (key,title,json.dumps(subjects,ensure_ascii=False),json.dumps(authors,ensure_ascii=False),description,json.dumps(cats,ensure_ascii=False),json.dumps(raw,ensure_ascii=False)))

    def upsert_edition(self, key: str, raw* *: dict) -> None:
        works=raw.get("works") or []; work_id=works[0].get("key") if works and isinstance(works[0],dict) else None
        langs=raw.get("languages") or []; language=(langs[0].get("key","").rsplit("/",1)[-1] if langs and isinstance(langs[0],dict) else None) or None
        ids: dict[str,list[str]]={}
        for scheme,field in {"isbn10":"isbn_10","isbn13":"isbn_13","lccn":"lccn","oclc":"oclc_numbers"}.items():
            values=[]
            for value in raw.get(field) or []:
                cleaned=compact(str(value)) if scheme.startswith("isbn") else str(value).strip()
                if cleaned: values.append(cleaned)
            if values: ids[scheme]=list(dict.fromkeys(values))
        if raw.get("ocaid"): ids["internet_archive"]=[str(raw["ocaid"]).strip()]
        valid13=[x for x in ids.get("isbn13",[]) if is_valid_isbn13(x)]
        point=isbn_space_point(valid13[0]) if valid13 else None; toc=toc_titles(raw.get("table_of_contents"))
        with self._lock:
            self.db.execute("""INSERT INTO editions(id,work_id,title,language,publishers,publish_date,page_count,cover_url,table_of_contents,physical_format,space_x,space_y,raw_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET work_id=excluded.work_id,title=excluded.title,language=excluded.language,
            publishers=excluded.publishers,publish_date=excluded.publish_date,page_count=excluded.page_count,cover_url=excluded.cover_url,
            table_of_contents=excluded.table_of_contents,physical_format=excluded.physical_format,space_x=excluded.space_x,space_y=excluded.space_y,raw_json=excluded.raw_json""",
            (key,work_id,str(raw.get("title") or ""),language,json.dumps([str(x) for x in raw.get("publishers") or []],ensure_ascii=False),raw.get("publish_date"),raw.get("number_of_pages") if isinstance(raw.get("number_of_pages"),int) else None,_cover_url(raw,valid13),json.dumps(toc,ensure_ascii=False),raw.get("physical_format"),point.x if point else None,point.y if point else None,json.dumps(raw,ensure_ascii=False)))
            self.db.execute("DELETE FROM identifiers WHERE edition_id=?",(key,))
            for scheme,values in ids.items():
                for value in values:self.db.execute("INSERT OR IGNORE INTO identifiers(scheme,value,edition_id) VALUES(?,?,?)",(scheme,value,key))
            if self.index_on_write:self._upsert_search(key)

    def _author_names(self, ids: Iterable[str]) -> list[str]:
        out=[]
        for aid in ids:
            row=self.db.execute("SELECT name FROM authors WHERE id=?",(aid,)).fetchone(); out.append(str(row["name"]) if row and row["name"] else aid.rsplit("/",1)[-1])
        return out

    def _search_doc(self, edition_id: str):
        row=self.db.execute("""SELECT e.id,e.work_id,e.title,e.language,e.publishers,e.publish_date,w.title work_title,w.subjects,w.authors,w.categories
        FROM editions e LEFT JOIN works w ON w.id=e.work_id WHERE e.id=?""",(edition_id,)).fetchone()
        if not row:return None
        authors=self._author_names(json.loads(row["authors"] or "[]")); subjects=json.loads(row["subjects"] or "[]"); cats=json.loads(row["categories"] or "[]"); pubs=json.loads(row["publishers"] or "[]")
        identifiers=[str(r["value"]) for r in self.db.execute("SELECT value FROM identifiers WHERE edition_id=? ORDER BY scheme,value",(edition_id,))]
        return (row["id"],row["work_id"] or "",row["work_title"] or row["title"] or ""," | ".join(authors)," | ".join(subjects)," | ".join(pubs)," | ".join(cats)," ".join(identifiers),row["language"] or "",row["publish_date"] or "")

    def _upsert_search(self, edition_id: str) -> None:
        doc=self._search_doc(edition_id)
        if not doc:return
        table="search_fts" if self.has_fts else "search_index"; self.db.execute(f"DELETE FROM {table} WHERE edition_id=?",(edition_id,)); self.db.execute(f"INSERT INTO {table}(edition_id,work_id,title,authors,subjects,publishers,categories,identifiers,language,publish_date) VALUES(?,?,?,?,?,?,?,?,?,?)",doc)

    def reindex(self, commit_every: int = 5000) -> dict[str,int]:
        with self._lock:
            table="search_fts" if self.has_fts else "search_index"; self.db.execute(f"DELETE FROM {table}"); processed=coordinates=0
            rows=self.db.execute("SELECT id,space_x,space_y FROM editions ORDER BY id").fetchall()
            for row in rows:
                if row["space_x"] is None or row["space_y"] is None:
                    isbn=self.db.execute("SELECT value FROM identifiers WHERE edition_id=? AND scheme='isbn13' LIMIT 1",(row["id"],)).fetchone()
                    if isbn and is_valid_isbn13(str(isbn["value"])):
                        p=isbn_space_point(str(isbn["value"])); self.db.execute("UPDATE editions SET space_x=?,space_y=? WHERE id=?",(p.x,p.y,row["id"])); coordinates+=1
                self._upsert_search(str(row["id"])); processed+=1
                if processed%commit_every==0:self.db.commit()
            self.db.commit(); return {"indexed":processed,"coordinates_updated":coordinates}

    def commit(self) -> None:
        with self._lock:self.db.commit()

    def _record(self, e: sqlite3.Row) -> BookRecord:
        raw_e=json.loads(e["raw_json"] or "{}"); ids={}
        for row in self.db.execute("SELECT scheme,value FROM identifiers WHERE edition_id=? ORDER BY scheme,value",(e["id"],)):ids.setdefault(str(row["scheme"]),[]).append(str(row["value"]))
        work=None; raw_w={}
        if e["work_id"]:
            w=self.db.execute("SELECT * FROM works WHERE id=?",(e["work_id"],)).fetchone()
            if w:
                raw_w=json.loads(w["raw_json"] or "{}"); names=self._author_names(json.loads(w["authors"] or "[]")); cats=json.loads(w["categories"] or "[]"); subjects=json.loads(w["subjects"] or "[]")
                work=Work(id=_wid(str(w["id"])),title=str(w["title"]),authors=names,subjects=subjects,description=w["description"],first_sentence=text_value(raw_w.get("first_sentence")),categories=cats,source_refs=[f"openlibrary:{w['id']}"])
        edition=Edition(id=_eid(str(e["id"])),work_id=_wid(str(e["work_id"])) if e["work_id"] else None,title=str(e["title"]),language=e["language"],publishers=json.loads(e["publishers"] or "[]"),publish_date=e["publish_date"],page_count=e["page_count"],identifiers=ids,cover_url=e["cover_url"],table_of_contents=json.loads(e["table_of_contents"] or "[]"),physical_format=e["physical_format"],source_refs=[f"openlibrary:{e['id']}"])
        evidence=openlibrary_evidence(raw_w,raw_e,f"openlibrary:{e['work_id']}" if e["work_id"] else None,f"openlibrary:{e['id']}")
        return BookRecord(work,edition,Analysis(level="L0",confidence=1.0,sources=edition.source_refs,warnings=["Loaded from local bibliographic metadata; no interpretation generated."]),[Provenance(source="Open Library dump",source_id=str(e["id"]),url=f"https://openlibrary.org{e['id']}")],evidence)

    def lookup_isbn(self, isbn13: str) -> BookRecord | None:
        with self._lock:
            row=self.db.execute("SELECT edition_id FROM identifiers WHERE scheme='isbn13' AND value=? LIMIT 1",(isbn13,)).fetchone()
            if not row:return None
            e=self.db.execute("SELECT * FROM editions WHERE id=?",(row["edition_id"],)).fetchone(); return self._record(e) if e else None

    @staticmethod
    def _fts_query(query: str) -> str:
        terms=re.findall(r"[\w\u3400-\u9fff]+",query,flags=re.UNICODE); return " AND ".join(f'"{term}"' for term in terms[:12])

    def _result(self,row,score=None):
        isbn=self.db.execute("SELECT value FROM identifiers WHERE edition_id=? AND scheme='isbn13' LIMIT 1",(row["edition_id"],)).fetchone(); cover=self.db.execute("SELECT cover_url FROM editions WHERE id=?",(row["edition_id"],)).fetchone()
        return {"edition_id":_eid(str(row["edition_id"])),"work_id":_wid(str(row["work_id"])) if row["work_id"] else None,"title":row["title"],"authors":[x.strip() for x in str(row["authors"] or "").split("|") if x.strip()],"subjects":[x.strip() for x in str(row["subjects"] or "").split("|") if x.strip()],"publishers":[x.strip() for x in str(row["publishers"] or "").split("|") if x.strip()],"categories":[x.strip() for x in str(row["categories"] or "").split("|") if x.strip()],"language":row["language"] or None,"publish_date":row["publish_date"] or None,"isbn":str(isbn["value"]) if isbn else None,"cover_url":str(cover["cover_url"]) if cover and cover["cover_url"] else None,"score":score,"source":"local"}

    def search(self, query: str, limit: int = 20, category: str | None = None, language: str | None = None, year_from: int | None = None, year_to: int | None = None) -> list[dict]:
        limit=max(1,min(int(limit),100)); query=query.strip()
        with self._lock:
            if self.has_fts and query:
                fts=self._fts_query(query)
                if fts:
                    clauses=["search_fts MATCH ?"]; params:list[object]=[fts]
                    if category:clauses.append("categories LIKE ?"); params.append(f"%{category}%")
                    if language:clauses.append("language=?"); params.append(language)
                    if year_from:clauses.append("CAST(substr(publish_date,1,4) AS INTEGER)>=?"); params.append(year_from)
                    if year_to:clauses.append("CAST(substr(publish_date,1,4) AS INTEGER)<=?"); params.append(year_to)
                    params.append(limit)
                    try:rows=self.db.execute("SELECT *,bm25(search_fts) rank FROM search_fts WHERE "+" AND ".join(clauses)+" ORDER BY rank LIMIT ?",params).fetchall()
                    except sqlite3.OperationalError:rows=[]
                    if rows:return [self._result(r,float(r["rank"])) for r in rows]
            terms=[x for x in re.split(r"\s+",query) if x]; clauses=["1=1"]; params=[]
            for term in terms[:6]:
                clauses.append("(e.title LIKE ? OR w.title LIKE ? OR w.subjects LIKE ? OR w.authors LIKE ? OR e.publishers LIKE ?)"); like=f"%{term}%"; params.extend([like]*5)
            if category:clauses.append("w.categories LIKE ?"); params.append(f"%{category}%")
            if language:clauses.append("e.language=?"); params.append(language)
            if year_from:clauses.append("CAST(substr(e.publish_date,1,4) AS INTEGER)>=?"); params.append(year_from)
            if year_to:clauses.append("CAST(substr(e.publish_date,1,4) AS INTEGER)<=?"); params.append(year_to)
            params.append(limit)
            rows=self.db.execute("SELECT e.id edition_id,e.work_id,COALESCE(w.title,e.title) title,w.authors author_ids,w.subjects,e.publishers,w.categories,e.language,e.publish_date FROM editions e LEFT JOIN works w ON w.id=e.work_id WHERE "+" AND ".join(clauses)+" ORDER BY e.publish_date DESC LIMIT ?",params).fetchall(); out=[]
            for r in rows:
                d=dict(r); d["authors"]=" | ".join(self._author_names(json.loads(r["author_ids"] or "[]"))); d["subjects"]=" | ".join(json.loads(r["subjects"] or "[]")); d["publishers"]=" | ".join(json.loads(r["publishers"] or "[]")); d["categories"]=" | ".join(json.loads(r["categories"] or "[]")); out.append(self._result(d))
            return out

    def related(self, work_id: str | None, subjects: list[str], limit: int = 12) -> list[dict]:
        out=[]; seen=set()
        for subject in subjects[:4]:
            for item in self.search(subject,limit=max(4,limit)):
                if item["work_id"]==work_id or item["edition_id"] in seen:continue
                seen.add(item["edition_id"]); out.append(item)
                if len(out)>=limit:return out
        return out

    def universe_points(self, limit: int = 2500, min_x: float = 0.0, max_x: float = 1.0, min_y: float = 0.0, max_y: float = 1.0, category: str | None = None, query: str | None = None) -> list[dict]:
        limit=max(1,min(int(limit),5000))
        with self._lock:
            clauses=["e.space_x IS NOT NULL","e.space_y IS NOT NULL","e.space_x BETWEEN ? AND ?","e.space_y BETWEEN ? AND ?"]; params:list[object]=[min_x,max_x,min_y,max_y]
            if category:clauses.append("w.categories LIKE ?"); params.append(f"%{category}%")
            if query:
                terms=[x for x in re.split(r"\s+",query.strip()) if x]
                for term in terms[:4]:clauses.append("(e.title LIKE ? OR w.title LIKE ? OR w.subjects LIKE ?)"); params.extend([f"%{term}%"]*3)
            params.append(limit)
            rows=self.db.execute("SELECT e.id,e.title,e.work_id,e.space_x,e.space_y,e.publish_date,w.categories FROM editions e LEFT JOIN works w ON w.id=e.work_id WHERE "+" AND ".join(clauses)+" ORDER BY e.space_x,e.space_y LIMIT ?",params).fetchall(); out=[]
            for row in rows:
                isbn=self.db.execute("SELECT value FROM identifiers WHERE edition_id=? AND scheme='isbn13' LIMIT 1",(row["id"],)).fetchone()
                if isbn:out.append({"edition_id":_eid(str(row["id"])),"work_id":_wid(str(row["work_id"])) if row["work_id"] else None,"title":row["title"],"isbn":str(isbn["value"]),"x":float(row["space_x"]),"y":float(row["space_y"]),"publish_date":row["publish_date"],"categories":json.loads(row["categories"] or "[]")})
            return out

    def store_analysis(self, key: str, edition_id: str | None, analysis: Analysis) -> None:
        with self._lock:
            self.db.execute("INSERT INTO analyses(analysis_key,edition_id,level,payload_json,created_at) VALUES(?,?,?,?,?) ON CONFLICT(analysis_key) DO UPDATE SET edition_id=excluded.edition_id,level=excluded.level,payload_json=excluded.payload_json,created_at=excluded.created_at",(key,edition_id,analysis.level,json.dumps(asdict(analysis),ensure_ascii=False),_now())); self.db.commit()

    def record_document(self, content_hash: str, edition_id: str | None, work_id: str | None, rights: str, source_path: str | None, chars: int) -> None:
        with self._lock:
            self.db.execute("INSERT INTO documents(content_hash,edition_id,work_id,rights,source_path,chars,imported_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(content_hash) DO UPDATE SET edition_id=excluded.edition_id,work_id=excluded.work_id,rights=excluded.rights,source_path=excluded.source_path,chars=excluded.chars",(content_hash,edition_id,work_id,rights,source_path,chars,_now())); self.db.commit()

    def stats(self) -> dict[str,int]:
        with self._lock:return {name:int(self.db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]) for name in ("works","editions","authors","identifiers","analyses","documents")}

    def close(self) -> None:
        with self._lock:self.db.close()

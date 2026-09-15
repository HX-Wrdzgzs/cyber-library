from __future__ import annotations

import hashlib
from pathlib import Path

from .cache import JsonCache
from .content import ContentDocument, RIGHTS_VALUES
from .database import CatalogDB
from .graph import build_knowledge_graph
from .identifiers import normalize_isbn
from .intelligence import analyze_record, full_text_analysis
from .llm import LLMClient
from .models import Analysis, BookRecord, Edition, Provenance, Work
from .scale import MAX_TILE_LEVEL, query_universe_tiles
from .semantic import EmbeddingClient, EmbeddingError, embedding_count, hybrid_search
from .sources.openlibrary import NotFound, OpenLibraryClient
from .taxonomy import categories as all_categories
from .universe import isbn_space_point, space_metadata


class CatalogService:
    def __init__(self, cache_path: str | Path = ".cyber-library/cache.sqlite3", contact: str | None = None, catalog_db_path: str | Path | None = None, live_fallback: bool = True, use_llm: bool = True) -> None:
        self.cache = JsonCache(cache_path)
        self.openlibrary = OpenLibraryClient(self.cache, contact)
        self.catalog = CatalogDB(catalog_db_path) if catalog_db_path else None
        self.live_fallback = live_fallback
        self.llm = LLMClient.from_env() if use_llm else None
        self.embedding = EmbeddingClient.from_env()

    @staticmethod
    def _analysis_mode(value: bool | str | None) -> str:
        if value is True: return "auto"
        if value in (False, None): return "none"
        text = str(value).strip().lower()
        if text in {"1","true","yes","on"}: return "auto"
        if text in {"0","false","no","off"}: return "none"
        return text

    def resolve_isbn(self, isbn: str, analyze: bool | str = False) -> BookRecord:
        isbn13 = normalize_isbn(isbn)
        record = self.catalog.lookup_isbn(isbn13) if self.catalog else None
        if record is None:
            if not self.live_fallback: raise NotFound(isbn13)
            record = self.openlibrary.lookup_isbn(isbn13)
        mode = self._analysis_mode(analyze)
        if mode != "none": record.analysis = analyze_record(record, self.llm, mode)
        return record

    def search(self, query: str, limit: int = 20, category: str | None = None, language: str | None = None, year_from: int | None = None, year_to: int | None = None) -> list[dict]:
        lexical=[]
        if self.catalog:
            lexical=self.catalog.search(query,limit=max(limit * 2, 30),category=category,language=language,year_from=year_from,year_to=year_to)
            if self.embedding and embedding_count(self.catalog, self.embedding.model_name) > 0:
                try:
                    hybrid=hybrid_search(
                        self.catalog,
                        self.embedding,
                        query,
                        lexical,
                        limit=limit,
                        category=category,
                        language=language,
                        year_from=year_from,
                        year_to=year_to,
                    )
                    if hybrid:
                        return hybrid
                except EmbeddingError:
                    pass
        if lexical or not self.live_fallback:return lexical[:limit]
        live=self.openlibrary.search_books(query,limit)
        if category: live=[item for item in live if category in item.get("categories",[])]
        if language: live=[item for item in live if item.get("language")==language]
        if year_from: live=[item for item in live if item.get("publish_date") and str(item["publish_date"])[:4].isdigit() and int(str(item["publish_date"])[:4])>=year_from]
        if year_to: live=[item for item in live if item.get("publish_date") and str(item["publish_date"])[:4].isdigit() and int(str(item["publish_date"])[:4])<=year_to]
        return live[:limit]

    def graph(self, isbn: str) -> dict:
        record=self.resolve_isbn(isbn,analyze="auto"); related=[]
        if self.catalog and record.work: related=self.catalog.related(record.work.id,record.work.subjects,16)
        return build_knowledge_graph(record,related)

    def universe(self, limit:int=2500, min_x:float=0.0, max_x:float=1.0, min_y:float=0.0, max_y:float=1.0, category:str|None=None, query:str|None=None, zoom_level:int|None=None) -> dict:
        if self.catalog:
            if not category and not query and zoom_level is not None and zoom_level <= MAX_TILE_LEVEL:
                tiles=query_universe_tiles(self.catalog,level=zoom_level,min_x=min_x,max_x=max_x,min_y=min_y,max_y=max_y,limit=limit)
                if tiles:
                    return {"space":space_metadata(),"mode":"tiles","zoom_level":zoom_level,"tiles":tiles,"points":[]}
            points=self.catalog.universe_points(limit=limit,min_x=min_x,max_x=max_x,min_y=min_y,max_y=max_y,category=category,query=query)
        elif query and self.live_fallback:
            points=[]
            for item in self.openlibrary.search_books(query,min(limit,50)):
                isbn=item.get("isbn")
                if not isbn: continue
                try: point=isbn_space_point(isbn)
                except Exception: continue
                points.append({"edition_id":item.get("edition_id"),"work_id":item.get("work_id"),"title":item.get("title"),"isbn":point.isbn13,"x":point.x,"y":point.y,"publish_date":item.get("publish_date"),"categories":item.get("categories") or []})
        else: points=[]
        return {"space":space_metadata(),"mode":"points","zoom_level":zoom_level,"tiles":[],"points":points}

    def analyze_text(self, text:str, rights:str, title:str|None=None, isbn:str|None=None, headings:list[str]|None=None, source_ref:str|None=None, source_path:str|None=None) -> BookRecord:
        if rights not in RIGHTS_VALUES: raise ValueError("invalid rights value")
        text=text.strip()
        if len(text)<100: raise ValueError("text is too short for full-text analysis")
        content_hash="sha256:"+hashlib.sha256(text.encode("utf-8")).hexdigest()
        if isbn: record=self.resolve_isbn(isbn,analyze=False)
        else:
            seed=content_hash.split(":",1)[1][:20]; book_title=title or "Local document"
            work=Work(id=f"local:work:{seed}",title=book_title,authors=[],subjects=[],source_refs=[f"local:{content_hash}"])
            edition=Edition(id=f"local:edition:{seed}",work_id=work.id,title=book_title,identifiers={"content_hash":[content_hash]},source_refs=[f"local:{content_hash}"])
            record=BookRecord(work=work,edition=edition,analysis=Analysis(level="L0"),provenance=[Provenance(source="Local content",source_id=content_hash,url=source_path,license=rights)])
        ref=source_ref or f"content:{content_hash}"
        record.analysis=full_text_analysis(record,text,headings or [],rights,ref,self.llm)
        if self.catalog:
            self.catalog.record_document(content_hash=content_hash,edition_id=record.edition.id,work_id=record.work.id if record.work else None,rights=rights,source_path=source_path,chars=len(text))
            self.catalog.store_analysis(f"{record.edition.id}:{content_hash}",record.edition.id,record.analysis)
        return record

    def analyze_document(self, document: ContentDocument, isbn: str | None = None) -> BookRecord:
        return self.analyze_text(text=document.text,rights=document.rights,title=document.title,isbn=isbn,headings=document.headings,source_ref=f"file:{document.content_hash}",source_path=document.source_path)

    def categories(self) -> list[str]: return all_categories()

    def stats(self) -> dict[str, int | bool | str | None]:
        result = self.catalog.stats() if self.catalog else {"works":0,"editions":0,"authors":0,"identifiers":0,"analyses":0,"documents":0}
        result["local_catalog"]=bool(self.catalog); result["live_fallback"]=self.live_fallback; result["llm_enabled"]=self.llm is not None; result["llm_model"]=self.llm.model_name if self.llm else None
        result["embedding_enabled"]=self.embedding is not None; result["embedding_model"]=self.embedding.model_name if self.embedding else None
        result["embedding_indexed"]=embedding_count(self.catalog,self.embedding.model_name) if self.catalog and self.embedding else 0
        return result

    def close(self) -> None:
        if self.catalog:self.catalog.close()
        self.cache.close()

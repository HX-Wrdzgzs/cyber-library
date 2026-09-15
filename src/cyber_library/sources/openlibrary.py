from __future__ import annotations
import json, os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from ..cache import JsonCache
from ..identifiers import normalize_isbn
from ..models import Analysis, BookRecord, Edition, Provenance, Work

BASE="https://openlibrary.org"
class SourceError(RuntimeError): pass
class NotFound(SourceError): pass

class OpenLibraryClient:
    """Low-volume, user-triggered Open Library lookup client. Use data dumps for bulk ingestion."""
    def __init__(self, cache: JsonCache|None=None, contact: str|None=None, timeout: float=10.0)->None:
        self.cache=cache; self.timeout=timeout
        contact=contact or os.getenv("CYBER_LIBRARY_CONTACT","")
        self.user_agent="CyberLibrary/0.1.0"+(f" ({contact})" if contact else "")
    def _get_json(self,url:str,key:str)->dict:
        if self.cache:
            hit=self.cache.get(key)
            if hit is not None: return hit
        req=Request(url,headers={"Accept":"application/json","User-Agent":self.user_agent})
        try:
            with urlopen(req,timeout=self.timeout) as resp: data=json.load(resp)
        except HTTPError as exc:
            if exc.code==404: raise NotFound(url) from exc
            raise SourceError(f"Open Library HTTP {exc.code}") from exc
        except (URLError,TimeoutError,json.JSONDecodeError) as exc:
            raise SourceError(f"Open Library request failed: {exc}") from exc
        if self.cache: self.cache.set(key,data)
        return data
    def lookup_isbn(self,isbn:str)->BookRecord:
        isbn13=normalize_isbn(isbn)
        eraw=self._get_json(f"{BASE}/isbn/{isbn13}.json",f"ol:isbn:{isbn13}")
        ekey=str(eraw.get("key") or f"/isbn/{isbn13}"); eid=ekey.rsplit("/",1)[-1]
        works=eraw.get("works") or []; wkey=works[0].get("key") if works and isinstance(works[0],dict) else None
        wraw=self._get_json(f"{BASE}{wkey}.json",f"ol:work:{wkey}") if wkey else None
        language=None
        langs=eraw.get("languages") or []
        if langs and isinstance(langs[0],dict): language=str(langs[0].get("key","")).rsplit("/",1)[-1] or None
        work=None; wid=None
        if wraw is not None and wkey:
            wid=wkey.rsplit("/",1)[-1]
            work=Work(id=f"openlibrary:work:{wid}",title=str(wraw.get("title") or eraw.get("title") or ""),
                      subjects=[str(x) for x in (wraw.get("subjects") or []) if isinstance(x,str)],
                      source_refs=[f"openlibrary:{wkey}"])
        ids={"isbn13":[isbn13]}
        if eraw.get("isbn_10"): ids["isbn10"]=[str(x) for x in eraw["isbn_10"]]
        if eraw.get("isbn_13"): ids["isbn13"]=[str(x) for x in eraw["isbn_13"]]
        edition=Edition(id=f"openlibrary:edition:{eid}",work_id=f"openlibrary:work:{wid}" if wid else None,
            title=str(eraw.get("title") or ""),language=language,publishers=[str(x) for x in (eraw.get("publishers") or [])],
            publish_date=eraw.get("publish_date"),page_count=eraw.get("number_of_pages"),identifiers=ids,
            cover_url=f"https://covers.openlibrary.org/b/isbn/{isbn13}-L.jpg?default=false",
            source_refs=[f"openlibrary:{ekey}"])
        sources=[f"openlibrary:{ekey}"]+([f"openlibrary:{wkey}"] if wkey else [])
        return BookRecord(work=work,edition=edition,
            analysis=Analysis(level="L0",confidence=1.0,sources=sources,warnings=["No AI interpretation has been generated for this record."]),
            provenance=[Provenance(source="Open Library",source_id=eid,url=f"{BASE}{ekey}",retrieved_at=datetime.now(timezone.utc).isoformat())])

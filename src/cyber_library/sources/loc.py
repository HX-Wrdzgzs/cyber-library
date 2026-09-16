from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..cache import JsonCache
from ..identifiers import compact, normalize_isbn
from .base import ExternalSourceError, SourceMatch

DEFAULT_LCDB = "http://lx2.loc.gov:210/LCDB"
DEFAULT_NAF = "http://lx2.loc.gov:210/NAF"


class LibraryOfCongressError(ExternalSourceError):
    pass


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _subfields(record: ET.Element, tag: str, code: str | None = None) -> list[str]:
    out: list[str] = []
    for field in record.iter():
        if _local(field.tag) != "datafield" or field.attrib.get("tag") != tag:
            continue
        for child in field:
            if _local(child.tag) != "subfield":
                continue
            if code is not None and child.attrib.get("code") != code:
                continue
            text = (child.text or "").strip()
            if text:
                out.append(text)
    return out


def _control(record: ET.Element, tag: str) -> str | None:
    for field in record.iter():
        if _local(field.tag) == "controlfield" and field.attrib.get("tag") == tag:
            text = (field.text or "").strip()
            if text:
                return text
    return None


def _isbn_tokens(value: str) -> list[str]:
    out=[]
    for token in re.findall(r"(?<!\d)(?:97[89][\d -]{10,20}|[\dXx][\dXx -]{8,16})(?!\d)", value):
        cleaned=compact(token)
        if len(cleaned) in {10,13}: out.append(cleaned)
    return out


class LibraryOfCongressAdapter:
    name = "loc"

    def __init__(self, cache: JsonCache | None = None, contact: str | None = None, lcdb_url: str | None = None, naf_url: str | None = None, timeout: float = 25.0) -> None:
        self.cache = cache
        self.contact = (contact or os.getenv("CYBER_LIBRARY_CONTACT", "")).strip()
        self.lcdb_url = (lcdb_url or os.getenv("CYBER_LIBRARY_LOC_LCDB_URL", DEFAULT_LCDB)).rstrip("?")
        self.naf_url = (naf_url or os.getenv("CYBER_LIBRARY_LOC_NAF_URL", DEFAULT_NAF)).rstrip("?")
        self.timeout = timeout

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("isbn-reconciliation", "authority-author-search", "national-library", "lc-sru")

    def health(self) -> dict[str, object]:
        return {"name": self.name, "configured": bool(self.lcdb_url and self.naf_url), "catalog_endpoint": self.lcdb_url, "authority_endpoint": self.naf_url, "capabilities": list(self.capabilities)}

    def _get_xml(self, base: str, params: dict[str, str], cache_key: str) -> ET.Element:
        if self.cache:
            cached = self.cache.get(cache_key)
            if isinstance(cached, dict) and isinstance(cached.get("xml"), str):
                try: return ET.fromstring(cached["xml"])
                except ET.ParseError: pass
        request = Request(base + "?" + urlencode(params), headers={"Accept":"application/xml,text/xml;q=0.9,*/*;q=0.1","User-Agent":"CyberLibrary/3.0 (+https://github.com/HX-Wrdzgzs/cyber-library)" + (f" ({self.contact})" if self.contact else "")})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = ""
            try: detail = exc.read(1600).decode("utf-8", "replace")
            except Exception: pass
            raise LibraryOfCongressError(f"Library of Congress SRU HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError) as exc:
            raise LibraryOfCongressError(f"Library of Congress SRU request failed: {exc}") from exc
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise LibraryOfCongressError(f"Library of Congress returned invalid XML: {exc}") from exc
        if self.cache:
            self.cache.set(cache_key, {"xml": raw.decode("utf-8", "replace")})
        return root

    @staticmethod
    def _record_payloads(root: ET.Element) -> list[ET.Element]:
        out=[]
        for element in root.iter():
            if _local(element.tag) != "recordData": continue
            for child in element:
                if isinstance(child.tag, str):
                    out.append(child); break
        return out

    def reconcile_isbn(self, isbn: str) -> list[SourceMatch]:
        isbn13 = normalize_isbn(isbn)
        root = self._get_xml(self.lcdb_url, {"operation":"searchRetrieve","version":"1.1","query":f'bath.isbn="{isbn13}"',"maximumRecords":"10","recordSchema":"marcxml"}, f"loc:isbn:{isbn13}")
        matches=[]; seen=set()
        for record in self._record_payloads(root):
            isbn_values=[]
            for value in _subfields(record,"020","a"): isbn_values.extend(_isbn_tokens(value))
            normalized=[]
            for value in isbn_values:
                try: normalized.append(normalize_isbn(value))
                except Exception: pass
            if isbn13 not in normalized: continue
            lccn = (_subfields(record,"010","a") or [None])[0]
            if lccn: lccn = re.sub(r"[\s-]+", "", lccn)
            control = _control(record,"001")
            source_id = lccn or control or hashlib.sha256(ET.tostring(record)).hexdigest()[:24]
            if source_id in seen: continue
            seen.add(source_id)
            title_parts = _subfields(record,"245","a") + _subfields(record,"245","b")
            title = " ".join(x.rstrip(" /:;") for x in title_parts).strip() or None
            authors = [x.rstrip(" ,/") for x in (_subfields(record,"100","a") + _subfields(record,"700","a"))]
            publishers = [x.rstrip(" ,;") for x in (_subfields(record,"264","b") + _subfields(record,"260","b"))]
            dates = [x.rstrip(" .") for x in (_subfields(record,"264","c") + _subfields(record,"260","c"))]
            identifiers={"isbn13":[isbn13]}
            if lccn: identifiers["lccn"]=[lccn]
            matches.append(SourceMatch(source=self.name, source_id=source_id, url=f"https://lccn.loc.gov/{lccn}" if lccn else None, label=title, description="Library of Congress bibliographic record", confidence=1.0, identifiers=identifiers, metadata={"authors":authors,"publishers":publishers,"dates":dates,"control_number":control}))
        return matches

    def reconcile_author(self, name: str, limit: int = 20) -> list[SourceMatch]:
        name = " ".join(name.split()).strip()
        if not name: return []
        limit=max(1,min(int(limit),50))
        root=self._get_xml(self.naf_url,{"operation":"searchRetrieve","version":"1.1","query":f'bath.personalName="{name}"',"maximumRecords":str(limit),"recordSchema":"mads"},f"loc:authority:{name.casefold()}:{limit}")
        matches=[]; seen=set()
        for idx,record in enumerate(self._record_payloads(root),1):
            label_parts=[]; identifiers={}
            for element in record.iter():
                local=_local(element.tag); text=(element.text or "").strip()
                if not text: continue
                if local=="namePart": label_parts.append(text)
                elif local in {"recordIdentifier","identifier"}:
                    kind=(element.attrib.get("type") or "lccn").lower(); identifiers.setdefault(kind,[]).append(text)
            label=" ".join(dict.fromkeys(label_parts)).strip() or None
            identifier = next((v for values in identifiers.values() for v in values if v), None)
            source_id = identifier or f"naf-{hashlib.sha256((label or name+str(idx)).encode()).hexdigest()[:20]}"
            if source_id in seen: continue
            seen.add(source_id)
            matches.append(SourceMatch(source=self.name,source_id=source_id,url=f"https://id.loc.gov/authorities/names/{source_id}.html" if source_id.startswith("n") else None,label=label,description="Library of Congress Name Authority File candidate",confidence=0.75,identifiers=identifiers,metadata={"query":name,"auto_merge":False,"candidate_only":True}))
        return matches[:limit]

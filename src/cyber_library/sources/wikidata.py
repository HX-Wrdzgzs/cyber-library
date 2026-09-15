from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..cache import JsonCache
from ..identifiers import compact, is_valid_isbn10, normalize_isbn
from .base import ExternalSourceError, SourceMatch

DEFAULT_ENDPOINT = "https://query.wikidata.org/sparql"


class WikidataError(ExternalSourceError):
    pass


def _literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


class WikidataAdapter:
    name = "wikidata"

    def __init__(self, cache: JsonCache | None = None, contact: str | None = None, endpoint: str | None = None, timeout: float = 25.0) -> None:
        self.cache = cache
        self.contact = (contact or os.getenv("CYBER_LIBRARY_CONTACT", "")).strip()
        self.endpoint = (endpoint or os.getenv("CYBER_LIBRARY_WIKIDATA_SPARQL_URL", DEFAULT_ENDPOINT)).strip()
        self.timeout = timeout

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("isbn-reconciliation", "entity-linking", "authority-author-search")

    def health(self) -> dict[str, object]:
        return {"name": self.name, "configured": bool(self.endpoint), "endpoint": self.endpoint, "capabilities": list(self.capabilities)}

    def _query(self, sparql: str, cache_key: str) -> dict:
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        query = urlencode({"query": sparql, "format": "json"})
        request = Request(
            f"{self.endpoint}?{query}",
            headers={"Accept": "application/sparql-results+json", "User-Agent": "CyberLibrary/2.1 (+https://github.com/HX-Wrdzgzs/cyber-library)" + (f" ({self.contact})" if self.contact else "")},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except HTTPError as exc:
            detail = ""
            try: detail = exc.read(1600).decode("utf-8", "replace")
            except Exception: pass
            raise WikidataError(f"Wikidata HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise WikidataError(f"Wikidata request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise WikidataError("Wikidata returned a non-object response")
        if self.cache:
            self.cache.set(cache_key, payload)
        return payload

    @staticmethod
    def _binding_value(binding: dict, key: str) -> str | None:
        value = binding.get(key)
        if not isinstance(value, dict): return None
        text = value.get("value")
        return str(text) if text is not None else None

    def reconcile_isbn(self, isbn: str) -> list[SourceMatch]:
        raw = compact(isbn); isbn13 = normalize_isbn(isbn); isbn10 = raw if is_valid_isbn10(raw) else None
        branches = ["{ ?item wdt:P212 ?matched . " f'FILTER(REPLACE(UCASE(STR(?matched)), "-", "") = "{isbn13}") }}']
        if isbn10:
            branches.append("{ ?item wdt:P957 ?matched . " f'FILTER(REPLACE(UCASE(STR(?matched)), "-", "") = "{isbn10}") }}')
        sparql = f'''SELECT DISTINCT ?item ?itemLabel ?itemDescription ?isbn13 ?isbn10 WHERE {{
  {" UNION ".join(branches)}
  OPTIONAL {{ ?item wdt:P212 ?isbn13. }}
  OPTIONAL {{ ?item wdt:P957 ?isbn10. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
LIMIT 10'''
        payload = self._query(sparql, f"wikidata:isbn:{isbn13}:{isbn10 or ''}")
        bindings = payload.get("results", {}).get("bindings", []) if isinstance(payload.get("results"), dict) else []
        if not isinstance(bindings, list): return []
        matches=[]; seen=set()
        for binding in bindings:
            if not isinstance(binding, dict): continue
            item_url=self._binding_value(binding,"item")
            if not item_url: continue
            qid=item_url.rstrip("/").rsplit("/",1)[-1]
            if not qid.startswith("Q") or not qid[1:].isdigit() or qid in seen: continue
            seen.add(qid); identifiers={"wikidata":[qid]}
            value13=self._binding_value(binding,"isbn13"); value10=self._binding_value(binding,"isbn10")
            if value13: identifiers["isbn13"]=[compact(value13)]
            if value10: identifiers["isbn10"]=[compact(value10)]
            matches.append(SourceMatch(source=self.name,source_id=qid,url=f"https://www.wikidata.org/wiki/{qid}",label=self._binding_value(binding,"itemLabel"),description=self._binding_value(binding,"itemDescription"),confidence=1.0,identifiers=identifiers,metadata={"matched_isbn13":isbn13,"matched_isbn10":isbn10}))
        return matches

    def reconcile_author(self, name: str, limit: int = 20) -> list[SourceMatch]:
        """Return exact-label author authority candidates without auto-merging them."""
        name = name.strip()
        if not name:
            return []
        limit = max(1, min(int(limit), 50))
        escaped = _literal(name)
        sparql = f'''SELECT DISTINCT ?item ?itemLabel ?itemDescription ?isni ?viaf ?lcnaf ?gnd WHERE {{
  ?item rdfs:label ?candidateLabel .
  FILTER(LCASE(STR(?candidateLabel)) = LCASE("{escaped}"))
  FILTER(LANG(?candidateLabel) IN ("en","zh","zh-cn","zh-hans","zh-hant","ja",""))
  OPTIONAL {{ ?item wdt:P213 ?isni. }}
  OPTIONAL {{ ?item wdt:P214 ?viaf. }}
  OPTIONAL {{ ?item wdt:P244 ?lcnaf. }}
  OPTIONAL {{ ?item wdt:P227 ?gnd. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en,ja". }}
}}
LIMIT {limit}'''
        payload = self._query(sparql, f"wikidata:authority:author:{name.casefold()}:{limit}")
        bindings = payload.get("results", {}).get("bindings", []) if isinstance(payload.get("results"), dict) else []
        if not isinstance(bindings, list): return []
        matches=[]; seen=set()
        for binding in bindings:
            if not isinstance(binding, dict): continue
            item_url=self._binding_value(binding,"item")
            if not item_url: continue
            qid=item_url.rstrip("/").rsplit("/",1)[-1]
            if not qid.startswith("Q") or not qid[1:].isdigit() or qid in seen: continue
            seen.add(qid)
            identifiers={"wikidata":[qid]}
            for field,scheme in (("isni","isni"),("viaf","viaf"),("lcnaf","lcnaf"),("gnd","gnd")):
                value=self._binding_value(binding,field)
                if value: identifiers[scheme]=[value]
            authority_count=sum(1 for key in ("isni","viaf","lcnaf","gnd") if key in identifiers)
            matches.append(SourceMatch(source=self.name,source_id=qid,url=f"https://www.wikidata.org/wiki/{qid}",label=self._binding_value(binding,"itemLabel") or name,description=self._binding_value(binding,"itemDescription"),confidence=0.95 if authority_count else 0.8,identifiers=identifiers,metadata={"authority_identifiers":authority_count,"auto_merge":False}))
        return matches

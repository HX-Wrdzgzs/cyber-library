from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .identifiers import InvalidISBN
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError


def _int(value: str | None, default: int | None = None) -> int | None:
    if value in (None, ""):
        return default
    return int(value)


def _float(value: str | None, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)


class Handler(BaseHTTPRequestHandler):
    server_version = "CyberLibraryHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/api/health":
            return self._json({"ok": True, "service": "cyber-library", "version": __version__, "stats": self.server.catalog.stats()})
        if parsed.path == "/api/stats":
            return self._json(self.server.catalog.stats())
        if parsed.path == "/api/categories":
            return self._json({"categories": self.server.catalog.categories()})
        if parsed.path == "/api/resolve":
            isbn = (query.get("isbn") or [""])[0]
            mode = (query.get("analysis") or query.get("analyze") or ["auto"])[0]
            if not isbn:
                return self._json({"error": "missing_isbn"}, HTTPStatus.BAD_REQUEST)
            try:
                record = self.server.catalog.resolve_isbn(isbn, analyze=mode)
            except InvalidISBN as exc:
                return self._json({"error": "invalid_isbn", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            except NotFound:
                return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except SourceError as exc:
                return self._json({"error": "upstream_error", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
            except ValueError as exc:
                return self._json({"error": "invalid_analysis_mode", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            return self._json(record.to_dict())
        if parsed.path == "/api/search":
            text = (query.get("q") or [""])[0].strip()
            if not text:
                return self._json({"error": "missing_query"}, HTTPStatus.BAD_REQUEST)
            try:
                limit = max(1, min(_int((query.get("limit") or ["20"])[0], 20) or 20, 100))
                results = self.server.catalog.search(text, limit=limit, category=(query.get("category") or [None])[0] or None, language=(query.get("language") or [None])[0] or None, year_from=_int((query.get("year_from") or [None])[0]), year_to=_int((query.get("year_to") or [None])[0]))
            except (ValueError, SourceError) as exc:
                return self._json({"error": "search_failed", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return self._json({"query": text, "results": results})
        if parsed.path == "/api/graph":
            isbn = (query.get("isbn") or [""])[0]
            if not isbn:
                return self._json({"error": "missing_isbn"}, HTTPStatus.BAD_REQUEST)
            try:
                return self._json(self.server.catalog.graph(isbn))
            except InvalidISBN as exc:
                return self._json({"error": "invalid_isbn", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            except NotFound:
                return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except SourceError as exc:
                return self._json({"error": "upstream_error", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
        if parsed.path == "/api/universe":
            try:
                payload = self.server.catalog.universe(limit=max(1, min(_int((query.get("limit") or ["2500"])[0], 2500) or 2500, 5000)), min_x=max(0.0, min(1.0, _float((query.get("min_x") or [None])[0], 0.0))), max_x=max(0.0, min(1.0, _float((query.get("max_x") or [None])[0], 1.0))), min_y=max(0.0, min(1.0, _float((query.get("min_y") or [None])[0], 0.0))), max_y=max(0.0, min(1.0, _float((query.get("max_y") or [None])[0], 1.0))), category=(query.get("category") or [None])[0] or None, query=(query.get("q") or [None])[0] or None)
            except (ValueError, SourceError) as exc:
                return self._json({"error": "universe_failed", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            return self._json(payload)
        if parsed.path.startswith("/api/"):
            return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        return self._static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze-text":
            return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        length = _int(self.headers.get("Content-Length"), 0) or 0
        if length <= 0:
            return self._json({"error": "empty_body"}, HTTPStatus.BAD_REQUEST)
        if length > 16 * 1024 * 1024:
            return self._json({"error": "payload_too_large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict):
            return self._json({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
        text = payload.get("text"); rights = payload.get("rights")
        if not isinstance(text, str) or not text.strip():
            return self._json({"error": "missing_text"}, HTTPStatus.BAD_REQUEST)
        if not isinstance(rights, str):
            return self._json({"error": "missing_rights"}, HTTPStatus.BAD_REQUEST)
        headings = payload.get("headings")
        if headings is not None and not (isinstance(headings, list) and all(isinstance(x, str) for x in headings)):
            return self._json({"error": "invalid_headings"}, HTTPStatus.BAD_REQUEST)
        try:
            record = self.server.catalog.analyze_text(text=text, rights=rights, title=payload.get("title") if isinstance(payload.get("title"), str) else None, isbn=payload.get("isbn") if isinstance(payload.get("isbn"), str) else None, headings=headings or [], source_ref="api:user-provided")
        except (ValueError, InvalidISBN) as exc:
            return self._json({"error": "analysis_failed", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
        except (NotFound, SourceError) as exc:
            return self._json({"error": "analysis_source_failed", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
        return self._json(record.to_dict())

    def _json(self, payload, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(int(status)); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(body)

    def _static(self, request_path: str) -> None:
        root = self.server.web_root
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        target = (root / relative).resolve()
        if target != root and root not in target.parents:
            return self._json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
        if not target.is_file():
            return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        body = target.read_bytes(); content_type, _ = mimetypes.guess_type(target.name)
        self.send_response(200); self.send_header("Content-Type", content_type or "application/octet-stream"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-cache"); self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print("[web] " + fmt % args)


def serve(host: str = "127.0.0.1", port: int = 8080, web_root: str = "web", cache_path: str = ".cyber-library/cache.sqlite3", contact: str | None = None, catalog_db_path: str | None = None, live_fallback: bool = True, use_llm: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    server.web_root = Path(web_root).resolve()
    server.catalog = CatalogService(cache_path, contact, catalog_db_path, live_fallback, use_llm=use_llm)
    print(f"Cyber Library: http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.catalog.close(); server.server_close()

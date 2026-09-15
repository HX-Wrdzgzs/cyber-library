from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .identifiers import InvalidISBN
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._json({"ok": True, "service": "cyber-library", "version": "0.1.0"})
        if parsed.path == "/api/stats":
            return self._json(self.server.catalog.stats())
        if parsed.path == "/api/resolve":
            query = parse_qs(parsed.query)
            isbn = (query.get("isbn") or [""])[0]
            analyze = (query.get("analyze") or ["1"])[0].lower() not in {"0", "false", "no"}
            if not isbn:
                return self._json({"error": "missing_isbn"}, HTTPStatus.BAD_REQUEST)
            try:
                record = self.server.catalog.resolve_isbn(isbn, analyze=analyze)
            except InvalidISBN as exc:
                return self._json({"error": "invalid_isbn", "detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            except NotFound:
                return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except SourceError as exc:
                return self._json({"error": "upstream_error", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return self._json(record.to_dict())
        if parsed.path == "/":
            return self._file("index.html")
        if parsed.path in {"/app.js", "/styles.css"}:
            return self._file(parsed.path[1:])
        return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def _json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, name):
        path = self.server.web_root / name
        if not path.is_file():
            return self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        body = path.read_bytes()
        content_type, _ = mimetypes.guess_type(path.name)
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[web] " + fmt % args)


def serve(
    host="127.0.0.1",
    port=8080,
    web_root="web",
    cache_path=".cyber-library/cache.sqlite3",
    contact=None,
    catalog_db_path=None,
    live_fallback=True,
):
    server = ThreadingHTTPServer((host, port), Handler)
    server.web_root = Path(web_root).resolve()
    server.catalog = CatalogService(cache_path, contact, catalog_db_path, live_fallback)
    print(f"Cyber Library: http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.catalog.close()
        server.server_close()

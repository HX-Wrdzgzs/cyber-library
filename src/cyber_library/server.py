from __future__ import annotations
import json, mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .identifiers import InvalidISBN
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p=urlparse(self.path)
        if p.path=="/api/health": return self._json({"ok":True,"service":"cyber-library","version":"0.1.0"})
        if p.path=="/api/resolve":
            q=parse_qs(p.query); isbn=(q.get("isbn") or [""])[0]; analyze=(q.get("analyze") or ["1"])[0] not in {"0","false","no"}
            if not isbn: return self._json({"error":"missing_isbn"},HTTPStatus.BAD_REQUEST)
            try: rec=self.server.catalog.resolve_isbn(isbn,analyze=analyze)
            except InvalidISBN as e: return self._json({"error":"invalid_isbn","detail":str(e)},HTTPStatus.BAD_REQUEST)
            except NotFound: return self._json({"error":"not_found"},HTTPStatus.NOT_FOUND)
            except SourceError as e: return self._json({"error":"upstream_error","detail":str(e)},HTTPStatus.BAD_GATEWAY)
            return self._json(rec.to_dict())
        if p.path=="/": return self._file("index.html")
        if p.path in {"/app.js","/styles.css"}: return self._file(p.path[1:])
        return self._json({"error":"not_found"},HTTPStatus.NOT_FOUND)
    def _json(self,payload,status=HTTPStatus.OK):
        body=json.dumps(payload,ensure_ascii=False,indent=2).encode()
        self.send_response(int(status)); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def _file(self,name):
        path=self.server.web_root/name
        if not path.is_file(): return self._json({"error":"not_found"},HTTPStatus.NOT_FOUND)
        body=path.read_bytes(); c,_=mimetypes.guess_type(path.name)
        self.send_response(200); self.send_header("Content-Type",c or "application/octet-stream"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,fmt,*args): print("[web] "+fmt%args)

def serve(host="127.0.0.1",port=8080,web_root="web",cache_path=".cyber-library/cache.sqlite3",contact=None):
    server=ThreadingHTTPServer((host,port),Handler); server.web_root=Path(web_root).resolve(); server.catalog=CatalogService(cache_path,contact)
    print(f"Cyber Library: http://{host}:{port}")
    try: server.serve_forever()
    finally: server.catalog.close(); server.server_close()

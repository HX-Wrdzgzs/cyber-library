from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .identifiers import InvalidISBN, normalize_isbn
from .server import serve
from .service import CatalogService
from .sources.openlibrary import NotFound, SourceError

def main()->int:
    p=argparse.ArgumentParser(prog="cyber-library"); sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("isbn"); a.add_argument("value")
    a=sub.add_parser("resolve"); a.add_argument("value"); a.add_argument("--analyze",action="store_true"); a.add_argument("--cache",default=".cyber-library/cache.sqlite3"); a.add_argument("--contact")
    a=sub.add_parser("inspect"); a.add_argument("path")
    a=sub.add_parser("serve"); a.add_argument("--host",default="127.0.0.1"); a.add_argument("--port",type=int,default=8080); a.add_argument("--web-root",default="web"); a.add_argument("--cache",default=".cyber-library/cache.sqlite3"); a.add_argument("--contact")
    args=p.parse_args()
    if args.command=="inspect":
        print(json.dumps(json.loads(Path(args.path).read_text(encoding="utf-8")),ensure_ascii=False,indent=2)); return 0
    if args.command=="isbn":
        try: print(normalize_isbn(args.value)); return 0
        except InvalidISBN as e: print(str(e)); return 2
    if args.command=="resolve":
        svc=CatalogService(args.cache,args.contact)
        try:
            print(json.dumps(svc.resolve_isbn(args.value,args.analyze).to_dict(),ensure_ascii=False,indent=2)); return 0
        except InvalidISBN as e: print(json.dumps({"error":"invalid_isbn","detail":str(e)})); return 2
        except NotFound: print('{"error":"not_found"}'); return 3
        except SourceError as e: print(json.dumps({"error":"upstream_error","detail":str(e)})); return 4
        finally: svc.close()
    if args.command=="serve":
        serve(args.host,args.port,args.web_root,args.cache,args.contact); return 0
    return 1

if __name__=="__main__": raise SystemExit(main())

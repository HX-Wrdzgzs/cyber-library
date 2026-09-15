from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any

class JsonCache:
    def __init__(self, path: str | Path, ttl_seconds: int = 86400) -> None:
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds=ttl_seconds
        self.db=sqlite3.connect(self.path)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache(cache_key TEXT PRIMARY KEY, body TEXT NOT NULL, stored_at INTEGER NOT NULL)")
        self.db.commit()
    def get(self,key:str)->dict[str,Any]|None:
        row=self.db.execute("SELECT body, stored_at FROM cache WHERE cache_key=?",(key,)).fetchone()
        if not row: return None
        body, stored_at=row
        if int(time.time())-int(stored_at)>self.ttl_seconds:
            self.db.execute("DELETE FROM cache WHERE cache_key=?",(key,)); self.db.commit(); return None
        return json.loads(body)
    def set(self,key:str,value:dict[str,Any])->None:
        self.db.execute("INSERT INTO cache(cache_key,body,stored_at) VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET body=excluded.body, stored_at=excluded.stored_at",(key,json.dumps(value,ensure_ascii=False),int(time.time())))
        self.db.commit()
    def close(self)->None: self.db.close()

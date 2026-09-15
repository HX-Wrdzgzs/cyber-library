from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .models import Analysis, BookRecord, Edition, Provenance, Work

class CatalogDB:
    def __init__(self,path:str|Path)->None:
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS works(id TEXT PRIMARY KEY,title TEXT NOT NULL,subjects TEXT NOT NULL DEFAULT '[]',authors TEXT NOT NULL DEFAULT '[]',raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS authors(id TEXT PRIMARY KEY,name TEXT NOT NULL,raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS editions(id TEXT PRIMARY KEY,work_id TEXT,title TEXT NOT NULL,language TEXT,publishers TEXT NOT NULL DEFAULT '[]',publish_date TEXT,page_count INTEGER,raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS identifiers(scheme TEXT NOT NULL,value TEXT NOT NULL,edition_id TEXT NOT NULL,PRIMARY KEY(scheme,value,edition_id));
        CREATE INDEX IF NOT EXISTS idx_identifiers_lookup ON identifiers(scheme,value);
        CREATE INDEX IF NOT EXISTS idx_editions_work ON editions(work_id);
        '''); self.db.commit()
    def upsert_author(self,key:str,raw:dict)->None:
        self.db.execute("INSERT INTO authors(id,name,raw_json) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,raw_json=excluded.raw_json",(key,str(raw.get('name') or ''),json.dumps(raw,ensure_ascii=False)))
    def upsert_work(self,key:str,raw:dict)->None:
        authors=[a.get('author',a).get('key') for a in (raw.get('authors') or []) if isinstance(a,dict) and isinstance(a.get('author',a),dict) and a.get('author',a).get('key')]
        subjects=[str(x) for x in (raw.get('subjects') or []) if isinstance(x,str)]
        self.db.execute("INSERT INTO works(id,title,subjects,authors,raw_json) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,subjects=excluded.subjects,authors=excluded.authors,raw_json=excluded.raw_json",(key,str(raw.get('title') or ''),json.dumps(subjects,ensure_ascii=False),json.dumps(authors,ensure_ascii=False),json.dumps(raw,ensure_ascii=False)))
    def upsert_edition(self,key:str,raw:dict)->None:
        works=raw.get('works') or []; work_id=works[0].get('key') if works and isinstance(works[0],dict) else None
        langs=raw.get('languages') or []; language=(langs[0].get('key','').rsplit('/',1)[-1] if langs and isinstance(langs[0],dict) else None) or None
        self.db.execute("INSERT INTO editions(id,work_id,title,language,publishers,publish_date,page_count,raw_json) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET work_id=excluded.work_id,title=excluded.title,language=excluded.language,publishers=excluded.publishers,publish_date=excluded.publish_date,page_count=excluded.page_count,raw_json=excluded.raw_json",(key,work_id,str(raw.get('title') or ''),language,json.dumps([str(x) for x in (raw.get('publishers') or [])],ensure_ascii=False),raw.get('publish_date'),raw.get('number_of_pages'),json.dumps(raw,ensure_ascii=False)))
        self.db.execute("DELETE FROM identifiers WHERE edition_id=?",(key,))
        schemes={'isbn10':'isbn_10','isbn13':'isbn_13','lccn':'lccn','oclc':'oclc_numbers'}
        for scheme,field in schemes.items():
            for value in raw.get(field) or []:
                self.db.execute("INSERT OR IGNORE INTO identifiers(scheme,value,edition_id) VALUES(?,?,?)",(scheme,str(value).replace('-','').strip(),key))
    def commit(self)->None:self.db.commit()
    def lookup_isbn(self,isbn13:str)->BookRecord|None:
        row=self.db.execute("SELECT edition_id FROM identifiers WHERE scheme='isbn13' AND value=? LIMIT 1",(isbn13,)).fetchone()
        if not row:return None
        e=self.db.execute("SELECT id,work_id,title,language,publishers,publish_date,page_count FROM editions WHERE id=?",(row[0],)).fetchone()
        if not e:return None
        ids={}
        for scheme,value in self.db.execute("SELECT scheme,value FROM identifiers WHERE edition_id=?",(e[0],)):ids.setdefault(scheme,[]).append(value)
        work=None
        if e[1]:
            w=self.db.execute("SELECT id,title,subjects,authors FROM works WHERE id=?",(e[1],)).fetchone()
            if w:
                names=[]
                for aid in json.loads(w[3]):
                    a=self.db.execute("SELECT name FROM authors WHERE id=?",(aid,)).fetchone(); names.append(a[0] if a and a[0] else aid)
                work=Work(id=w[0],title=w[1],authors=names,subjects=json.loads(w[2]),source_refs=[f"openlibrary:{w[0]}"])
        edition=Edition(id=e[0],work_id=e[1],title=e[2],language=e[3],publishers=json.loads(e[4]),publish_date=e[5],page_count=e[6],identifiers=ids,source_refs=[f"openlibrary:{e[0]}"])
        return BookRecord(work=work,edition=edition,analysis=Analysis(level='L0',confidence=1.0,sources=edition.source_refs,warnings=['Loaded from local bibliographic metadata; no interpretation generated.']),provenance=[Provenance(source='Open Library dump',source_id=e[0])])
    def stats(self)->dict[str,int]:
        return {name:self.db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ('works','editions','authors','identifiers')}
    def close(self)->None:self.db.close()

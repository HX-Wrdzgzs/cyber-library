from __future__ import annotations
import gzip,json
from pathlib import Path
from typing import TextIO
from .database import CatalogDB

def _open(path:Path)->TextIO:
    return gzip.open(path,'rt',encoding='utf-8',errors='replace') if path.suffix=='.gz' else path.open('r',encoding='utf-8',errors='replace')

def import_openlibrary_dump(path:str|Path,db_path:str|Path,limit:int|None=None,commit_every:int=5000)->dict[str,int]:
    path=Path(path); db=CatalogDB(db_path); counts={'lines':0,'works':0,'editions':0,'authors':0,'errors':0}
    try:
        with _open(path) as fh:
            for line in fh:
                if limit is not None and counts['lines']>=limit:break
                counts['lines']+=1
                try:
                    cols=line.rstrip('\n').split('\t',4)
                    if len(cols)!=5:raise ValueError('expected five TSV columns')
                    typ,key,_,_,payload=cols; raw=json.loads(payload)
                    if typ=='/type/work':db.upsert_work(key,raw);counts['works']+=1
                    elif typ=='/type/edition':db.upsert_edition(key,raw);counts['editions']+=1
                    elif typ=='/type/author':db.upsert_author(key,raw);counts['authors']+=1
                except (ValueError,json.JSONDecodeError,TypeError):counts['errors']+=1
                if counts['lines']%commit_every==0:db.commit()
        db.commit();return counts
    finally:db.close()

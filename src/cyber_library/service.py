from pathlib import Path
from .cache import JsonCache
from .intelligence import catalog_analysis
from .sources.openlibrary import OpenLibraryClient

class CatalogService:
    def __init__(self,cache_path: str|Path=".cyber-library/cache.sqlite3",contact:str|None=None)->None:
        self.cache=JsonCache(cache_path); self.openlibrary=OpenLibraryClient(self.cache,contact)
    def resolve_isbn(self,isbn:str,analyze:bool=False):
        record=self.openlibrary.lookup_isbn(isbn)
        if analyze: record.analysis=catalog_analysis(record)
        return record
    def close(self)->None: self.cache.close()

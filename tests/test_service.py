import tempfile
import unittest
from pathlib import Path
from cyber_library.service import CatalogService
class ServiceTest(unittest.TestCase):
    def test_local_fulltext_analysis_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            service=CatalogService(cache_path=Path(directory)/'cache.sqlite3',catalog_db_path=Path(directory)/'catalog.sqlite3',live_fallback=False,use_llm=False)
            try:
                text=("Systems are composed of interacting parts. Clear interfaces reduce accidental coupling. Observability helps operators understand failures. ")*30
                record=service.analyze_text(text,rights='user-provided',title='Systems Notes')
                self.assertEqual(record.analysis.level,'L3'); self.assertTrue(record.analysis.summary); stats=service.stats(); self.assertEqual(stats['documents'],1); self.assertEqual(stats['analyses'],1)
            finally: service.close()
if __name__=='__main__': unittest.main()

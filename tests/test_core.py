import tempfile, unittest
from pathlib import Path
from cyber_library.cache import JsonCache
from cyber_library.intelligence import catalog_analysis
from cyber_library.models import Analysis,BookRecord,Edition,Work
class T(unittest.TestCase):
    def test_cache(self):
        with tempfile.TemporaryDirectory() as d:
            c=JsonCache(Path(d)/"c.db"); c.set("a",{"x":1}); self.assertEqual(c.get("a"),{"x":1}); c.close()
    def test_l1_safe(self):
        r=BookRecord(Work("w","Example",subjects=["Computers"]),Edition("e","w","Example",publishers=["Press"]),Analysis(sources=["demo"]))
        a=catalog_analysis(r); self.assertEqual(a.level,"L1"); self.assertEqual(a.outline,[]); self.assertTrue(a.warnings)

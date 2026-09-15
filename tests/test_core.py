import tempfile
import unittest
from pathlib import Path

from cyber_library.cache import JsonCache
from cyber_library.intelligence import catalog_analysis
from cyber_library.models import Analysis, BookRecord, Edition, Work


class CoreTest(unittest.TestCase):
    def test_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory) / "cache.db")
            cache.set("a", {"x": 1})
            self.assertEqual(cache.get("a"), {"x": 1})
            cache.close()

    def test_l1_stays_inside_catalog_evidence(self):
        record = BookRecord(
            Work("w", "Example", authors=["A"], subjects=["Computers"]),
            Edition("e", "w", "Example", publishers=["Press"]),
            Analysis(sources=["demo"]),
        )
        analysis = catalog_analysis(record)
        self.assertEqual(analysis.level, "L1")
        self.assertEqual(analysis.table_of_contents, [])
        self.assertEqual(analysis.outline, [])
        self.assertIsNone(analysis.detailed)
        self.assertIsNotNone(analysis.mindmap)
        self.assertTrue(analysis.warnings)


if __name__ == "__main__":
    unittest.main()

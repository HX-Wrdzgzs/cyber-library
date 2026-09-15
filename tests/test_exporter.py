import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.exporter import export_analysis_bundle, export_universe_static, import_analysis_bundle
from cyber_library.models import Analysis


class ExporterTest(unittest.TestCase):
    def test_static_universe_and_analysis_bundle_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            db = CatalogDB(source)
            try:
                db.upsert_work("/works/W1", {"title": "Export Work", "subjects": ["Science"]})
                db.upsert_edition("/books/E1", {"title": "Export Work", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"]})
                db.store_analysis("a1", "/books/E1", Analysis(level="L1", brief="demo", sources=["fixture:test"]))
                db.commit()
            finally:
                db.close()

            universe = export_universe_static(source, root / "universe", max_level=2, rebuild=True)
            self.assertEqual(len(universe["files"]), 3)
            self.assertTrue((root / "universe" / "manifest.json").is_file())

            bundle = export_analysis_bundle(source, root / "bundle")
            self.assertEqual(bundle["records"], 1)
            self.assertIn("fixture:test", bundle["sources"])

            target = root / "target.sqlite3"
            imported = import_analysis_bundle(target, root / "bundle")
            self.assertEqual(imported["imported"], 1)
            target_db = CatalogDB(target)
            try:
                self.assertEqual(target_db.stats()["analyses"], 1)
            finally:
                target_db.close()


if __name__ == "__main__":
    unittest.main()

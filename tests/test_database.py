import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB


class DatabaseTest(unittest.TestCase):
    def test_import_lookup_search_and_universe(self):
        with tempfile.TemporaryDirectory() as directory:
            db = CatalogDB(Path(directory) / "catalog.sqlite3", index_on_write=False)
            try:
                db.upsert_author("/authors/OL1A", {"name": "Example Author"})
                db.upsert_work("/works/OL1W", {"title": "Practical Machine Learning", "authors": [{"author": {"key": "/authors/OL1A"}}], "subjects": ["Machine learning", "Computer science"], "description": "A practical guide to machine learning systems."})
                db.upsert_edition("/books/OL1M", {"title": "Practical Machine Learning", "works": [{"key": "/works/OL1W"}], "isbn_13": ["9780306406157"], "publishers": ["Example Press"], "publish_date": "2025", "languages": [{"key": "/languages/eng"}], "table_of_contents": [{"title": "Models"}, {"title": "Deployment"}]})
                db.commit()
                self.assertEqual(db.reindex()["indexed"], 1)
                record = db.lookup_isbn("9780306406157")
                self.assertIsNotNone(record)
                self.assertEqual(record.work.authors, ["Example Author"])
                self.assertTrue(record.evidence)
                results = db.search("Machine Learning")
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["isbn"], "9780306406157")
                points = db.universe_points()
                self.assertEqual(len(points), 1)
                self.assertEqual(points[0]["isbn"], "9780306406157")
            finally: db.close()


if __name__ == "__main__": unittest.main()

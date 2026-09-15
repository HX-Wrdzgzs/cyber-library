import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.navigation import author_timeline, concept_graph, publisher_map


class NavigationTest(unittest.TestCase):
    def test_cross_work_navigation_views(self):
        with tempfile.TemporaryDirectory() as directory:
            db = CatalogDB(Path(directory) / "catalog.sqlite3")
            try:
                db.upsert_author("/authors/A1", {"name": "Ada Example"})
                db.upsert_work("/works/W1", {"title": "Learning Machines", "authors": [{"author": {"key": "/authors/A1"}}], "subjects": ["Machine learning", "Artificial intelligence"]})
                db.upsert_work("/works/W2", {"title": "Practical AI", "authors": [{"author": {"key": "/authors/A1"}}], "subjects": ["Machine learning", "Robotics"]})
                db.upsert_edition("/books/E1", {"title": "Learning Machines", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"], "publishers": ["Example Press"], "publish_date": "2020", "languages": [{"key": "/languages/eng"}]})
                db.upsert_edition("/books/E2", {"title": "Practical AI", "works": [{"key": "/works/W2"}], "isbn_13": ["9780140328721"], "publishers": ["Example Press"], "publish_date": "2024", "languages": [{"key": "/languages/eng"}]})
                db.commit()

                graph = concept_graph(db, "机器学习")
                self.assertEqual(graph["kind"], "concept_graph")
                self.assertEqual(graph["canonical_query"], "Machine learning")
                self.assertEqual(len(graph["works"]), 2)
                self.assertTrue(any(node.get("label") == "Robotics" for node in graph["nodes"]))

                timeline = author_timeline(db, "Ada Example")
                self.assertEqual([entry["year"] for entry in timeline["entries"]], [2020, 2024])
                self.assertEqual(len(timeline["authors"]), 1)

                publisher = publisher_map(db, "Example Press")
                self.assertEqual(publisher["publisher"], "Example Press")
                self.assertEqual(len(publisher["editions"]), 2)
                self.assertTrue(publisher["years"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

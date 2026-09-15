import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.scale import build_universe_tiles, query_universe_tiles, universe_tile_status


class ScaleIndexTest(unittest.TestCase):
    def test_universe_tiles_are_built_and_resumable(self):
        with tempfile.TemporaryDirectory() as directory:
            db = CatalogDB(Path(directory) / "catalog.sqlite3")
            try:
                db.upsert_work("/works/W1", {"title": "Physics", "subjects": ["Science"]})
                db.upsert_work("/works/W2", {"title": "Fiction", "subjects": ["Fiction"]})
                db.upsert_edition(
                    "/books/E1",
                    {"title": "Physics", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"]},
                )
                db.upsert_edition(
                    "/books/E2",
                    {"title": "Fiction", "works": [{"key": "/works/W2"}], "isbn_13": ["9780140328721"]},
                )
                db.commit()

                first = build_universe_tiles(db, max_level=4)
                self.assertEqual(first["skipped"], [])
                self.assertEqual(len(first["built"]), 5)

                level0 = query_universe_tiles(db, level=0)
                self.assertEqual(len(level0), 1)
                self.assertEqual(level0[0]["count"], 2)

                status = universe_tile_status(db)
                self.assertEqual(len(status["levels"]), 5)
                self.assertEqual(status["levels"][0]["items"], 2)

                second = build_universe_tiles(db, max_level=4)
                self.assertEqual(second["built"], [])
                self.assertEqual(second["skipped"], [0, 1, 2, 3, 4])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

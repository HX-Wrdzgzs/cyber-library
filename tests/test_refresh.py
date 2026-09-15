import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.refresh import get_refresh_checkpoint, refresh_openlibrary


class FakeRecentClient:
    def __init__(self, changes, documents):
        self.changes = list(changes)
        self.documents = dict(documents)
        self.document_requests = []

    def recent_changes(self, limit, offset=0):
        return self.changes[offset : offset + limit]

    def get_document(self, key):
        self.document_requests.append(key)
        return self.documents[key]


class RefreshTest(unittest.TestCase):
    def _seed(self, path):
        db = CatalogDB(path)
        db.upsert_author("/authors/A1", {"name": "Old Author"})
        db.upsert_work("/works/W1", {"title": "Old Title", "authors": [{"author": {"key": "/authors/A1"}}]})
        db.upsert_edition(
            "/books/E1",
            {"title": "Old Title", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"]},
        )
        db.commit()
        db.close()

    def test_bounded_refresh_applies_documents_and_advances_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.sqlite3"
            self._seed(path)
            client = FakeRecentClient(
                [
                    {"timestamp": "2026-09-16T01:00:00", "changes": [{"key": "/books/E2"}]},
                    {"timestamp": "2026-09-16T00:30:00", "changes": [{"key": "/works/W1"}]},
                    {"timestamp": "2026-09-15T23:50:00", "changes": [{"key": "/books/OLD"}]},
                ],
                {
                    "/books/E2": {"title": "New Edition", "works": [{"key": "/works/W1"}], "isbn_13": ["9780140328721"]},
                    "/works/W1": {"title": "Updated Work", "authors": [{"author": {"key": "/authors/A1"}}], "subjects": ["Science"]},
                },
            )
            result = refresh_openlibrary(path, client=client, since="2026-09-16T00:00:00Z", max_changes=10)
            self.assertFalse(result["truncated"])
            self.assertEqual(result["counts"]["editions"], 1)
            self.assertEqual(result["counts"]["works"], 1)
            self.assertTrue(result["checkpoint_advanced_to"].startswith("2026-09-16T01:00:00"))

            db = CatalogDB(path)
            try:
                record = db.lookup_isbn("9780140328721")
                self.assertIsNotNone(record)
                self.assertEqual(record.work.title, "Updated Work")
                self.assertTrue(get_refresh_checkpoint(db).startswith("2026-09-16T01:00:00"))
            finally:
                db.close()

    def test_truncated_window_does_not_advance_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.sqlite3"
            self._seed(path)
            client = FakeRecentClient(
                [
                    {"timestamp": "2026-09-16T02:00:00", "changes": [{"key": "/books/E2"}]},
                    {"timestamp": "2026-09-16T01:00:00", "changes": [{"key": "/books/E3"}]},
                ],
                {
                    "/books/E2": {"title": "E2", "works": [{"key": "/works/W1"}], "isbn_13": ["9780140328721"]},
                },
            )
            result = refresh_openlibrary(path, client=client, since="2026-09-16T00:00:00Z", max_changes=1)
            self.assertTrue(result["truncated"])
            self.assertIsNone(result["checkpoint_advanced_to"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.dump import import_openlibrary_dump
from cyber_library.identifiers import normalize_isbn


class DumpImportTest(unittest.TestCase):
    def test_import_and_lookup(self):
        author = {"name": "Example Author"}
        work = {"title": "Example Book", "authors": [{"author": {"key": "/authors/OL1A"}}], "subjects": ["Computers"]}
        edition = {
            "title": "Example Book",
            "works": [{"key": "/works/OL1W"}],
            "languages": [{"key": "/languages/eng"}],
            "publishers": ["Example Press"],
            "publish_date": "2026",
            "number_of_pages": 123,
            "isbn_10": ["0306406152"],
            "isbn_13": ["9780306406157"],
        }
        rows = [
            ("/type/author", "/authors/OL1A", author),
            ("/type/work", "/works/OL1W", work),
            ("/type/edition", "/books/OL1M", edition),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "dump.txt"
            dump.write_text("".join(f"{typ}\t{key}\t1\t2026-01-01T00:00:00.000000\t{json.dumps(payload)}\n" for typ, key, payload in rows), encoding="utf-8")
            db_path = Path(tmp) / "catalog.sqlite3"
            result = import_openlibrary_dump(dump, db_path)
            self.assertEqual(result["errors"], 0)
            self.assertEqual(result["works"], 1)
            db = CatalogDB(db_path)
            try:
                record = db.lookup_isbn(normalize_isbn("0-306-40615-2"))
                self.assertIsNotNone(record)
                self.assertEqual(record.work.title, "Example Book")
                self.assertEqual(record.work.authors, ["Example Author"])
                self.assertEqual(record.edition.language, "eng")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

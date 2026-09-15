import gzip
import json
import tempfile
import unittest
from pathlib import Path

from cyber_library.dump import import_openlibrary_dump, import_openlibrary_dumps


class DumpImportTest(unittest.TestCase):
    @staticmethod
    def _write_dump(path: Path, rows: list[tuple[str, str, str, dict]]) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            for typ, key, modified, payload in rows:
                fh.write(
                    "\t".join(
                        [typ, key, "1", modified, json.dumps(payload, ensure_ascii=False)]
                    )
                    + "\n"
                )

    def test_dump_reports_latest_modified_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "works.txt.gz"
            db = root / "catalog.sqlite3"
            self._write_dump(
                dump,
                [
                    ("/type/work", "/works/W1", "2026-08-30T12:00:00.000000", {"title": "Older"}),
                    ("/type/work", "/works/W2", "2026-08-31T23:59:59Z", {"title": "Newest"}),
                ],
            )
            result = import_openlibrary_dump(dump, db)
            self.assertEqual(result["works"], 2)
            self.assertEqual(result["latest_modified"], "2026-08-31T23:59:59+00:00")

    def test_multiple_dumps_keep_global_latest_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authors = root / "authors.txt.gz"
            editions = root / "editions.txt.gz"
            db = root / "catalog.sqlite3"
            self._write_dump(
                authors,
                [("/type/author", "/authors/A1", "2026-08-28T00:00:00Z", {"name": "Author"})],
            )
            self._write_dump(
                editions,
                [
                    (
                        "/type/edition",
                        "/books/E1",
                        "2026-08-31T18:30:00+00:00",
                        {"title": "Book", "isbn_13": ["9780306406157"]},
                    )
                ],
            )
            result = import_openlibrary_dumps([authors, editions], db, reindex=False)
            self.assertEqual(result["authors"], 1)
            self.assertEqual(result["editions"], 1)
            self.assertEqual(result["latest_modified"], "2026-08-31T18:30:00+00:00")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyber_library.catalog_ingest import add_isbn, validate_catalog
from cyber_library.models import Analysis, BookRecord, Edition, Provenance, Work


class FakeOpenLibraryClient:
    def lookup_isbn(self, isbn: str) -> BookRecord:
        return BookRecord(
            work=Work(
                id="openlibrary:work:OLTESTW",
                title="Test Book",
                authors=["Test Author"],
                subjects=["Testing"],
                categories=["Reference"],
                source_refs=["openlibrary:/works/OLTESTW"],
            ),
            edition=Edition(
                id="openlibrary:edition:OLTESTM",
                work_id="openlibrary:work:OLTESTW",
                title="Test Book",
                identifiers={"isbn13": [isbn], "isbn10": ["0306406152"]},
                publishers=["Test Press"],
                source_refs=["openlibrary:/books/OLTESTM"],
            ),
            analysis=Analysis(level="L0", confidence=1.0, sources=["openlibrary:/books/OLTESTM"]),
            provenance=[Provenance(source="Open Library", source_id="OLTESTM", url="https://openlibrary.org/books/OLTESTM")],
        )


class CatalogIngestTest(unittest.TestCase):
    def test_add_isbn_writes_commit_ready_record_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = add_isbn("0-306-40615-2", root=tmp, client=FakeOpenLibraryClient())
            self.assertTrue(first["changed"])
            path = Path(tmp) / first["path"]
            self.assertTrue(path.is_file())
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value["edition"]["identifiers"]["isbn13"], ["9780306406157"])
            self.assertEqual(value["analysis"]["level"], "L0")
            self.assertEqual(value["provenance"][0]["source"], "Open Library")
            self.assertTrue(validate_catalog(tmp)["ok"])

            second = add_isbn("9780306406157", root=tmp, client=FakeOpenLibraryClient())
            self.assertFalse(second["changed"])
            self.assertEqual(second["reason"], "already_exists")

    def test_validator_rejects_unsourced_or_invalid_catalog_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "data" / "catalog"
            folder.mkdir(parents=True)
            (folder / "bad.json").write_text(
                json.dumps({"work": {"id": "w", "title": "Bad"}, "edition": {"id": "e", "identifiers": {"isbn13": ["9780000000000"]}}}),
                encoding="utf-8",
            )
            result = validate_catalog(tmp)
            self.assertFalse(result["ok"])
            self.assertTrue(any("provenance" in error for error in result["errors"]))
            self.assertTrue(any("invalid isbn13" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()

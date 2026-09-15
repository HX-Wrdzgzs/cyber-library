import gzip
import json
import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.dump import import_openlibrary_dump
from cyber_library.sources.openlibrary import OpenLibraryClient
from cyber_library.taxonomy import classify, normalize_subject, normalize_subjects


class SubjectNormalizationTest(unittest.TestCase):
    def test_aliases_are_canonical_and_deduplicated(self):
        self.assertEqual(normalize_subject("人工智能"), "Artificial intelligence")
        self.assertEqual(normalize_subject("人工知能"), "Artificial intelligence")
        self.assertEqual(normalize_subjects(["人工智能", "Artificial intelligence", "機械学習"]), ["Artificial intelligence", "Machine learning"])
        self.assertIn("Computer Science", classify(["人工知能", "機械学習"], "Neural systems"))

    def test_dump_ingestion_normalizes_subjects_but_preserves_raw_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "works.txt.gz"
            db_path = root / "catalog.sqlite3"
            raw = {"title": "AI", "subjects": ["人工智能", "機械学習"]}
            with gzip.open(dump, "wt", encoding="utf-8") as fh:
                fh.write("\t".join(["/type/work", "/works/W1", "1", "2026-09-01T00:00:00Z", json.dumps(raw, ensure_ascii=False)]) + "\n")
            import_openlibrary_dump(dump, db_path)
            db = CatalogDB(db_path)
            try:
                row = db.db.execute("SELECT subjects,raw_json FROM works WHERE id='/works/W1'").fetchone()
                self.assertEqual(json.loads(row["subjects"]), ["Artificial intelligence", "Machine learning"])
                self.assertEqual(json.loads(row["raw_json"])["subjects"], ["人工智能", "機械学習"])
            finally:
                db.close()

    def test_live_record_normalizes_subjects(self):
        record = OpenLibraryClient.build_record(
            "9780306406157",
            {"key": "/books/E1", "title": "AI", "works": [{"key": "/works/W1"}]},
            {"key": "/works/W1", "title": "AI", "subjects": ["人工智能", "機械学習"]},
            ["Example Author"],
        )
        self.assertEqual(record.work.subjects, ["Artificial intelligence", "Machine learning"])


if __name__ == "__main__":
    unittest.main()

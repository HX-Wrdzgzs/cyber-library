from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cyber_library.reference_index import check_references, load_sources, render_references, validate_sources


class ReferenceIndexTest(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def test_repository_reference_markdown_matches_machine_readable_index(self) -> None:
        result = check_references(self.root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertGreaterEqual(result["sources"], 10)
        expected = render_references(load_sources(self.root))
        self.assertEqual((self.root / "REFERENCES.md").read_text(encoding="utf-8"), expected)

    def test_reference_validator_rejects_duplicate_ids_and_insecure_urls(self) -> None:
        errors = validate_sources([
            {"id": "same", "name": "A", "kind": "docs", "url": "http://example.test/a", "purpose": "A"},
            {"id": "same", "name": "B", "kind": "docs", "url": "https://example.test/b", "purpose": "B"},
        ])
        self.assertTrue(any("duplicate source id" in error for error in errors))
        self.assertTrue(any("must use https" in error for error in errors))

    def test_citation_cff_is_present_and_tracks_release(self) -> None:
        text = (self.root / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn("cff-version: 1.2.0", text)
        self.assertIn('title: "Cyber Library"', text)
        self.assertIn('version: "3.4.0"', text)
        self.assertIn("https://github.com/HX-Wrdzgzs/cyber-library", text)


if __name__ == "__main__":
    unittest.main()

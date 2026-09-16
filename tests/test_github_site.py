from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyber_library.github_site import build_github_site, check_markdown_links


class GitHubOnlySiteTest(unittest.TestCase):
    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def test_static_site_build_contains_catalog_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = build_github_site(self.root, tmp)
            out = Path(tmp)
            self.assertGreaterEqual(result["records"], 2)
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / "404.html").is_file())
            self.assertTrue((out / "github.js").is_file())
            self.assertTrue((out / ".nojekyll").is_file())
            catalog = json.loads((out / "site-data" / "catalog.json").read_text(encoding="utf-8"))
            refs = json.loads((out / "site-data" / "references.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["format"], "cyber-library-github-static")
            self.assertTrue(any((r.get("edition", {}).get("identifiers", {}).get("isbn13") or []) for r in catalog["records"]))
            self.assertTrue(any(r.get("universe") for r in catalog["records"]))
            self.assertGreaterEqual(len(refs.get("sources", [])), 5)

    def test_repository_markdown_links_are_valid(self) -> None:
        result = check_markdown_links(self.root)
        self.assertTrue(result["ok"], result["broken"])


if __name__ == "__main__":
    unittest.main()

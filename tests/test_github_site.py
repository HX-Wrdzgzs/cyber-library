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

    def test_static_site_build_contains_index_records_manifest_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = build_github_site(self.root, tmp)
            out = Path(tmp)
            self.assertGreaterEqual(result["records"], 2)
            self.assertEqual(result["records"], result["record_files"])
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / "404.html").is_file())
            self.assertTrue((out / "github.js").is_file())
            self.assertTrue((out / ".nojekyll").is_file())

            index = json.loads((out / "site-data" / "index.json").read_text(encoding="utf-8"))
            refs = json.loads((out / "site-data" / "references.json").read_text(encoding="utf-8"))
            manifest = json.loads((out / "site-data" / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(index["format"], "cyber-library-github-index")
            self.assertEqual(index["version"], 2)
            self.assertEqual(manifest["format"], "cyber-library-github-manifest")
            self.assertEqual(manifest["records"], len(index["records"]))
            self.assertTrue(any((r.get("edition", {}).get("identifiers", {}).get("isbn13") or []) for r in index["records"]))
            self.assertTrue(any(r.get("universe") for r in index["records"]))
            self.assertTrue(all(r.get("record_file", "").startswith("records/") for r in index["records"]))
            self.assertGreaterEqual(len(refs.get("sources", [])), 5)

            for entry in index["records"]:
                record_path = out / "site-data" / entry["record_file"]
                self.assertTrue(record_path.is_file())
                record = json.loads(record_path.read_text(encoding="utf-8"))
                self.assertEqual(record.get("edition", {}).get("id"), entry.get("edition", {}).get("id"))

            manifest_paths = {item["path"] for item in manifest["files"]}
            self.assertIn("index.json", manifest_paths)
            self.assertIn("references.json", manifest_paths)
            self.assertIn("project.json", manifest_paths)
            self.assertTrue(any(path.startswith("records/") for path in manifest_paths))
            self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["files"]))

    def test_repository_markdown_links_are_valid(self) -> None:
        result = check_markdown_links(self.root)
        self.assertTrue(result["ok"], result["broken"])


if __name__ == "__main__":
    unittest.main()

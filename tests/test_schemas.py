import json
import unittest
from pathlib import Path


class SchemaFilesTest(unittest.TestCase):
    def test_all_schema_files_are_valid_json(self):
        paths = sorted(Path("schemas").glob("*.json"))
        self.assertGreaterEqual(len(paths), 4)
        for path in paths:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("$schema", data)


if __name__ == "__main__":
    unittest.main()

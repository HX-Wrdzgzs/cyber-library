import tempfile
import unittest
from pathlib import Path

from cyber_library.benchmark import run_bulk_benchmark


class BenchmarkTest(unittest.TestCase):
    def test_synthetic_bulk_benchmark_uses_real_importer(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_bulk_benchmark(24, Path(directory), reindex=True)
            self.assertEqual(result["requested_editions"], 24)
            self.assertEqual(result["imported"]["editions"], 24)
            self.assertGreater(result["editions_per_second"], 0)
            self.assertGreater(result["database_bytes"], 0)


if __name__ == "__main__":
    unittest.main()

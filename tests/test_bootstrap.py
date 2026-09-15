import gzip
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyber_library.bootstrap import OPENLIBRARY_DUMP_URLS, bootstrap_openlibrary, download_url
from cyber_library.database import CatalogDB
from cyber_library.refresh import get_refresh_checkpoint


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, *, status: int, headers: dict[str, str], url: str):
        super().__init__(payload)
        self.status = status
        self.headers = headers
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def geturl(self):
        return self._url


class BootstrapTest(unittest.TestCase):
    def test_official_latest_dump_urls(self):
        self.assertEqual(set(OPENLIBRARY_DUMP_URLS), {"authors", "works", "editions"})
        for kind, url in OPENLIBRARY_DUMP_URLS.items():
            self.assertTrue(url.startswith("https://openlibrary.org/data/"), kind)
            self.assertTrue(url.endswith("_latest.txt.gz"), kind)

    def test_download_can_resume_partial_gzip(self):
        full = gzip.compress(b"hello cyber library\n" * 100)
        cut = max(2, len(full) // 3)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            partial = root / "sample.txt.gz.part"
            partial.write_bytes(full[:cut])
            response = FakeResponse(full[cut:], status=206, headers={"Content-Length": str(len(full) - cut), "Content-Range": f"bytes {cut}-{len(full)-1}/{len(full)}"}, url="https://example.invalid/sample.txt.gz")
            with patch("cyber_library.bootstrap.urlopen", return_value=response) as mocked:
                result = download_url("https://example.invalid/sample.txt.gz", root)
            self.assertEqual(result["status"], "downloaded")
            self.assertEqual((root / "sample.txt.gz").read_bytes(), full)
            self.assertFalse(partial.exists())
            request = mocked.call_args.args[0]
            self.assertEqual(request.headers.get("Range"), f"bytes={cut}-")

    def test_existing_download_is_reused(self):
        full = gzip.compress(b"already here")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sample.txt.gz"
            target.write_bytes(full)
            with patch("cyber_library.bootstrap.urlopen") as mocked:
                result = download_url("https://example.invalid/sample.txt.gz", root)
            self.assertEqual(result["status"], "existing")
            mocked.assert_not_called()

    def test_complete_bootstrap_seeds_refresh_checkpoint_from_dump_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump_dir = root / "dumps"
            dump_dir.mkdir()
            db_path = root / "catalog.sqlite3"
            fake_downloads = {
                kind: {"kind": kind, "url": url, "path": str(dump_dir / f"{kind}.gz"), "bytes": 1, "status": "existing"}
                for kind, url in OPENLIBRARY_DUMP_URLS.items()
            }

            def fake_download(kind, *_args, **_kwargs):
                return fake_downloads[kind]

            imported = {"lines": 3, "works": 1, "editions": 1, "authors": 1, "errors": 0, "latest_modified": "2026-08-31T23:59:59+00:00", "indexed": 0, "coordinates_updated": 0}
            with patch("cyber_library.bootstrap.download_openlibrary_dump", side_effect=fake_download), patch("cyber_library.bootstrap.import_openlibrary_dumps", return_value=imported):
                result = bootstrap_openlibrary(db_path, dump_dir)

            self.assertEqual(result["refresh_checkpoint"], "2026-08-31T23:59:59+00:00")
            db = CatalogDB(db_path)
            try:
                self.assertEqual(get_refresh_checkpoint(db), "2026-08-31T23:59:59+00:00")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

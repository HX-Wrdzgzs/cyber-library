import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from cyber_library.database import CatalogDB
from cyber_library.deployment import OpenSearchAdapter, OpenSearchConfig, PostgresCatalogAdapter, PostgresConfig, QdrantAdapter, QdrantConfig, S3ArtifactPublisher, S3Config
from cyber_library.semantic import ensure_embedding_schema


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close(); return False


class FakeS3:
    def __init__(self): self.calls=[]
    def upload_file(self, path, bucket, key, ExtraArgs=None): self.calls.append((path,bucket,key,ExtraArgs or {}))


class DeploymentAdapterTest(unittest.TestCase):
    def _catalog(self, directory):
        db=CatalogDB(Path(directory)/"catalog.sqlite3")
        db.upsert_author("/authors/A1",{"name":"Ada Example"})
        db.upsert_work("/works/W1",{"title":"Machine Learning","authors":[{"author":{"key":"/authors/A1"}}],"subjects":["Machine learning"]})
        db.upsert_edition("/books/E1",{"title":"Machine Learning","works":[{"key":"/works/W1"}],"isbn_13":["9780306406157"],"publishers":["Example Press"],"languages":[{"key":"/languages/eng"}]})
        db.commit();return db

    def test_postgres_status_does_not_require_driver(self):
        adapter=PostgresCatalogAdapter(PostgresConfig("postgresql://example.invalid/db"))
        self.assertTrue(adapter.health()["configured"])
        self.assertTrue(adapter.health()["postgis_optional"])

    def test_opensearch_search_contract(self):
        payload={"hits":{"hits":[{"_score":2.5,"_source":{"edition_id":"/books/E1","title":"Machine Learning"}}]}}
        adapter=OpenSearchAdapter(OpenSearchConfig("http://search.invalid","books"))
        with patch("cyber_library.deployment.urlopen",return_value=FakeResponse(json.dumps(payload).encode())) as mocked:
            result=adapter.search("machine",limit=5)
        self.assertEqual(result[0]["edition_id"],"/books/E1")
        self.assertEqual(result[0]["source"],"opensearch")
        request=mocked.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/books/_search"))
        self.assertEqual(request.method,"POST")

    def test_opensearch_sync_uses_bulk_api(self):
        with tempfile.TemporaryDirectory() as directory:
            db=self._catalog(directory);calls=[]
            def fake_open(request, timeout=None):
                calls.append((request.method,request.full_url,request.data))
                if request.method=="GET" and request.full_url.endswith("/books"):
                    raise HTTPError(request.full_url,404,"missing",{},None)
                return FakeResponse(json.dumps({"errors":False}).encode())
            try:
                adapter=OpenSearchAdapter(OpenSearchConfig("http://search.invalid","books"))
                with patch("cyber_library.deployment.urlopen",side_effect=fake_open):
                    result=adapter.sync_from_sqlite(db,batch_size=1)
                self.assertEqual(result["indexed"],1)
                bulk=[c for c in calls if c[1].endswith("/_bulk")][0]
                self.assertIn(b'"edition_id":"/books/E1"',bulk[2])
            finally: db.close()

    def test_qdrant_sync_and_query_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            db=self._catalog(directory);ensure_embedding_schema(db)
            with db._lock:
                db.db.execute("INSERT INTO embeddings(edition_id,model,dimensions,vector_json,text_hash,updated_at) VALUES(?,?,?,?,?,?)",("/books/E1","demo",3,"[0.1,0.2,0.3]","x","now"));db.db.commit()
            calls=[]
            def fake_open(request, timeout=None):
                calls.append((request.method,request.full_url,request.data))
                if request.method=="GET" and "/collections/books" in request.full_url:
                    raise HTTPError(request.full_url,404,"missing",{},None)
                if request.full_url.endswith("/points/query"):
                    return FakeResponse(json.dumps({"result":{"points":[{"id":"p1","score":0.9,"payload":{"edition_id":"/books/E1"}}]}}).encode())
                return FakeResponse(b'{"status":"ok"}')
            try:
                adapter=QdrantAdapter(QdrantConfig("http://qdrant.invalid","books"))
                with patch("cyber_library.deployment.urlopen",side_effect=fake_open):
                    result=adapter.sync_embeddings(db,"demo",batch_size=1)
                    matches=adapter.query([0.1,0.2,0.3],limit=3)
                self.assertEqual(result["indexed"],1)
                self.assertEqual(matches[0]["payload"]["edition_id"],"/books/E1")
                self.assertTrue(any("/points?wait=true" in c[1] for c in calls))
            finally: db.close()

    def test_s3_publisher_uploads_manifest_and_tiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"manifest.json").write_text("{}",encoding="utf-8");(root/"z0.json").write_text("{}",encoding="utf-8")
            fake=FakeS3();publisher=S3ArtifactPublisher(S3Config("bucket","universe"),client=fake)
            report=publisher.publish_directory(root)
            self.assertEqual(report["uploaded"],2)
            keys={call[2] for call in fake.calls};self.assertEqual(keys,{"universe/manifest.json","universe/z0.json"})
            manifest=[call for call in fake.calls if call[2].endswith("manifest.json")][0]
            self.assertEqual(manifest[3]["CacheControl"],"no-cache")


if __name__=="__main__": unittest.main()

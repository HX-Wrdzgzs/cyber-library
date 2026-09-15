import tempfile
import unittest
from pathlib import Path

from cyber_library.database import CatalogDB
from cyber_library.semantic import build_embedding_index, embedding_count, hybrid_search, semantic_search


class FakeEmbeddingClient:
    model_name = "fake-embedding"

    def embed(self, texts):
        vectors = []
        for text in texts:
            value = text.lower()
            if "space" in value or "galaxy" in value or "astronomy" in value:
                vectors.append([1.0, 0.0])
            elif "cook" in value or "kitchen" in value or "recipe" in value:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.5, 0.5])
        return vectors


class SemanticSearchTest(unittest.TestCase):
    def test_incremental_index_and_semantic_ranking(self):
        with tempfile.TemporaryDirectory() as directory:
            db = CatalogDB(Path(directory) / "catalog.sqlite3")
            try:
                db.upsert_work("/works/W1", {"title": "Space Atlas", "subjects": ["Astronomy", "Space"]})
                db.upsert_work("/works/W2", {"title": "Kitchen Book", "subjects": ["Cooking", "Recipes"]})
                db.upsert_edition(
                    "/books/E1",
                    {"title": "Space Atlas", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"]},
                )
                db.upsert_edition(
                    "/books/E2",
                    {"title": "Kitchen Book", "works": [{"key": "/works/W2"}], "isbn_13": ["9780140328721"]},
                )
                db.commit()

                client = FakeEmbeddingClient()
                first = build_embedding_index(db, client, batch_size=1)
                self.assertEqual(first["indexed"], 2)
                self.assertEqual(embedding_count(db, client.model_name), 2)

                second = build_embedding_index(db, client, batch_size=2)
                self.assertEqual(second["indexed"], 0)

                results = semantic_search(db, client, "galaxy", limit=2)
                self.assertEqual(results[0]["title"], "Space Atlas")
                self.assertGreater(results[0]["semantic_score"], results[1]["semantic_score"])

                hybrid = hybrid_search(db, client, "galaxy", [], limit=1)
                self.assertEqual(hybrid[0]["title"], "Space Atlas")
                self.assertEqual(hybrid[0]["rank_source"], "hybrid")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

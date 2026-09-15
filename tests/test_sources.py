import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cyber_library.database import CatalogDB
from cyber_library.reconciliation import links_for, reconcile_isbn
from cyber_library.sources.base import SourceMatch
from cyber_library.sources.crossref import CrossrefAdapter
from cyber_library.sources.registry import SourceRegistry, register_builtin_sources
from cyber_library.sources.wikidata import WikidataAdapter


class FakeResponse(io.BytesIO):
    def __init__(self, payload: dict):
        super().__init__(json.dumps(payload).encode("utf-8"))
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close(); return False


class FakeAdapter:
    name = "fake"
    @property
    def capabilities(self): return ("isbn-reconciliation",)
    def health(self): return {"name": self.name, "configured": True}
    def reconcile_isbn(self, isbn): return [SourceMatch(source=self.name, source_id="X1", url="https://example.invalid/X1", label="Example entity", confidence=1.0, identifiers={"isbn13": ["9780306406157"]})]


class SourceAdapterTest(unittest.TestCase):
    def test_registry_contract(self):
        registry = SourceRegistry(); registry.register("fake", FakeAdapter)
        self.assertEqual(registry.names(), ["fake"]); self.assertEqual(registry.create("fake").name, "fake")
        with self.assertRaises(ValueError): registry.register("fake", FakeAdapter)

    def test_builtin_registry_contains_wikidata_and_crossref(self):
        names = register_builtin_sources().names(); self.assertIn("wikidata", names); self.assertIn("crossref", names)

    def test_wikidata_isbn_binding(self):
        payload = {"results": {"bindings": [{"item": {"type": "uri", "value": "http://www.wikidata.org/entity/Q123"}, "itemLabel": {"type": "literal", "value": "Example book"}, "itemDescription": {"type": "literal", "value": "book edition"}, "isbn13": {"type": "literal", "value": "978-0-306-40615-7"}}]}}
        adapter = WikidataAdapter(endpoint="https://query.wikidata.org/sparql")
        with patch("cyber_library.sources.wikidata.urlopen", return_value=FakeResponse(payload)) as mocked: matches = adapter.reconcile_isbn("9780306406157")
        self.assertEqual(matches[0].source_id, "Q123"); self.assertEqual(matches[0].identifiers["isbn13"], ["9780306406157"])
        self.assertIn("P212", mocked.call_args.args[0].full_url)

    def test_wikidata_authority_candidates(self):
        payload = {"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q42"}, "itemLabel": {"value": "Example Author"}, "itemDescription": {"value": "writer"}, "isni": {"value": "0000000123456789"}, "viaf": {"value": "12345"}, "lcnaf": {"value": "n123"}, "gnd": {"value": "456"}}]}}
        adapter = WikidataAdapter(endpoint="https://query.wikidata.org/sparql")
        with patch("cyber_library.sources.wikidata.urlopen", return_value=FakeResponse(payload)) as mocked: matches = adapter.reconcile_author("Example Author")
        self.assertEqual(matches[0].identifiers["isni"], ["0000000123456789"])
        self.assertEqual(matches[0].identifiers["viaf"], ["12345"])
        self.assertFalse(matches[0].metadata["auto_merge"])
        url = mocked.call_args.args[0].full_url
        self.assertIn("P213", url); self.assertIn("P214", url); self.assertIn("P244", url); self.assertIn("P227", url)

    def test_crossref_isbn_binding(self):
        payload = {"message": {"items": [{"DOI": "10.1234/EXAMPLE", "title": ["Example book"], "type": "book", "ISBN": ["978-0-306-40615-7"], "publisher": "Example Press", "issued": {"date-parts": [[2020]]}, "author": [{"given": "Ada", "family": "Example"}], "URL": "https://doi.org/10.1234/example"}]}}
        adapter = CrossrefAdapter(base_url="https://api.crossref.org", contact="dev@example.invalid")
        with patch("cyber_library.sources.crossref.urlopen", return_value=FakeResponse(payload)) as mocked: matches = adapter.reconcile_isbn("9780306406157")
        self.assertEqual(matches[0].source_id, "10.1234/example"); self.assertEqual(matches[0].metadata["authors"], ["Ada Example"])
        request = mocked.call_args.args[0]; self.assertIn("filter=isbn%3A9780306406157", request.full_url); self.assertIn("mailto=dev%40example.invalid", request.full_url)

    def test_crossref_citation_graph(self):
        payload = {"message": {"DOI": "10.1234/example", "title": ["Example book"], "is-referenced-by-count": 7, "reference": [{"DOI": "10.1000/a", "article-title": "A", "year": "2020"}, {"unstructured": "No DOI reference"}], "relation": {"is-preprint-of": [{"id-type": "doi", "id": "10.1000/pre", "asserted-by": "subject"}]}}}
        adapter = CrossrefAdapter(base_url="https://api.crossref.org", contact="dev@example.invalid")
        with patch("cyber_library.sources.crossref.urlopen", return_value=FakeResponse(payload)) as mocked: graph = adapter.citation_graph("10.1234/example")
        self.assertEqual(graph["is_referenced_by_count"], 7); self.assertEqual(len(graph["edges"]), 1); self.assertEqual(graph["references_without_doi"], 1)
        self.assertEqual(graph["relations"][0]["kind"], "is-preprint-of")
        self.assertIn("10.1234%2Fexample", mocked.call_args.args[0].full_url)

    def test_reconciliation_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            db = CatalogDB(Path(directory) / "catalog.sqlite3")
            try:
                db.upsert_work("/works/W1", {"title": "Example book"})
                db.upsert_edition("/books/E1", {"title": "Example book", "works": [{"key": "/works/W1"}], "isbn_13": ["9780306406157"]}); db.commit()
                result = reconcile_isbn(db, FakeAdapter(), "9780306406157")
                stored = links_for(db, "edition", result["edition_id"])
                self.assertEqual(result["stored"], 1); self.assertEqual(stored[0]["source"], "fake"); self.assertEqual(stored[0]["source_id"], "X1")
            finally: db.close()


if __name__ == "__main__": unittest.main()

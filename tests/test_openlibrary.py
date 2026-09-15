import unittest
from cyber_library.sources.openlibrary import OpenLibraryClient
class OpenLibraryTransformTest(unittest.TestCase):
    def test_build_record_extracts_evidence(self):
        edition={"key":"/books/OL1M","title":"Example Book","works":[{"key":"/works/OL1W"}],"isbn_13":["9780306406157"],"publishers":["Example Press"],"table_of_contents":[{"title":"One"},{"title":"Two"}],"languages":[{"key":"/languages/eng"}],"covers":[123]}
        work={"key":"/works/OL1W","title":"Example Book","description":{"value":"A source-backed description of the work."},"subjects":["Computer science"],"first_sentence":{"value":"It begins with a system."}}
        record=OpenLibraryClient.build_record("9780306406157",edition,work,["Example Author"])
        self.assertEqual(record.work.title,"Example Book"); self.assertEqual(record.edition.table_of_contents,["One","Two"]); self.assertTrue(record.evidence); self.assertIn("Computer Science",record.work.categories); self.assertIn("/id/123-L.jpg",record.edition.cover_url)
if __name__ == "__main__": unittest.main()

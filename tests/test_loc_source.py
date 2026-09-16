import io
import unittest
from unittest.mock import patch

from cyber_library.sources.loc import LibraryOfCongressAdapter


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close(); return False


MARC = b'''<?xml version="1.0"?>
<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
  <records><record><recordData>
    <record xmlns="http://www.loc.gov/MARC21/slim">
      <controlfield tag="001">123456</controlfield>
      <datafield tag="010"><subfield code="a">  2026123456 </subfield></datafield>
      <datafield tag="020"><subfield code="a">978-0-306-40615-7 (hardcover)</subfield></datafield>
      <datafield tag="100"><subfield code="a">Example, Ada</subfield></datafield>
      <datafield tag="245"><subfield code="a">Example book :</subfield><subfield code="b">a test</subfield></datafield>
      <datafield tag="264"><subfield code="b">Example Press</subfield><subfield code="c">2026.</subfield></datafield>
    </record>
  </recordData></record></records>
</searchRetrieveResponse>'''

MADS = b'''<?xml version="1.0"?>
<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
  <records><record><recordData>
    <mads xmlns="http://www.loc.gov/mads/v2">
      <recordInfo><recordIdentifier>n12345678</recordIdentifier></recordInfo>
      <authority><name type="personal"><namePart>Example, Ada</namePart></name></authority>
      <identifier type="isni">0000000123456789</identifier>
    </mads>
  </recordData></record></records>
</searchRetrieveResponse>'''


class LibraryOfCongressSourceTest(unittest.TestCase):
    def test_isbn_sru_reconciliation(self):
        adapter=LibraryOfCongressAdapter(lcdb_url="http://loc.invalid/LCDB",naf_url="http://loc.invalid/NAF")
        with patch("cyber_library.sources.loc.urlopen",return_value=FakeResponse(MARC)) as mocked:
            matches=adapter.reconcile_isbn("9780306406157")
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0].identifiers["isbn13"],["9780306406157"])
        self.assertEqual(matches[0].identifiers["lccn"],["2026123456"])
        self.assertIn("Example book",matches[0].label)
        request=mocked.call_args.args[0]
        self.assertIn("bath.isbn",request.full_url)
        self.assertIn("recordSchema=marcxml",request.full_url)

    def test_name_authority_candidates_never_auto_merge(self):
        adapter=LibraryOfCongressAdapter(lcdb_url="http://loc.invalid/LCDB",naf_url="http://loc.invalid/NAF")
        with patch("cyber_library.sources.loc.urlopen",return_value=FakeResponse(MADS)) as mocked:
            matches=adapter.reconcile_author("Example Ada",10)
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0].source_id,"n12345678")
        self.assertFalse(matches[0].metadata["auto_merge"])
        self.assertTrue(matches[0].metadata["candidate_only"])
        request=mocked.call_args.args[0]
        self.assertIn("bath.personalName",request.full_url)
        self.assertIn("recordSchema=mads",request.full_url)


if __name__=="__main__":unittest.main()

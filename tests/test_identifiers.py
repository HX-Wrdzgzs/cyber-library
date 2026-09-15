import unittest
from cyber_library.identifiers import InvalidISBN,is_valid_isbn10,is_valid_isbn13,normalize_isbn
class IdentifierTest(unittest.TestCase):
    def test_isbn10_to_13(self):
        self.assertTrue(is_valid_isbn10("0-306-40615-2")); self.assertEqual(normalize_isbn("0-306-40615-2"),"9780306406157")
    def test_isbn13(self): self.assertTrue(is_valid_isbn13("978-0-306-40615-7"))
    def test_rejects_bad_checksum(self):
        with self.assertRaises(InvalidISBN): normalize_isbn("9780306406158")
    def test_rejects_non_isbn_ean(self): self.assertFalse(is_valid_isbn13("4006381333931"))
if __name__ == "__main__": unittest.main()

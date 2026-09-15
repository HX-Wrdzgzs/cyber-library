import unittest
from cyber_library.identifiers import InvalidISBN,is_valid_isbn10,is_valid_isbn13,normalize_isbn
class T(unittest.TestCase):
    def test_10(self):
        self.assertTrue(is_valid_isbn10("0-306-40615-2")); self.assertEqual(normalize_isbn("0-306-40615-2"),"9780306406157")
    def test_13(self):
        self.assertTrue(is_valid_isbn13("978-0-306-40615-7"))
    def test_bad(self):
        with self.assertRaises(InvalidISBN): normalize_isbn("9780306406158")

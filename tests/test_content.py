import tempfile
import unittest
import zipfile
from pathlib import Path

from cyber_library.content import ContentError, extract_document


class ContentTest(unittest.TestCase):
    def test_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.md"
            path.write_text("# First\n" + ("This is a sufficiently long paragraph about systems and books. " * 10) + "\n# Second\n" + ("Another section contains more source text for analysis. " * 10), encoding="utf-8")
            doc = extract_document(path, "user-provided")
            self.assertIn("First", doc.headings)
            self.assertTrue(doc.content_hash.startswith("sha256:"))

    def test_epub_minimal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.epub"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("META-INF/container.xml", """<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>""")
                zf.writestr("OEBPS/content.opf", """<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>""")
                zf.writestr("OEBPS/c1.xhtml", "<html><body><h1>Chapter One</h1><p>" + ("Readable EPUB content for testing. " * 20) + "</p></body></html>")
            doc = extract_document(path, "open-license")
            self.assertIn("Chapter One", doc.headings)
            self.assertGreater(len(doc.text), 100)

    def test_rights_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.txt"
            path.write_text("x" * 200, encoding="utf-8")
            with self.assertRaises(ContentError): extract_document(path, "unknown")


if __name__ == "__main__": unittest.main()

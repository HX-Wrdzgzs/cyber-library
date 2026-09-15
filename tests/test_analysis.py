import unittest

from cyber_library.intelligence import catalog_analysis, full_text_analysis, source_analysis
from cyber_library.models import Analysis, BookRecord, Edition, EvidenceItem, Work


class AnalysisTest(unittest.TestCase):
    def setUp(self):
        self.record = BookRecord(
            Work("work:test", "Example Systems", authors=["A. Author"], subjects=["Computer science", "Software engineering"], categories=["Computer Science"], source_refs=["source:work"]),
            Edition("edition:test", "work:test", "Example Systems", publishers=["Example Press"], table_of_contents=["Foundations", "Architecture", "Operations"], source_refs=["source:edition"]),
            Analysis(sources=["source:edition"]),
        )

    def test_catalog_analysis_does_not_invent(self):
        analysis = catalog_analysis(self.record)
        self.assertEqual(analysis.level, "L1")
        self.assertIsNone(analysis.detailed)
        self.assertIn("Computer Science", analysis.categories)

    def test_source_analysis_uses_evidence(self):
        self.record.evidence = [EvidenceItem("description", "This book explains software architecture and reliable systems. It compares design choices and operational trade-offs.", "source:description")]
        analysis = source_analysis(self.record)
        self.assertEqual(analysis.level, "L2")
        self.assertTrue(analysis.summary)
        self.assertEqual(analysis.table_of_contents[0], "Foundations")
        self.assertIn("source:description", analysis.sources)

    def test_full_text_analysis(self):
        text = """
# Foundations
Reliable systems require clear interfaces. Architecture shapes how components interact, fail, and recover. Good designs make assumptions explicit.

# Operations
Operators need observability and repeatable procedures. Monitoring helps teams understand failures. Automation can reduce repetitive work when its boundaries are clear.
""" * 20
        analysis = full_text_analysis(self.record, text, ["Foundations", "Operations"], "user-provided", "file:test")
        self.assertEqual(analysis.level, "L3")
        self.assertTrue(analysis.summary)
        self.assertTrue(analysis.chapter_summaries)
        self.assertIn("file:test", analysis.sources)


if __name__ == "__main__": unittest.main()

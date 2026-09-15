import unittest
from cyber_library.taxonomy import classify
class TaxonomyTest(unittest.TestCase):
    def test_computer_science(self): self.assertIn('Computer Science',classify(['Artificial intelligence','Machine learning'],'Neural Networks'))
    def test_chinese_literature(self): self.assertIn('Literature',classify(['中国文学','小说'],'测试'))
    def test_unclassified(self): self.assertEqual(classify([],'Untitled'),['Unclassified'])
if __name__=='__main__': unittest.main()

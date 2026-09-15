import json
import unittest
from pathlib import Path
class SampleRecordTest(unittest.TestCase):
    def test_sample_matches_v1_shape(self):
        record=json.loads(Path('data/samples/book.sample.json').read_text(encoding='utf-8'))
        self.assertIn('work',record); self.assertIn('edition',record); self.assertIn('analysis',record); self.assertIn('evidence',record); self.assertEqual(record['edition']['work_id'],record['work']['id']); self.assertIn(record['analysis']['level'],{'L1','L2','L3'}); self.assertTrue(record['analysis']['tags'])
if __name__=='__main__': unittest.main()

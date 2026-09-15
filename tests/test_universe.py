import unittest
from cyber_library.universe import GRID_SIZE,isbn_space_point
class UniverseTest(unittest.TestCase):
    def test_point_is_deterministic_and_bounded(self):
        a=isbn_space_point('9780306406157'); b=isbn_space_point('9780306406157'); self.assertEqual(a,b); self.assertGreaterEqual(a.x,0); self.assertLessEqual(a.x,1); self.assertGreaterEqual(a.y,0); self.assertLessEqual(a.y,1); self.assertGreaterEqual(a.grid_x,0); self.assertLess(a.grid_x,GRID_SIZE)
if __name__=='__main__': unittest.main()

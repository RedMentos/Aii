import unittest
from v13 import lora_session as L

class T(unittest.TestCase):
    def test_halves_interleaved(self):
        a, b = L.split_halves(7); self.assertEqual(a, [0, 2, 4, 6]); self.assertEqual(b, [1, 3, 5])
    def test_combine(self):
        c, n = L.combine([1., 1., 1., 1.]); self.assertEqual((c, n), (1., 0.))
        c, n = L.combine([1., 0., 1., 0.]); self.assertAlmostEqual(c, .5); self.assertAlmostEqual(n, .5)
        c, n = L.combine([.8, .6]); self.assertAlmostEqual(c, .7); self.assertAlmostEqual(n, .1)
if __name__ == '__main__': unittest.main()

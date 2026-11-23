import unittest
from v13.measured_prefill import Sample, forecast

class TestForecast(unittest.TestCase):
    def test_unverified(self):
        self.assertEqual(forecast('C3',617,30,5,[Sample('C3',617,28.72)]),('UNVERIFIED',0))
    def test_role_isolation(self):
        self.assertEqual(forecast('C3',100,30,5,[Sample('B1',100,5,True)]),('UNVERIFIED',0))
    def test_reduce(self):
        self.assertEqual(forecast('C3',600,30,5,[Sample('C3',600,30,True)]),('REDUCE_UPSTREAM',500))
    def test_defer(self):
        self.assertEqual(forecast('C3',100,2,1,[Sample('C3',100,10,True)]),('DEFER',0))
    def test_slowest(self):
        s=[Sample('C3',100,1,True),Sample('C3',100,10,True)]
        self.assertEqual(forecast('C3',100,8,3,s),('REDUCE_UPSTREAM',50))
    def test_invalid(self):
        with self.assertRaises(ValueError): Sample('C3',0,1,True)

import tempfile
import unittest
from pathlib import Path
from v13.temporal_outcome import Expectation, TemporalLedger

class TestTemporal(unittest.TestCase):
    def test_restart_and_omission(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'ledger.json'
            a = TemporalLedger(p)
            a.add(Expectation('a', 'source:1', 'done', 10, 20, .8))
            self.assertEqual(TemporalLedger(p).resolve('a', at=21, observable=True, outcome_ref='observation:1').error, -.8)
            self.assertEqual(TemporalLedger(p).rows['a'].status, 'OMITTED')
            with self.assertRaises(ValueError):
                TemporalLedger(p).resolve('a', at=22, observable=True, outcome_ref='observation:2')

    def test_censor_and_delayed(self):
        with tempfile.TemporaryDirectory() as d:
            a = TemporalLedger(Path(d)/'db')
            a.add(Expectation('a', 'source:1', 'done', 10, 20, .8))
            self.assertEqual(a.resolve('a', at=25).status, 'CENSORED')
            self.assertIsNone(a.rows['a'].error)
            a.add(Expectation('b', 'source:2', 'done', 10, 20, .8))
            self.assertEqual(a.resolve('b', at=25, observed='done', outcome_ref='obs:2').status, 'DELAYED')
            self.assertAlmostEqual(a.rows['b'].error, .2)

    def test_invalid_and_capacity(self):
        with self.assertRaises(ValueError):
            Expectation('a', 'src', 'x', 1, 2, float('nan'))
        with tempfile.TemporaryDirectory() as d:
            a = TemporalLedger(Path(d)/'db', max_pending=1)
            a.add(Expectation('a','s','x',1,2,.5))
            with self.assertRaises(ValueError):
                a.add(Expectation('b','s','x',1,2,.5))
            self.assertEqual(a.resolve('a',at=3,observable=True).status, 'CENSORED')

if __name__ == '__main__':
    unittest.main()

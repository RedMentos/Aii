"""Synthetic persistence and evidence-admission checks; not Android or JEPA proof."""
import tempfile
import unittest
from pathlib import Path
from v14.code.temporal_outcomes import TemporalOutcomes

class TestTemporalOutcomes(unittest.TestCase):
    def test_censored_vs_omitted_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'world.sqlite'
            x=TemporalOutcomes(p)
            x.expect(id='a',source='T8:source-a',owner='WORLD',outcome='screen changed',earliest=10,deadline=20,probability=.8,created=9)
            self.assertEqual(x.pending_due(21)[0]['id'],'a')
            with self.assertRaises(ValueError):
                x.resolve('a',status='OMITTED',observed_at=21,evidence=['T8:obs'],observation_complete=False)
            x.resolve('a',status='CENSORED',observed_at=21,evidence=[])
            self.assertIsNone(TemporalOutcomes(p).read('a')['error'])
            x.expect(id='b',source='T8:source-b',owner='ACTION',outcome='ack',earliest=10,deadline=20,probability=.7,created=9)
            self.assertAlmostEqual(x.resolve('b',status='OMITTED',observed_at=21,evidence=['T8:interval-verified'],observation_complete=True)['prediction_error'],-.7)
            self.assertEqual(TemporalOutcomes(p).read('b')['status'],'OMITTED')
            with self.assertRaises(ValueError):
                x.resolve('b',status='OBSERVED',observed_at=21,evidence=['duplicate'])

    def test_late_and_transaction_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            x=TemporalOutcomes(Path(d)/'x.sqlite')
            x.expect(id='a',source='src',owner='WORLD',outcome='o',earliest=1,deadline=2,probability=.4,created=0)
            with self.assertRaises(ValueError):
                x.resolve('a',status='OBSERVED',observed_at=3,evidence=['late'])
            self.assertEqual(x.read('a')['status'],'PENDING')
            self.assertAlmostEqual(x.resolve('a',status='DELAYED',observed_at=3,evidence=['late'])['prediction_error'],.6)

if __name__=='__main__':
    unittest.main()

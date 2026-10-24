"""Run62 actual SleepCycle callsite test. Requires complete V13 checkout."""
import copy
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from v13.sleep import SleepCycle, default_policy, empty_schedule
from v13.sleep_trace_decay import DAY


class _DB:
    def execute(self, _query):
        return self
    def fetchone(self):
        return (0, 0, 0)


class _Store:
    def __init__(self):
        self.mutex = threading.RLock()
        self.db = _DB()
    def one(self, _query):
        return {'n': 0}
    def prune_telemetry(self):
        return 0


class _Queue:
    def sync(self, _state, _policy):
        return 0, False


def _item(priority=1.0):
    return {'created':0., 'last':None, 'expires':100*DAY,
            'retired':None, 'priority':priority, 'type':'EPISODIC',
            'next_due':0., 'reps':0, 'failures':0, 'last_outcome':None}


class SleepCIntegration(unittest.TestCase):
    def test_production_callsite_idempotence(self):
        with TemporaryDirectory() as td:
            cycle = SleepCycle.__new__(SleepCycle)
            cycle.s = _Store()
            cycle.home = Path(td)
            cycle.queue = _Queue()
            cycle.clock = lambda: 10 * DAY
            cycle.plasticity = None
            cycle.neuromod = None
            cycle._checkpoint = lambda *a, **kw: None
            cycle._homeostasis = lambda *a, **kw: {'changes': {}}
            st = empty_schedule()
            st['items'] = {'r1': _item()}
            policy = default_policy()
            first = cycle.sleep_c(st, policy)
            self.assertEqual(first['status'], 'DONE')
            p = st['items']['r1']['priority']
            self.assertAlmostEqual(p, .98**10)
            second = cycle.sleep_c(st, policy)
            self.assertEqual(second['status'], 'DONE')
            self.assertEqual(st['items']['r1']['priority'], p)
            self.assertEqual(second['trace_decay']['decayed'], 0)

    def test_corrupt_second_item_does_not_partially_decay_first(self):
        with TemporaryDirectory() as td:
            cycle = SleepCycle.__new__(SleepCycle)
            cycle.s = _Store(); cycle.home = Path(td); cycle.queue = _Queue()
            cycle.clock = lambda: 10 * DAY
            cycle.plasticity = None; cycle.neuromod = None
            cycle._checkpoint = lambda *a, **kw: None
            cycle._homeostasis = lambda *a, **kw: {'changes': {}}
            st = empty_schedule()
            st['items'] = {'r1': _item(), 'r2': _item(priority=float('nan'))}
            before = copy.deepcopy(st['items']['r1'])
            with self.assertRaises(ValueError): cycle.sleep_c(st, default_policy())
            self.assertEqual(st['items']['r1'], before)


if __name__ == '__main__': unittest.main()

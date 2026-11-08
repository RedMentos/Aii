"""Adversarial persistence and identity tests for the review-only C5 ledger."""
import copy
import unittest
from v13 import c5_feedback_ledger_candidate as L

class LedgerIntegrityTests(unittest.TestCase):
    def test_delimiter_alias_is_rejected(self):
        # Without this guard, ('a|b','c') and ('a','b|c') share an aggregate key.
        for ctx, action in [('a|b', 'c'), ('a', 'b|c')]:
            with self.subTest(ctx=ctx, action=action), self.assertRaises(ValueError):
                L.record(L.empty(), 'e1', ctx, action, 10)

    def test_reject_malformed_persisted_state_on_both_paths(self):
        base = L.record(L.empty(), 'e1', 'ctx', 'act', 10)
        corrupt = []
        for field, value in [('context','ctx|other'), ('action_id','act|other'),
                             ('score',float('nan')), ('score',True)]:
            s = copy.deepcopy(base)
            s['ratings']['e1'][field] = value
            corrupt.append(s)
        for bad_id in ('', 'x'*257):
            s = copy.deepcopy(base)
            s['ratings'][bad_id] = s['ratings'].pop('e1')
            corrupt.append(s)
        s = copy.deepcopy(base)
        s['ratings']['e1']['extra'] = 'untrusted'
        corrupt.append(s)
        s = copy.deepcopy(base)
        s['unexpected'] = 1
        corrupt.append(s)
        for state in corrupt:
            with self.subTest(state=repr(state)[:90]):
                with self.assertRaises(ValueError):
                    L.aggregate(state)
                with self.assertRaises(ValueError):
                    L.record(state, 'e2', 'ctx', 'act', 1)

    def test_valid_existing_data_preserved(self):
        s = L.record(L.empty(), 'e1', 'ctx', 'act', 10)
        s = L.record(s, 'e2', 'ctx', 'act', 1)
        self.assertEqual(L.aggregate(s)['ctx|act'],
                         {'n':2, 'human_approval':.5, 'human_correction':.5})
        self.assertEqual(L.record(s, 'e1', 'ctx', 'act', 10), s)

if __name__ == '__main__':
    unittest.main()

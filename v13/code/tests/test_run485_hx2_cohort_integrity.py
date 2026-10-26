"""Run485 cross-review: HX2 cannot select NaN or silently discard holdout rows."""
import unittest
from v13.agi import harness_probe as HP


def full_axes():
    return {'both_exact': {'ref': {'a':[.2,.2,.2], 'b':[.2,.2,.2]},
                           'chosen': {'a':[.8,.8,.8], 'b':[.8,.8,.8]},
                           'unguided': {'a':[.2,.2,.2], 'b':[.2,.2,.2]}}}


class HX2Integrity(unittest.TestCase):
    WRONG={'ref':0,'chosen':0,'unguided':0}

    def test_valid_complete_holdout_can_pass(self):
        self.assertEqual(HP.holdout_gate(full_axes(),'both_exact',self.WRONG,True)['status'],'HX2_PASS')

    def test_nan_probe_cannot_be_chosen(self):
        for v in (float('nan'),float('inf'),True,-.1,1.1):
            with self.subTest(value=v):
                r=HP.compose({'V1':v},.5)
                self.assertEqual(r['status'],'INVALID_PROBE')
                self.assertIsNone(r['choice'])

    def test_bad_reference_or_gain_rejected(self):
        self.assertEqual(HP.compose({'V1':.8},float('nan'))['status'],'INVALID_PROBE')
        self.assertEqual(HP.compose({'V1':.8},.5,min_gain=float('nan'))['status'],'INVALID_PROBE')

    def test_missing_holdout_task_never_passes(self):
        axes=full_axes();del axes['both_exact']['chosen']['b']
        self.assertEqual(HP.holdout_gate(axes,'both_exact',self.WRONG,True)['status'],'HX2_INVALID')
        with self.assertRaises(ValueError):
            HP.paired(axes['both_exact']['chosen'],axes['both_exact']['ref'])

    def test_missing_seed_never_passes(self):
        axes=full_axes();axes['both_exact']['chosen']['a'].pop()
        self.assertEqual(HP.holdout_gate(axes,'both_exact',self.WRONG,True)['status'],'HX2_INVALID')
        with self.assertRaises(ValueError):
            HP.paired(axes['both_exact']['chosen'],axes['both_exact']['ref'])

    def test_nan_nonprimary_axis_rejected(self):
        axes=full_axes()
        axes['b2_only']={'ref':{'a':[.3]},'chosen':{'a':[float('nan')]},
                         'unguided':{'a':[.3]}}
        self.assertEqual(HP.holdout_gate(axes,'both_exact',self.WRONG,True)['status'],'HX2_INVALID')

    def test_wrong_counts_must_be_actual_nonnegative_integers(self):
        for wrong in ({'ref':0,'chosen':True,'unguided':0},
                      {'ref':0,'chosen':-1,'unguided':0},
                      {'ref':0,'chosen':0}):
            with self.subTest(wrong=wrong):
                self.assertEqual(HP.holdout_gate(full_axes(),'both_exact',wrong,True)['status'],'HX2_INVALID')

    def test_missing_axis_or_structural_false_invalid(self):
        self.assertEqual(HP.holdout_gate({},'both_exact',self.WRONG,True)['status'],'HX2_INVALID')
        self.assertEqual(HP.holdout_gate(full_axes(),'both_exact',self.WRONG,False)['status'],'HX2_INVALID')


if __name__=='__main__':
    unittest.main()

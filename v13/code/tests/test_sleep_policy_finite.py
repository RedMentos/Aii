import copy
import math
import unittest
from v13.sleep_policy_finite import validate_mix, validate_quiet_hours, normalized_quota

MIX = {'recent':.50,'protected_old':.35,'failure':.15}


class SleepPolicyFiniteTests(unittest.TestCase):
    def test_valid_mix_unchanged(self):
        for m in [MIX, {'recent':1,'protected_old':0,'failure':0},
                  {'recent':.01,'protected_old':.02,'failure':.03}]:
            before = copy.deepcopy(m)
            self.assertIsNone(validate_mix(m, MIX))
            self.assertEqual(m, before)

    def test_nan_rejected(self):
        for key in MIX:
            m = dict(MIX); m[key] = float('nan')
            with self.subTest(key=key), self.assertRaises(ValueError): validate_mix(m, MIX)

    def test_infinities_rejected(self):
        for bad in [float('inf'), -float('inf')]:
            m = dict(MIX); m['recent'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError): validate_mix(m, MIX)

    def test_sum_overflow_rejected(self):
        with self.assertRaises(ValueError):
            validate_mix(dict.fromkeys(MIX, 1e308), MIX)

    def test_negative_and_zero_rejected(self):
        for m in [{'recent':-1,'protected_old':1,'failure':1}, dict.fromkeys(MIX,0)]:
            with self.assertRaises(ValueError): validate_mix(m, MIX)

    def test_bool_and_string_rejected(self):
        for bad in [True, False, '0.2', None]:
            m = dict(MIX); m['recent'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError): validate_mix(m, MIX)

    def test_nonmapping_and_wrong_keys_rejected(self):
        for bad in [[], None, ['recent'], {'recent':1}, {'recent':1,'protected_old':1,'failure':1,'extra':1}]:
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError): validate_mix(bad, MIX)

    def test_huge_finite_weight_has_stable_quota(self):
        m = {'recent':1e308,'protected_old':0.,'failure':0.}
        self.assertEqual(normalized_quota(m, 8), {'recent':8.0,'protected_old':0.0,'failure':0.0})

    def test_invalid_batch_size_refused(self):
        for n in [-1,True,1.5]:
            with self.assertRaises(ValueError): normalized_quota(MIX,n)

    def test_quiet_hours_valid(self):
        for q in [None,[0,0],[0,23],[23,0]]:
            self.assertIsNone(validate_quiet_hours(q))

    def test_quiet_hours_bools_rejected(self):
        for q in [[True, 22], [1, False]]:
            with self.subTest(q=q), self.assertRaises(ValueError): validate_quiet_hours(q)

    def test_quiet_hours_invalid(self):
        for q in [(1,2),[24,0],[-1,1],[1],[1,2,3],['1',2],1]:
            with self.subTest(q=q), self.assertRaises(ValueError): validate_quiet_hours(q)


if __name__ == '__main__': unittest.main()

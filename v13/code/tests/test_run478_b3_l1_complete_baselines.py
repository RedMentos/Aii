import unittest
from v13.b3bridge import l1_gate
from scripts.run478_b3_l1_complete_baselines import evaluate


def full():
    acc = {'NO_MESSAGE':[0.,0.,0.,0.], 'LATENT':[1.,1.,1.,1.],
           'LATENT_SHUFFLED':[0.,0.,0.,0.],
           'LATENT_RANDOM':[0.,0.,0.,0.],
           'EXACT':[0.,0.,0.,0.], 'CONTROL':[0.,0.,0.,0.],
           'SYMBOLIC':[0.,0.,0.,0.]}
    return {'acc':acc, 'bytes':{k:0 for k in acc},
            'role_drop':0., 'ood_rate':0., 'reload_identical':True}


class L1Completeness(unittest.TestCase):
    def test_complete_table_diagnostic_never_promotes(self):
        out=evaluate(full())
        self.assertEqual(out['diagnostic_l1_verdict'],'PASS')
        self.assertFalse(out['canonical_gate_pass'])
        self.assertEqual(out['latent_authority'],0)
        self.assertEqual(out['b3_l1'],'FAIL')

    def test_missing_controls_can_pass_old_gate_but_not_candidate(self):
        t=full()
        for key in ('EXACT','CONTROL','SYMBOLIC','LATENT_SHUFFLED','LATENT_RANDOM'):
            del t['acc'][key];del t['bytes'][key]
        self.assertEqual(l1_gate(t)['verdict'],'PASS')
        with self.assertRaisesRegex(ValueError,'B3_REQUIRED_BASELINE_MISSING'):
            evaluate(t)

    def test_shortened_seed_arm_refused(self):
        t=full();t['acc']['SYMBOLIC']=t['acc']['SYMBOLIC'][:2]
        with self.assertRaisesRegex(ValueError,'B3_SEED_COVERAGE_MISMATCH'):
            evaluate(t)

    def test_missing_bytes_cannot_get_free_utility(self):
        t=full();del t['bytes']['LATENT']
        with self.assertRaisesRegex(ValueError,'B3_REQUIRED_BASELINE_MISSING'):
            evaluate(t)

    def test_nonfinite_bool_and_out_of_range_refused(self):
        for value in (float('nan'),float('inf'),True,-0.1,1.1):
            t=full();t['acc']['EXACT'][0]=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'B3_ACC_NONFINITE_OR_INVALID'):
                evaluate(t)

    def test_missing_or_forged_role_ood_and_reload_refused(self):
        for key,value,reason in [('role_drop',None,'B3_MEASUREMENT_MISSING_OR_INVALID'),
                                 ('ood_rate',float('nan'),'B3_MEASUREMENT_MISSING_OR_INVALID'),
                                 ('reload_identical',1,'B3_RELOAD_MEASUREMENT_MISSING')]:
            t=full();t[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,reason):
                evaluate(t)

    def test_extra_channel_not_part_of_frozen_cohort(self):
        t=full();t['acc']['EXTRA']=[1.]*4;t['bytes']['EXTRA']=0
        with self.assertRaisesRegex(ValueError,'B3_CHANNEL_COHORT_MISMATCH'):
            evaluate(t)


if __name__=='__main__':unittest.main()

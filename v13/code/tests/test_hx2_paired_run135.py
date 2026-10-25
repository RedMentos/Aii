"""Run135 HX2 pure same-task, same-seed blind comparison contract tests."""
import unittest
from v13.agi.hx2_paired_shadow import compare


def tasks(n=24):
    return [{'id':f't{i}', 'prompt':f'Question {i}', 'group':'general' if i%2 else 'domain', 'split':'holdout'} for i in range(n)]


def quality_judge(task, items):
    # Deliberately inspect only anonymous label/output, not original arm.
    best=max(items,key=lambda x: int(x['output'].split('quality=')[-1]))
    return best['label']


class HX2Pairs(unittest.TestCase):
    def test_same_task_seed_all_arms_and_control(self):
        calls=[]
        def gen(prompt,arm,seed):
            calls.append((prompt,arm,seed))
            return {'reference':'quality=1','guided':'quality=3','unguided':'quality=2'}[arm]
        out=compare(tasks(),gen,quality_judge,seed=13525)
        self.assertEqual(len(calls),24*3)
        for i in range(24):
            a,b,c=calls[i*3:i*3+3]
            self.assertEqual({a[1],b[1],c[1]},{'reference','guided','unguided'})
            self.assertEqual(a[0],b[0]);self.assertEqual(b[0],c[0])
            self.assertEqual(a[2],b[2]);self.assertEqual(b[2],c[2])
        self.assertEqual(out['gate'],'UNVERIFIED')
        self.assertEqual(out['claim_limit'],'SYNTHETIC_OR_SOFTWARE_ONLY')
        self.assertEqual(out['axes']['general']['guided_vs_reference']['wins'],12)
        self.assertEqual(out['axes']['domain']['guided_vs_reference']['wins'],12)
        self.assertEqual(out['axes']['general']['unguided_vs_reference']['wins'],12)
        self.assertTrue(all('prompt' not in row and 'output' not in row for row in out['rows']))
        self.assertTrue(all(all(p['verified'] for p in row['pairs'].values()) for row in out['rows']))

    def test_position_biased_judge_never_picks(self):
        def gen(prompt,arm,seed):return {'reference':'quality=1','guided':'quality=3','unguided':'quality=2'}[arm]
        out=compare(tasks(4),gen,lambda task,items:'A')
        self.assertEqual(out['axes']['general']['guided_vs_reference']['wins'],0)
        self.assertEqual(out['axes']['general']['guided_vs_reference']['inconsistent'],2)
        self.assertEqual(out['gate'],'UNVERIFIED')

    def test_identical_outputs_are_ties(self):
        out=compare(tasks(4),lambda prompt,arm,seed:'same',quality_judge)
        self.assertEqual(out['axes']['domain']['guided_vs_reference']['ties'],2)
        self.assertEqual(out['axes']['general']['guided_vs_reference']['ties'],2)
        self.assertEqual(out['gate'],'UNVERIFIED')

    def test_unknown_label_abstains(self):
        out=compare(tasks(2),lambda prompt,arm,seed:arm,lambda task,items:'Q')
        self.assertEqual(out['axes']['domain']['guided_vs_reference']['no_pick'],1)
        self.assertEqual(out['gate'],'UNVERIFIED')

    def test_invalid_input_refused_before_model(self):
        calls=[]
        def gen(*a):calls.append(a);return 'a'
        for bad in [tasks(1)+tasks(1), [{'id':'a','prompt':'x','group':'general','split':'train'}],
                    [{'id':'a','prompt':'x','group':'unknown','split':'holdout'}],
                    [{'id':'a','prompt':'x','group':'general','split':'holdout'}]*65]:
            with self.assertRaises(ValueError):compare(bad,gen,quality_judge)
        self.assertEqual(calls,[])

    def test_generator_error_no_false_signal(self):
        def gen(prompt,arm,seed):
            if arm=='guided':raise RuntimeError('model down')
            return 'quality=1'
        out=compare(tasks(2),gen,quality_judge)
        self.assertEqual(out['status'],'INCOMPLETE')
        self.assertEqual(out['gate'],'UNVERIFIED')
        self.assertEqual(out['rows'][0]['status'],'GENERATION_ERROR')

    def test_unguided_control_can_defeat_guided_signal(self):
        def gen(prompt,arm,seed):
            return {'reference':'quality=1','guided':'quality=2','unguided':'quality=3'}[arm]
        out=compare(tasks(60),gen,quality_judge,seed=13525)
        self.assertEqual(out['axes']['general']['guided_vs_reference']['wins'],30)
        self.assertEqual(out['axes']['general']['guided_vs_unguided']['losses'],30)
        self.assertEqual(out['signal'],'NOT_SUPPORTED_OR_UNMEASURED')
        self.assertEqual(out['gate'],'UNVERIFIED')

    def test_tiny_cohort_cannot_create_positive_diagnostic(self):
        def gen(prompt,arm,seed):
            return {'reference':'quality=1','guided':'quality=3','unguided':'quality=2'}[arm]
        out=compare(tasks(6),gen,quality_judge,seed=13525)
        self.assertEqual(out['signal'],'NOT_SUPPORTED_OR_UNMEASURED')
        self.assertEqual(out['gate'],'UNVERIFIED')

    def test_synthetic_positive_is_never_gate_pass(self):
        def gen(prompt,arm,seed):return {'reference':'quality=1','guided':'quality=3','unguided':'quality=2'}[arm]
        out=compare(tasks(60),gen,quality_judge,seed=13525)
        self.assertEqual(out['gate'],'UNVERIFIED')
        self.assertEqual(out['signal'],'SYNTHETIC_DIAGNOSTIC_ONLY')
        for group in ('general','domain'):
            self.assertGreater(out['axes'][group]['guided_vs_reference']['lower95'],.5)
        print('RUN135_SYNTHETIC positive_60_pairs_but_gate_UNVERIFIED')


if __name__=='__main__':unittest.main()

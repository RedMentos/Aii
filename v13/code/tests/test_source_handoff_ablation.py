"""Ablation lifecycle/transport fixtures; no real native calls in unit tests."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import source_handoff_ablation as ablation
from v13.common import digest, dumps
from v13.config import validate
from v13.runners import RunnerPool


class HandoffAblation(unittest.TestCase):
    def test_fixed_cases_are_source_disjoint_and_unknown_controls_are_strict(self):
        from tests.integration_step2_utility import FIXTURES
        self.assertFalse({f['id'] for f in ablation.FIXTURES}&{f['id'] for f in FIXTURES})
        validate(ablation.CONFIG)
        for fixture in ablation.FIXTURES:
            if fixture['control'] in ('missing_rule','corrupt_prior'):
                self.assertEqual(fixture['oracle']['action'], 'UNKNOWN')
                self.assertTrue(all(o['remaining'] is None and o['eligible'] is None for o in fixture['oracle']['options']))

    def test_actual_native_context_excludes_oracle_and_unoffered_prior(self):
        fixture=copy.deepcopy(ablation.FIXTURES[0])
        fixture['prior']='PRIVATE_PRIOR_NOT_DELIVERED'
        fixture['oracle']={'marker':'PRIVATE_ORACLE_NOT_DELIVERED'}
        messages=ablation.consumer_messages(fixture,[{'hypothesis':'fallible','verified_quotes':[]}])
        text=dumps(messages)
        self.assertNotIn('PRIVATE_PRIOR',text)
        self.assertNotIn('PRIVATE_ORACLE',text)
        self.assertIn(fixture['current'],messages[1]['content'])

    def test_ongoing_frozen_cohort_blocks_even_registration(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json'
            for report in ({'status':'RUNNING','rows':[{}]*70},{'status':'UTILITY_FAIL','rows':[{}]*69}):
                path.write_text(dumps(report))
                with self.assertRaisesRegex(ValueError,'not complete'):
                    ablation.ensure_frozen_cohort_complete(path)
            path.write_text(dumps({'status':'UTILITY_FAIL','rows':[{}]*70}))
            self.assertEqual(ablation.ensure_frozen_cohort_complete(path)['rows'],70)

    def test_resume_preserves_failures_and_rejects_mutated_recorded_output(self):
        row={'fixture':'Mira','arm':'baseline','status':'ERROR','score':{'utility':0.,'exact':False}}
        report={'preregistration_sha256':'fixed','rows':[row],'row_sha256':{'Mira/baseline':digest(dumps(row))}}
        self.assertEqual(ablation.validate_resume(report,'fixed'),{('Mira','baseline')})
        changed=copy.deepcopy(report);changed['rows'][0]['score']['utility']=1.
        with self.assertRaisesRegex(ValueError,'row bytes changed'):
            ablation.validate_resume(changed,'fixed')
        with self.assertRaisesRegex(ValueError,'preregistration changed'):
            ablation.validate_resume(report,'other')
        duplicate=copy.deepcopy(report);duplicate['rows'].append(row)
        with self.assertRaisesRegex(ValueError,'row keys invalid'):
            ablation.validate_resume(duplicate,'fixed')

    def fake_runner(self,pool,role,fixture):
        def generate(messages,*args,**kwargs):
            if role=='C3_LANGUAGE':return iter([dumps(fixture['oracle'])])
            query=json.loads(messages[1]['content'])
            previous=query.get('earlier_context',[])
            quotes=['Budget 61 euros.'] if previous and fixture['id']=='Mira' else []
            return iter([dumps({'summary':'A fallible reading.','quotes':quotes,'uncertainty':'Uncertain','needs_reentry':not bool(quotes)})])
        runner=SimpleNamespace(role=role,last_metrics={'status':'FINAL'},generate=generate,
                               unload=lambda:{'process_reaped':True},purpose='generate')
        pool.current=runner
        return runner

    def test_real_store_offline_row_exercises_all_four_arms_and_cold_release(self):
        arms,validator=ablation.arm_sources()
        fixture=ablation.FIXTURES[0]
        with tempfile.TemporaryDirectory() as temp:
            for arm in ablation.ARMS:
                def get(pool,role):return self.fake_runner(pool,role,fixture)
                with patch.object(ablation,'installed_links'),patch.object(RunnerPool,'get',get):
                    row=ablation.run_row(Path(temp)/arm,Path(temp)/'unused',fixture,arm,arms[arm],validator)
                self.assertEqual(row['status'],'RECORDED',row)
                self.assertTrue(row['processes_reaped'])
                self.assertEqual([p['role'] for p in row['process_releases']],['B2_GIST','B2_GIST','C3_LANGUAGE'])
                self.assertEqual(row['delivered_prior_quotes'][0]['text'],'Budget 61 euros.')
                self.assertFalse(row['oracle_visible_to_native'])

    def test_corrupt_prior_is_not_repaired_or_secretly_supplied(self):
        arms,validator=ablation.arm_sources()
        fixture=ablation.FIXTURES[3]
        with tempfile.TemporaryDirectory() as temp:
            def get(pool,role):return self.fake_runner(pool,role,fixture)
            with patch.object(ablation,'installed_links'),patch.object(RunnerPool,'get',get):
                row=ablation.run_row(Path(temp)/'corrupt',Path(temp)/'unused',fixture,'full_candidate',arms['full_candidate'],validator)
        self.assertEqual(row['status'],'RECORDED',row)
        self.assertEqual(row['available_earlier_sources'],[])
        self.assertEqual(row['delivered_prior_quotes'],[])
        self.assertTrue(row['checks']['corrupt_prior_not_delivered'])
        self.assertNotIn('Budget 71 euros.',dumps(row['consumer_messages']))

    def test_preregistration_is_written_before_first_inference_and_resume_skips_recorded_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);cohort=folder/'step2.json';out=folder/'ablation.json'
            cohort.write_text(dumps({'status':'UTILITY_FAIL','rows':[{}]*70}))
            argv=['ablation','--installed-home',str(folder/'installed'),'--step2-report',str(cohort),'--out',str(out)]
            calls=[]
            def infer(home,installed,fixture,arm,code,validator):
                registration=json.loads(out.with_suffix('.preregistration.json').read_text())
                self.assertEqual(registration['fixtures_sha256'],digest(dumps(ablation.FIXTURES)))
                self.assertEqual(registration['consumer_schema_sha256'],digest(dumps(ablation.SCHEMA)))
                self.assertFalse(registration['native_oracle_visibility'])
                self.assertEqual(registration['config']['seed'],13)
                calls.append((fixture['id'],arm))
                return {'fixture':fixture['id'],'arm':arm,'status':'ERROR','score':{'utility':0.,'exact':False}}
            with patch.object(ablation,'binding',return_value={'fixture_binding':'fixed'}),patch.object(ablation,'run_row',infer),patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()):
                ablation.main()
                first=out.read_bytes()
                self.assertEqual(len(calls),16)
                self.assertEqual(json.loads(first)['status'],'STRUCTURAL_FAIL')
                ablation.main()
                self.assertEqual(len(calls),16)
                self.assertEqual(out.read_bytes(),first)

    def test_register_only_never_calls_native_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);cohort=folder/'step2.json';out=folder/'ablation.json'
            cohort.write_text(dumps({'status':'UTILITY_FAIL','rows':[{}]*70}))
            argv=['ablation','--installed-home',str(folder/'installed'),'--step2-report',str(cohort),'--out',str(out),'--register-only']
            with patch.object(ablation,'binding',return_value={'fixture_binding':'fixed'}),patch.object(ablation,'run_row') as native,patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()):
                ablation.main()
            native.assert_not_called()
            self.assertTrue(out.with_suffix('.preregistration.json').exists())
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()

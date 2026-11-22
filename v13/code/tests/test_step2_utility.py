import copy
import unittest
from v13.utility import paired_utility,score_decision

class DecisionScore(unittest.TestCase):
    def setUp(self):
        self.oracle={'project':'Aurora','action':'A','options':[{'entity':'A','cost':40,'remaining':60,'days':2,'local':True,'eligible':True},{'entity':'B','cost':70,'remaining':30,'days':7,'local':False,'eligible':False}]}
    def test_exact_assignment_and_order(self):
        actual=copy.deepcopy(self.oracle);actual['options'].reverse()
        self.assertTrue(score_decision(actual,self.oracle)['exact'])
    def test_numbers_under_wrong_entity_do_not_pass(self):
        actual=copy.deepcopy(self.oracle);actual['options'][0]['remaining'],actual['options'][1]['remaining']=30,60
        result=score_decision(actual,self.oracle)
        self.assertFalse(result['exact']);self.assertEqual(result['contradiction_count'],2)
    def test_constraint_negations_and_selected_action_scored(self):
        actual=copy.deepcopy(self.oracle);actual['action']='B';actual['options'][1]['eligible']=True;actual['options'][1]['local']=True
        result=score_decision(actual,self.oracle);self.assertEqual(result['contradiction_count'],3)
    def test_bool_cannot_impersonate_number(self):
        actual=copy.deepcopy(self.oracle);actual['options'][0]['cost']=True
        self.assertFalse(score_decision(actual,self.oracle)['field_checks']['A.cost'])
    def test_unknown_cannot_fabricate_rest(self):
        oracle=copy.deepcopy(self.oracle);oracle['action']='UNKNOWN'
        for option in oracle['options']:option.update(remaining=None,eligible=None)
        actual=copy.deepcopy(oracle);actual['options'][0]['remaining']=0
        self.assertFalse(score_decision(actual,oracle)['exact']);self.assertTrue(score_decision(oracle,oracle)['exact'])
    def test_duplicate_entity_and_extras_rejected(self):
        actual=copy.deepcopy(self.oracle);actual['options'][1]['entity']='A'
        self.assertEqual(score_decision(actual,self.oracle)['utility'],0)
        actual=copy.deepcopy(self.oracle);actual['hidden']='text'
        self.assertEqual(score_decision(actual,self.oracle)['utility'],0)
    def test_ambiguous_duplicate_json_key_rejected(self):
        import json
        raw=json.dumps(self.oracle).replace('\"action\": \"A\"','\"action\": \"B\", \"action\": \"A\"')
        self.assertEqual(score_decision(raw,self.oracle)['utility'],0.)
    def test_incomplete_pairs_never_pass(self):
        self.assertFalse(paired_utility([{'variant':'both_exact','fixture':'one','score':{'utility':1}}],['one','two'])['complete'])
    def test_gain_requires_both_error_profiles(self):
        variants=['b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual']
        rows=[{'variant':v,'fixture':f,'score':{'utility':1 if v=='both_exact' else .5}} for v in variants for f in ['one','two']]
        self.assertFalse(paired_utility(rows,['one','two'])['scoped_utility_gate_pass'])
        for r in rows:
            if r['variant']=='b1_only':r['score']['utility']=.8 if r['fixture']=='one' else .2
            if r['variant']=='b2_only':r['score']['utility']=.2 if r['fixture']=='one' else .8
        self.assertTrue(paired_utility(rows,['one','two'])['scoped_utility_gate_pass'])
class ResumeGuards(unittest.TestCase):
    def test_changed_source_or_completed_row_refused(self):
        import importlib.util
        from pathlib import Path
        from v13.common import digest,dumps
        path=Path(__file__).with_name('integration_step2_utility.py')
        spec=importlib.util.spec_from_file_location('step2_native_proof',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        expected={key:[] for key in ('proof_kind','proof_version','source_hashes','fixture_sha256','variant_spec','config','device','installed_artifacts')}
        old=copy.deepcopy(expected);row={'fixture':'one','variant':'both_exact','raw_answer':'native raw'}
        old.update(rows=[row],row_sha256={'one:both_exact':digest(dumps(row))})
        self.assertEqual(module.validate_resume(old,expected),{('one','both_exact')})
        old['rows'][0]['raw_answer']='changed'
        with self.assertRaisesRegex(ValueError,'row bytes changed'):module.validate_resume(old,expected)
        old['rows'][0]['raw_answer']='native raw';old['installed_artifacts']={'changed':True}
        with self.assertRaisesRegex(ValueError,'installed_artifacts'):module.validate_resume(old,expected)
        old['installed_artifacts']=[]
        old['source_hashes']={'changed':True}
        with self.assertRaisesRegex(ValueError,'source_hashes'):module.validate_resume(old,expected)
    def test_same_launcher_with_changed_shared_library_cannot_resume(self):
        import importlib.util
        from pathlib import Path
        path=Path(__file__).with_name('integration_step2_utility.py')
        spec=importlib.util.spec_from_file_location('step2_library_resume',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        expected={key:[] for key in ('proof_kind','proof_version','source_hashes','fixture_sha256','variant_spec','config','device')}
        expected['installed_artifacts']={'runner_sha256':'identical launcher','runner_runtime_libraries_sha256':{'libllama-server-impl.so':'new hook'}}
        old=copy.deepcopy(expected);old.update(rows=[],row_sha256={})
        old['installed_artifacts']['runner_runtime_libraries_sha256']['libllama-server-impl.so']='old hook'
        with self.assertRaisesRegex(ValueError,'installed_artifacts'):module.validate_resume(old,expected)
    def test_actual_store_state_json_roundtrip_after_restart(self):
        import importlib.util
        import json
        import tempfile
        from pathlib import Path
        from v13.config import initialize
        from v13.store import Store
        path=Path(__file__).with_name('integration_step2_utility.py')
        spec=importlib.util.spec_from_file_location('step2_store_resume',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);initialize(home);store=Store(home)
            try:
                store.set_state('B1_DETAIL:example',{'retained_offer_ids':['real-state-id'],'offer':{'summary':'unit persistence state'}})
                before={'B1_DETAIL':store.state('B1_DETAIL:example'),'B2_GIST':store.state('B2_GIST:example',{})}
                recorded=json.loads(json.dumps(before))
            finally:store.close()
            reopened=Store(home)
            try:
                actual={'B1_DETAIL':reopened.state('B1_DETAIL:example'),'B2_GIST':reopened.state('B2_GIST:example',{})}
                self.assertNotEqual(actual,recorded)
                self.assertTrue(module.same_persisted_state(actual,recorded))
                recorded['B1_DETAIL'][0]['retained_offer_ids'].append('tampered')
                self.assertFalse(module.same_persisted_state(actual,recorded))
            finally:reopened.close()
    def test_preregistered_corpus_oracles_and_temporal_mix(self):
        import importlib.util
        from pathlib import Path
        path=Path(__file__).with_name('integration_step2_utility.py')
        spec=importlib.util.spec_from_file_location('step2_native_fixtures',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(len(module.FIXTURES),10)
        self.assertEqual(sum(f['temporal_mode']=='CURRENT_EXPLICIT_OVERRIDE' for f in module.FIXTURES),4)
        self.assertEqual({f['oracle']['action'] for f in module.FIXTURES},{'A','B','NONE','UNKNOWN'})
        self.assertTrue(all(score_decision(f['oracle'],f['oracle'])['exact'] for f in module.FIXTURES))
if __name__=='__main__':unittest.main()

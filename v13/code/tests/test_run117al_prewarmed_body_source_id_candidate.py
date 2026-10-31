"""Run117AL seed1071 prewarming before immutable source-ID Store epoch."""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from scripts import run117al_prewarmed_body_source_id_native as native
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from tests.test_run117ah_body_source_id_candidate import choose
from v13.b1b2_source_id_quote_candidate import select, KIND
from v13.b1b2_source_id_event_binding_candidate import select_bound

FIXTURE=Path(__file__).resolve().parents[1]/(
    'docs/fixtures/RUN117AL_PREWARMED_BODY_SOURCE_ID_SEED1071.json')
SHA='be5cadca42348bd42b3a9ed1c553c59e2bd9684966608c45c320d3cadb577bb5'
IDS=('Helion','Indigo','Juniper','Kestrel','Lumen','Meridian')


def rows():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==SHA
    data=json.loads(FIXTURE.read_text())
    assert data['schema']=='v13.run117al.body_source_id_seed1071.v1'
    assert data['seed']==1071 and data['roles']==['B1_DETAIL','B2_GIST']
    assert tuple(x['id'] for x in data['rows'])==IDS
    assert native.fixture(FIXTURE)==data['rows']
    for row in data['rows']:
        assert row['prior'].count(row['policy_span'])==1
        assert row['current'].count(row['option_span'])==1
        assert row['prior'].startswith('Project '+row['id'])
        assert row['current'].startswith('Project '+row['id'])
        assert 'oracle' not in row['prior'] and 'oracle' not in row['current']
    return data['rows']


class PrewarmTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.row=rows()[0]
        self.r=QuoteRuntime(Path(self.tmp.name)/'home',self.row)
        self.r.cfg.update(OVERRIDES)
        self.prior=self.r.store.event(self.r.session,self.row['prior'])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def lifecycle_assigned(self):
        # The real RunnerPool._port -> BodyFabric.ports.event uses Store state.
        state,version=self.r.store.state('T13_BODY_PORTS',None)
        self.r.store.set_state('T13_BODY_PORTS',
                               {'synthetic_ASSIGNED':(state or {}).get(
                                   'synthetic_ASSIGNED',0)+1},
                               expected=version)

    def assert_no_authority(self,result):
        self.assertFalse(result['output_committed'])
        self.assertFalse(result['native_model_proven'])
        self.assertFalse(result['source_semantic_truth_authority'])
        self.assertEqual(result['tool_dispatches'],0)
        self.assertEqual(result['delivery_authority'],0)
        self.assertEqual(result['learning_authority'],0)
        self.assertEqual(result['jepa_weight'],0)
        self.assertFalse(result['whole_system_complete'])

    def test_original_lifecycle_inside_callback_is_red(self):
        def original_callback(messages):
            self.lifecycle_assigned()
            return choose('B2_GIST')(messages)
        result=select(self.r,self.prior,'B2_GIST',original_callback,
                      operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],'CALLBACK_STORE_CHANGED_RED')
        self.assertEqual(self.r.store.one(
            'SELECT COUNT(*) AS n FROM packets WHERE kind=?',
            (KIND,))['n'],0)
        self.assert_no_authority(result)

    def test_prewarm_outside_callback_passes_and_persists(self):
        self.lifecycle_assigned()
        result=select_bound(self.r,self.prior,'B2_GIST',choose('B2_GIST'),
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],
                         'SHADOW_EVENT_SOURCE_BOUND_CORRECT',result)
        self.assertTrue(result['authoritative_event_source_verified'])
        packet=json.loads(self.r.store.one(
            'SELECT payload FROM packets WHERE id=?',
            (result['packet_id'],))['payload'])
        self.assertEqual(packet['selected_span']['text'],
                         self.row['policy_span'])
        self.assert_no_authority(result)

    def test_six_disjoint_rows_two_source_ids_and_zero_authority(self):
        for row in rows():
            with self.subTest(project=row['id']):
                with tempfile.TemporaryDirectory() as tmp:
                    r=QuoteRuntime(Path(tmp)/'home',row)
                    r.cfg.update(OVERRIDES)
                    try:
                        prior=r.store.event(r.session,row['prior'])
                        r.store.set_state('T13_BODY_PORTS',{'synthetic_ASSIGNED':1})
                        b2=select_bound(r,prior,'B2_GIST',choose('B2_GIST'),
                                        operator_opt_in=True,callback_opt_in=True)
                        current=r.store.event(r.session,row['current'])
                        r.store.set_state('T13_BODY_PORTS',{'synthetic_ASSIGNED':2})
                        b1=select_bound(r,current,'B1_DETAIL',choose('B1_DETAIL'),
                                        operator_opt_in=True,callback_opt_in=True)
                        for result,expected in ((b2,row['policy_span']),
                                                (b1,row['option_span'])):
                            self.assertEqual(result['status'],
                                             'SHADOW_EVENT_SOURCE_BOUND_CORRECT',result)
                            packet=json.loads(r.store.one(
                                'SELECT payload FROM packets WHERE id=?',
                                (result['packet_id'],))['payload'])
                            self.assertEqual(packet['selected_span']['text'],expected)
                            self.assert_no_authority(result)
                        self.assertEqual(r.store.one(
                            'SELECT COUNT(*) AS n FROM actions')['n'],0)
                    finally:
                        r.close()

    def test_prewarm_does_not_waive_late_user_correction(self):
        self.lifecycle_assigned()
        def late(messages):
            self.r.store.event(self.r.session,
                               'Project Helion correction: stop this request.')
            return choose('B2_GIST')(messages)
        result=select_bound(self.r,self.prior,'B2_GIST',late,
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'],
                         'CALLBACK_STORE_CHANGED_RED')
        self.assert_no_authority(result)

    def test_prewarm_does_not_waive_forged_event_source(self):
        current=self.r.store.event(self.r.session,self.row['current'])
        forged=dict(current,source_ref=self.prior['source_ref'])
        self.lifecycle_assigned()
        called=[]
        result=select_bound(self.r,forged,'B2_GIST',
                            lambda _:called.append(True),
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],'EVENT_SOURCE_PREFLIGHT_RED')
        self.assertEqual(called,[])
        self.assert_no_authority(result)

    def test_prewarm_does_not_waive_prompt_mutation(self):
        self.lifecycle_assigned()
        def mutate(messages):
            messages[1]['content']='{}'
            return '{"span_id":"NONE"}'
        result=select_bound(self.r,self.prior,'B2_GIST',mutate,
                            operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],'FROZEN_SELECTOR_RED')
        self.assertEqual(result['component_status'],
                         'CALLBACK_PROMPT_MUTATED_RED')

    def test_new_runner_requires_all_thirty_native_final_receipts(self):
        def item(role):
            raw='{}'
            return {'role':role,'status':'RECORDED','process_reaped':True,
                    'native_metrics':{'status':'FINAL'},
                    'packet_evidence':{'raw':raw,
                        'sha256':hashlib.sha256(raw.encode()).hexdigest()},
                    'model_id_correct':True}
        report={'rows':[],'native_body_calls':30,
                'native_c3_calls':0,'native_jef_calls':0,'native_c2_calls':0}
        for row in rows():
            report['rows'].append({
                'id':row['id'],'status':'RECORDED','closed_store_ok':True,
                'no_live_output':True,'baseline_quote_ready':True,
                'id_pair_correct':True,
                'offers':[item('B2_GIST'),item('B1_DETAIL'),item('B2_GIST')],
                'id_selections':[item('B2_GIST'),item('B1_DETAIL')],
            })
        self.assertEqual(native._summarize(report),native.COMPLETE)
        report['native_body_calls']=29
        self.assertEqual(native._summarize(report),native.RED)
        report['native_body_calls']=30
        report['rows'][0]['id_selections'][0]['process_reaped']=False
        self.assertEqual(native._summarize(report),native.RED)

    def test_new_runner_wrong_fixture_fails_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            tampered=Path(d)/'tampered.json'
            tampered.write_bytes(FIXTURE.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'RUN117AL_FIXTURE_SHA_RED'):
                native.fixture(tampered)

    def test_native_runner_callback_contains_no_pool_get(self):
        source=inspect.getsource(native._id_native)
        tree=ast.parse(source)
        function=next(n for n in ast.walk(tree)
                      if isinstance(n,ast.FunctionDef) and n.name=='generate')
        callback_source=ast.get_source_segment(source,function)
        self.assertNotIn('runtime.pool.get',callback_source)
        self.assertIn('runner=runtime.pool.get(role)',source)
        self.assertLess(source.index('runner=runtime.pool.get(role)'),
                        source.index('result=select_bound('))
        self.assertIn('runner.load(',source)
        self.assertEqual(native.SEED,1071)
        self.assertEqual(native.FIXTURE_SHA,SHA)


if __name__=='__main__':
    unittest.main()

"""Run117BS prereg seed1103: eight disjoint real-Store source-bound software cases."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from v13.config import initialize
from v13.store import Store
from v13.agi.jef_eligibility_source_shadow_run46b import propose
from v13.agi.jef_c3_budget_formatter_shadow_run117bo import format_shadow

FIXTURE = Path(__file__).resolve().parents[1]/'docs/fixtures/RUN117BS_C3_DISJOINT_BUDGET_SEED1103.json'
SHA = 'f8ca7a22c47f991d630c9df1b1b2ee2943d24123246c8ffaf45db65998403f65'
IDS = ('Aurora','Boreal','Cirrus','Delta','Eos','Fjord','Gaia','Helix')
OLD = {'Helios','Lyra','Orion','Cedar','Mistral','Nexus','Sirius','Vela','Wren','Xenia','Yarrow','Zephyr'}

class FrozenDisjointBudget(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.home=Path(self.temp.name)
        initialize(self.home)
        self.store=Store(self.home)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),SHA)
        self.data=json.loads(FIXTURE.read_text())

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def test_frozen_fixture_schema_and_disjoint_ids(self):
        self.assertEqual(self.data['seed'],1103)
        self.assertEqual(self.data['schema'],'v13.run117bs.c3_disjoint_budget_seed1103.v1')
        self.assertEqual(self.data['arms'],['TYPED_JEF','RAW_SOURCE'])
        self.assertEqual(tuple(x['id'] for x in self.data['fixtures']),IDS)
        self.assertFalse(set(IDS)&OLD)
        self.assertEqual([x['oracle']['choice'] for x in self.data['fixtures']],
                         ['A','B','NONE','UNKNOWN','A','B','NONE','UNKNOWN'])

    def test_eight_exact_store_jef_candidates_and_copy_callback(self):
        for row in self.data['fixtures']:
            with self.subTest(id=row['id']):
                session=self.store.new_session()
                prior=self.store.event(session,row['prior'])['source_ref']
                current=self.store.event(session,row['current'])['source_ref']
                before=self.store.db.total_changes
                jef=propose(self.store,prior,current)
                self.assertEqual(jef['reason'],'EXACT_USER_SOURCE_RECIPE_SHADOW')
                self.assertEqual(jef['candidate'],row['oracle'])
                self.assertEqual(jef['authority'],0)
                def echo(messages,schema):
                    self.assertEqual([m['role'] for m in messages],['system','user'])
                    packet=json.loads(messages[1]['content'])
                    self.assertEqual(packet['typed_jef_candidate'],row['oracle'])
                    self.assertEqual(packet['candidate_authority'],0)
                    self.assertNotIn('oracle',packet)
                    return json.dumps(packet['typed_jef_candidate'])
                result=format_shadow(self.store,session,prior,current,echo,
                                     operator_opt_in=True,callback_opt_in=True)
                self.assertEqual(result['status'],'FORMATTER_MATCH_SHADOW')
                self.assertTrue(result['source_rechecked'])
                self.assertEqual(result['delivery_authority'],0)
                self.assertEqual(result['learning_authority'],0)
                self.assertEqual(result['jepa_weight'],0)
                self.assertFalse(result['native_proof'])
                self.assertEqual(self.store.db.total_changes,before)

    def test_missing_prior_source_ref_never_calls_formatter(self):
        row=self.data['fixtures'][0]
        session=self.store.new_session()
        prior=self.store.event(session,row['prior'])['source_ref']
        current=self.store.event(session,row['current'])['source_ref']
        called=[]
        def fail(*_):called.append(True);return '{}'
        wrong=dict(prior,sha256='0'*64)
        result=format_shadow(self.store,session,wrong,current,fail,
                             operator_opt_in=True,callback_opt_in=True)
        self.assertEqual(result['status'],'SOURCE_PREFLIGHT_RED')
        self.assertFalse(called)

if __name__=='__main__':unittest.main()

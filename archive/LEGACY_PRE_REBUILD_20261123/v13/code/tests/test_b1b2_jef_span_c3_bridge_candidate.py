"""Run117AC real SQLite B1/B2 persisted offers + JEF span + ContextOS."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.b1b2_jef_span_c3_bridge_candidate import build_b1b2_jef_span_c3_bridge
from v13.context_os import controller
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json'
SHA = 'cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d'


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == SHA
        cls.rows = json.loads(FIXTURE.read_text())['rows']

    def setup(self, row):
        tmp = tempfile.TemporaryDirectory()
        r = QuoteRuntime(Path(tmp.name) / 'home', row)
        r.cfg.update(OVERRIDES)
        prior = r.store.event(r.session, row['prior'])
        current = r.store.event(r.session, row['current'])
        c = TopicPartitionOfferConsumer(r)
        ids = {}
        for role in ('B1_DETAIL','B2_GIST'):
            offer = c.guarded_offer(role, current, 0,
                                    time.monotonic() + 30, operator_opt_in=True)
            assert offer['status'] == 'SHADOW_OFFER_PRODUCED', offer
            ids[role] = offer['offer_packet_id']
        return tmp,r,prior,current,ids

    def test_all_six_contextos_source_jef_body_hypotheses(self):
        for row in self.rows:
            with self.subTest(project=row['id']):
                tmp,r,prior,current,ids = self.setup(row)
                try:
                    before_calls = dict(r.calls)
                    result = build_b1b2_jef_span_c3_bridge(
                        r,prior,current,ids,operator_opt_in=True)
                    self.assertEqual(result['status'],
                                     'SHADOW_B1B2_JEF_SPAN_C3_BRIDGE_VERIFIED',result)
                    self.assertEqual(result['typed_jef_candidate'],row['oracle'])
                    self.assertEqual(result['source_refs'],
                                     [prior['source_ref'],current['source_ref']])
                    self.assertEqual(result['offer_packet_ids'],ids)
                    self.assertEqual(r.calls,before_calls)
                    self.assertFalse(result['output_committed'])
                    self.assertEqual(result['tool_dispatches'],0)
                    self.assertEqual(result['jepa_weight'],0)
                    payload = json.loads(result['messages'][1]['content'])
                    self.assertEqual(payload['typed_jef_candidate'],row['oracle'])
                    self.assertEqual(payload['policy']['text'],row['policy_span'])
                    self.assertEqual(payload['options']['text'],row['option_span'])
                    self.assertFalse(payload['body_hypotheses_are_facts'])
                    self.assertFalse(payload['body_model_quote_verified'])
                    self.assertFalse(payload['source_semantic_truth_authority'])
                    self.assertEqual([x['role'] for x in payload['body_observations']],
                                     ['B1_DETAIL','B2_GIST'])
                    self.assertTrue(all(x['hypothesis_authority'] ==
                        'MODEL_HYPOTHESIS_NOT_FACT' for x in payload['body_observations']))
                    self.assertTrue(all(q['semantic_truth_authority'] is False
                        for x in payload['body_observations'] for q in x['verified_quotes']))
                    self.assertNotIn(row['policy_span'],result['messages'][0]['content'])
                    self.assertEqual(r.store.one('SELECT COUNT(*) AS n FROM actions')['n'],0)
                    self.assertIsNotNone(r.store.one(
                        "SELECT id FROM packets WHERE id=? AND kind='ContextPlan'",
                        (result['context_plan_packet_id'],)))
                finally:
                    r.close();tmp.cleanup()

    def test_off_creates_no_context_plan(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            before=r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")['n']
            result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids)
            self.assertEqual(result['status'],'OFF')
            self.assertEqual(r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind='ContextPlan'")['n'],before)
        finally:
            r.close();tmp.cleanup()

    def test_contextos_active_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            controller(r).set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
            result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'CONTEXT_OS_NOT_SHADOW_RED')
        finally:
            r.close();tmp.cleanup()

    def test_stale_user_correction_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            r.store.event(r.session,'Project Helix. Correction: cancel previous options.')
            result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'TWO_SOURCE_POINTER_RED')
        finally:
            r.close();tmp.cleanup()

    def test_offer_packet_mutation_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            row=r.store.one('SELECT payload FROM packets WHERE id=?',(ids['B1_DETAIL'],))
            data=json.loads(row['payload'])
            data['offer']['summary']='FORGED'
            with r.store.tx() as db:
                db.execute('UPDATE packets SET payload=? WHERE id=?',
                           (dumps(data),ids['B1_DETAIL']))
            result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'B1B2_OFFER_OR_SOURCE_RED')
        finally:
            r.close();tmp.cleanup()

    def test_source_deletion_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            with r.store.tx() as db:
                db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                           (prior['source_ref']['source_id'],))
            result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'TWO_SOURCE_POINTER_RED')
        finally:
            r.close();tmp.cleanup()

    def test_offer_changed_mid_assembly_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            from v13.two_source_c3_role_boundary_candidate import build_role_separated_c3_shadow
            def change(*args, **kwargs):
                result=build_role_separated_c3_shadow(*args, **kwargs)
                row=r.store.one('SELECT payload FROM packets WHERE id=?',(ids['B2_GIST'],))
                data=json.loads(row['payload'])
                data['offer']['summary']='LATE FORGERY'
                with r.store.tx() as db:
                    db.execute('UPDATE packets SET payload=? WHERE id=?',
                               (dumps(data),ids['B2_GIST']))
                return result
            with patch('v13.b1b2_jef_span_c3_bridge_candidate.build_role_separated_c3_shadow',
                       side_effect=change):
                result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'POST_ASSEMBLY_SOURCE_OFFER_PLAN_RED')
        finally:
            r.close();tmp.cleanup()

    def test_context_plan_tamper_mid_assembly_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            from v13.two_source_c3_role_boundary_candidate import build_role_separated_c3_shadow
            def change(*args, **kwargs):
                result=build_role_separated_c3_shadow(*args, **kwargs)
                pid=result['context_plan_packet_id']
                row=r.store.one('SELECT payload FROM packets WHERE id=?',(pid,))
                data=json.loads(row['payload'])
                data['provenance']=[]
                with r.store.tx() as db:
                    db.execute('UPDATE packets SET payload=? WHERE id=?',
                               (dumps(data),pid))
                return result
            with patch('v13.b1b2_jef_span_c3_bridge_candidate.build_role_separated_c3_shadow',
                       side_effect=change):
                result=build_b1b2_jef_span_c3_bridge(r,prior,current,ids,operator_opt_in=True)
            self.assertEqual(result['status'],'CONTEXT_PLAN_LINEAGE_RED')
        finally:
            r.close();tmp.cleanup()

    def test_swapped_or_duplicate_offer_ids_refused(self):
        tmp,r,prior,current,ids=self.setup(self.rows[0])
        try:
            cases=[{'B1_DETAIL':ids['B2_GIST'],'B2_GIST':ids['B1_DETAIL']},
                   {'B1_DETAIL':ids['B1_DETAIL'],'B2_GIST':ids['B1_DETAIL']}]
            for bad in cases:
                with self.subTest(bad=bad):
                    result=build_b1b2_jef_span_c3_bridge(r,prior,current,bad,operator_opt_in=True)
                    self.assertEqual(result['status'],'B1B2_OFFER_OR_SOURCE_RED')
        finally:
            r.close();tmp.cleanup()


if __name__=='__main__':
    unittest.main()

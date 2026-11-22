"""Actual Store/coordinator transport regression; no native model-quality claim."""
import json
from pathlib import Path
import shlex
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from v13.history import native_history
from v13.operator import Operator
from v13.output_policy import InvalidRule
from v13.runtime import Runtime
from v13.store import telemetry_metrics


class FixedPolicyHistoryRevocation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.r.cfg['observer_mode']='off'
        self.op=Operator(self.r)
        pending=self.op.run(':rules fixed "Feste Frage?" "Alte feste Antwort"').split(';')[0]
        self.op.run(':approve '+pending)
        self.rule=self.r.store.rules()[0]
        self.r.submit('Feste Frage?')
        self.fixed=self.wait()
        self.assertEqual(self.fixed['text'],'Alte feste Antwort')
        self.assertFalse(json.loads(self.fixed['metadata'])['model_generated'])
        self.install_transport()
        self.r.submit('Besprich die letzte Antwort')
        self.dependent=self.wait()
        meta=json.loads(self.dependent['metadata'])
        self.assertIn(self.rule['answer_ref'],meta['context_source_refs'])
        self.assertEqual(len(self.history()[0]),4)

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def wait(self):
        until=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(self.r.idle())
        row=self.r.last_answer()
        self.assertEqual(row['status'],'FINAL')
        return row

    def install_transport(self):
        self.native_messages=[]
        def generate(messages,*args,**kwargs):
            self.native_messages.append(messages)
            yield 'Transportfixture zur vorherigen Antwort'
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'transport_test_seam':True},generate=generate))
        self.r.learner.output_delta=Mock(return_value=None)

    def history(self):
        return native_history(self.r.store,self.r.session,'future-event',8)

    def remove(self):
        pending=self.op.run(':rules remove 0').split(';')[0]
        self.op.run(':approve '+pending)

    def test_removal_revokes_direct_and_transitive_history_without_deleting_chat(self):
        self.remove()
        self.assertEqual(self.history(),([],[]))
        shown=self.r.store.history(self.r.session)
        self.assertIn(self.fixed['text'],[x['text'] for x in shown])
        self.assertIn(self.dependent['text'],[x['text'] for x in shown])
        self.r.submit('Neue unabhängige Frage')
        self.wait()
        messages=self.native_messages[-1]
        self.assertFalse(any(x['role']=='assistant' for x in messages))
        self.assertNotIn('Alte feste Antwort',json.dumps(messages,ensure_ascii=False))

    def test_replacement_with_identical_answer_hash_still_rejects_old_source_id(self):
        self.remove()
        pending=self.op.run(':rules fixed "Feste Frage?" "Alte feste Antwort"').split(';')[0]
        self.op.run(':approve '+pending)
        replacement=self.r.store.rules()[0]
        self.assertEqual(replacement['answer_ref']['sha256'],self.rule['answer_ref']['sha256'])
        self.assertNotEqual(replacement['answer_ref']['source_id'],self.rule['answer_ref']['source_id'])
        self.assertEqual(self.history(),([],[]))
        self.r.submit('Feste Frage?')
        new=self.wait()
        self.assertEqual(new['text'],'Alte feste Antwort')
        records,refs=self.history()
        self.assertEqual([x['event_id'] for x in records],[new['event_id'],new['event_id']])
        self.assertIn(replacement['answer_ref'],refs)
        self.assertNotIn(self.rule['answer_ref'],refs)

    def test_unrelated_guidance_change_retains_still_approved_source_lineage(self):
        old_version=json.loads(self.fixed['metadata'])['output_policy']['rule_version']
        pending=self.op.run(':rules add kurz').split(';')[0]
        self.op.run(':approve '+pending)
        self.assertNotEqual(self.r.store.generation()['rule_version'],old_version)
        records,refs=self.history()
        self.assertEqual(len(records),4)
        self.assertIn(self.rule['answer_ref'],refs)
        self.assertIn(self.rule['query_ref'],refs)

    def test_still_active_entry_retains_history_after_other_exact_rule_addition(self):
        pending=self.op.run(':rules fixed "Andere feste Frage?" "Andere Antwort"').split(';')[0]
        self.op.run(':approve '+pending)
        self.assertEqual(len(self.history()[0]),4)
        self.assertIn(self.rule['answer_ref'],self.history()[1])

    def test_tampered_active_rule_history_fails_closed_instead_of_silently_skipping(self):
        path=self.home/'data/blobs'/self.rule['answer_ref']['sha256']
        path.write_text('tamper')
        with self.assertRaises(InvalidRule):self.history()
        before=len(self.native_messages)
        self.r.submit('Andere Frage trotz kaputter Policy')
        until=time.monotonic()+5
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(self.r.idle())
        row=self.r.last_answer();meta=json.loads(row['metadata'])
        self.assertEqual(row['status'],'ERROR')
        self.assertEqual(meta['failure_stage'],'policy_check')
        self.assertFalse(meta['model_generated'])
        self.assertEqual(len(self.native_messages),before)

    def test_revoked_query_source_excludes_dependent_history_after_explicit_removal(self):
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?',(self.rule['query_ref']['source_id'],))
        with self.assertRaises(InvalidRule):self.history()
        self.remove()
        self.assertEqual(self.history(),([],[]))

    def test_ledger_reports_exact_source_only_scope_and_existing_age_retention(self):
        from v13.verification import completion_ledger,GATES
        ledger=completion_ledger(self.r)
        row=next(x for x in ledger['rows'] if x['feature_id']=='C5_EXACT_APPROVED_RULE_OUTPUT')
        self.assertEqual(row['current_mode'],'IMPLEMENTED')
        self.assertEqual(row['gate_status'],'PARTIAL')
        self.assertIn('no native inference',row['hardware_proof'])
        self.assertIn('No fuzzy/paraphrase/whole-answer semantic rule enforcement or learned neural checker',row['known_limitations'])
        self.assertFalse(ledger['canonical_architecture_complete'])
        self.assertIn('no general semantic rule checker',GATES['fixed_output_policy'])
        logging=next(x for x in ledger['rows'] if x['feature_id']=='STEP0_LOGGING_MIGRATION')
        self.assertNotIn('not implemented',str(logging['known_limitations']))
        self.assertIn('tests/test_log_retention.py',logging['unit_tests'])

    def test_finite_public_policy_stage_codes_survive_without_private_text(self):
        stages=['A3_NATIVE_ALIGNMENT','SEMANTIC_RECALL','C2_CONTROL','B_OBSERVERS','C3_DECODE','NATIVE_WORLD_PREDICTION']
        telemetry=telemetry_metrics({'turn_stage':'policy_check','failure_stage':'policy_check','skipped_native_stages':stages,'answer':'Private Answer'})
        self.assertEqual(telemetry['turn_stage'],'policy_check')
        self.assertEqual(telemetry['failure_stage'],'policy_check')
        self.assertEqual(telemetry['skipped_native_stages'],stages)
        self.assertNotIn('Private',json.dumps(telemetry))


if __name__=='__main__':unittest.main()

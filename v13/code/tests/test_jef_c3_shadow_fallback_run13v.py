"""Run13V source-rechecked JEF fallback, real Store, synthetic native receipt."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import run13l_c3_system_native as l
from scripts import run13j_c3_jef_native as j
from scripts import run13k_c3_copy_native as k
from v13.agi import jef_c3_shadow_fallback_run13v as mux
from v13.runtime import Runtime

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/run13l_c3_system_seed251_20261030.json'


class SourceBoundFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        case = l.load_fixture(FIXTURE)[0]
        self.case = case
        self.data = j.prepare_case(self.runtime, case)
        self.linked = self.data['linked']
        self.ids = (self.data['plan_packet_id'], self.data['query_event_id'],
                    self.data['source_event_id'])

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def receipt(self, *, direct=True):
        prompt_hash = (mux._sha(k.COPY_PREFIX + self.linked['answer'] + k.COPY_SUFFIX)
                       if direct else self.linked['prompt_sha256'])
        return {'native_role': 'C3_LANGUAGE', 'native_status': 'FINAL',
                'native_calls': 1, 'native_reaped': True, 'native_pid': 12345,
                'native_release': {'process_reaped': True},
                'model_sha256': mux.MODEL_SHA,
                'model_revision': mux.MODEL_REVISION,
                'source_event_id': self.ids[2], 'query_event_id': self.ids[1],
                'context_plan_packet_id': self.ids[0],
                'answer_sha256': self.linked['answer_sha256'],
                'prompt_sha256': prompt_hash,
                'native_output_sha256': mux._sha(self.linked['answer']),
                'native_output_bytes': len(self.linked['answer'].encode('utf-8'))}

    def select(self, text, receipt=None, snapshot=None, ids=None):
        return mux.select_shadow(self.runtime.store, *(ids or self.ids),
                                 self.linked if snapshot is None else snapshot,
                                 c3_text=text, native_receipt=receipt)

    def assert_shadow(self, result):
        self.assertEqual(result['status'], 'SHADOW_NO_AUTHORITY')
        self.assertEqual(result['delivery_authority'], 0)
        self.assertEqual(result['context_authority'], 0)
        self.assertEqual(result['native_calls_by_mux'], 0)
        self.assertFalse(result['model_called_by_mux'])
        self.assertEqual(result['store_writes_by_mux'], 0)
        self.assertFalse(result['weight_updates'])
        self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
        self.assertEqual(result['step2_status'], 'UTILITY_FAIL')
        self.assertEqual(result['b3_status'], 'NO_PROMOTION')
        self.assertEqual(result['body_jepa_status'], 'UNAVAILABLE')
        self.assertEqual(result['jepa_weight'], 0)
        self.assertFalse(result['redmi_measured'])
        self.assertFalse(result['whole_system_complete'])
        self.assertFalse(result['utility_gate_pass'])

    def test_source_rechecked_exact_c3_selected_without_egress_or_model(self):
        before = (
            self.runtime.store.one("SELECT count(*) AS n FROM messages")['n'],
            self.runtime.store.one("SELECT count(*) AS n FROM sources")['n'],
        )
        with patch.object(self.runtime.pool, 'get',
                          side_effect=AssertionError('NATIVE_CALLED')):
            result = self.select(self.linked['answer'], self.receipt())
        self.assert_shadow(result)
        self.assertEqual(result['selected_provenance'], 'C3_FACTS_VERIFIED_SHADOW')
        self.assertEqual(result['selected_text'], self.linked['answer'])
        self.assertEqual(result['selected_text_sha256'], self.linked['answer_sha256'])
        self.assertTrue(result['source_revalidated'])
        self.assertTrue(result['native_receipt_bound'])
        self.assertEqual(before, (
            self.runtime.store.one("SELECT count(*) AS n FROM messages")['n'],
            self.runtime.store.one("SELECT count(*) AS n FROM sources")['n'],
        ))

    def test_unfaithful_or_missing_c3_falls_back_to_jef_not_model_success(self):
        answer = self.linked['answer']
        wrong = answer.replace('Silver finishes sooner.', 'Juniper finishes sooner.')
        for output, receipt in ((wrong, self.receipt()),
                                ('ABSTAIN.', self.receipt()),
                                (None, self.receipt()),
                                (answer, None),
                                (answer, dict(self.receipt(), model_sha256='0'*64)),
                                (answer, dict(self.receipt(), native_pid=True)),
                                (answer + 'X'*1000, self.receipt()),
                                (answer + '\ud800', self.receipt())):
            with self.subTest(output=str(output)[:30], receipt=bool(receipt)):
                result = self.select(output, receipt)
                self.assert_shadow(result)
                self.assertEqual(result['selected_provenance'],
                                 'JEF_VERIFIED_FALLBACK_SHADOW')
                self.assertEqual(result['selected_text'], answer)
                self.assertTrue(result['source_revalidated'])

    def test_both_frozen_prompt_hashes_can_bind_but_wrong_source_never(self):
        for direct in (True, False):
            with self.subTest(direct=direct):
                result = self.select(self.linked['answer'], self.receipt(direct=direct))
                self.assert_shadow(result)
                self.assertEqual(result['selected_provenance'], 'C3_FACTS_VERIFIED_SHADOW')
        forged = dict(self.receipt(), source_event_id='wrong')
        result = self.select(self.linked['answer'], forged)
        self.assert_shadow(result)
        self.assertEqual(result['selected_provenance'], 'JEF_VERIFIED_FALLBACK_SHADOW')

    def test_real_deleted_source_abstains_even_with_valid_native_receipt(self):
        with self.runtime.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id="
                       "(SELECT source_id FROM events WHERE id=?)",
                       (self.ids[2],))
        result = self.select(self.linked['answer'], self.receipt())
        self.assert_shadow(result)
        self.assertIsNone(result['selected_text'])
        self.assertFalse(result['source_revalidated'])
        self.assertEqual(result['selected_provenance'], 'NONE')

    def test_stale_source_tampered_snapshot_and_read_error_abstain(self):
        cases = (
            ('snapshot', dict(self.linked, answer_sha256='0'*64)),
            ('query', self.linked),
        )
        for kind, snapshot in cases:
            result = (self.select(self.linked['answer'], self.receipt(), snapshot=snapshot)
                      if kind == 'snapshot' else
                      self.select(self.linked['answer'], self.receipt(),
                                  ids=(self.ids[0], 'wrong-query', self.ids[2])))
            self.assert_shadow(result)
            self.assertIsNone(result['selected_text'])
            self.assertEqual(result['selected_provenance'], 'NONE')
        with patch.object(mux, 'propose_c3_context',
                          side_effect=sqlite3.OperationalError('DB unavailable')):
            result = self.select(self.linked['answer'], self.receipt())
        self.assert_shadow(result)
        self.assertIsNone(result['selected_text'])
        with patch.object(mux, 'propose_c3_context',
                          return_value=dict(self.linked, answer='changed')):
            result = self.select(self.linked['answer'], self.receipt())
        self.assert_shadow(result)
        self.assertIsNone(result['selected_text'])


if __name__ == '__main__':
    unittest.main()
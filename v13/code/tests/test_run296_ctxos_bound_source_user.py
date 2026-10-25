"""Run296: source-verified Context OS user layout, default-off, SQLite human lineage."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13.runtime import Runtime
from v13 import context_os as C

MATCH = 'Projekt Kelmo16: Finanzrahmen?'
WRONG_TOPIC = 'Projekt Kelmo16: Wer leitet das Team?'
WRONG_ENTITY = 'Projekt Kelmo17: Finanzrahmen?'


class BoundSourceLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.c = C.ContextOS(self.r.store, self.r.cfg)
        self.r.context_os = self.c
        e = self.r.store.event(self.r.session, 'Projekt Kelmo16 Budget')
        self.r.memory.feedback(e['event_id'], 'fact', '400 Euro', key='Projekt Kelmo16 Budget')
        self.m = dict(self.r.store.one('SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id ORDER BY m.created DESC LIMIT 1'))
        self.m['source_ref'] = {'source_id': self.m['source_id'], 'sha256': self.m['hash'],
                                'char_start': 0, 'char_end': self.m['chars'], 'modality': 'text'}
        self.m['retrieval_policy'] = {'decision': 'admit', 'in_support': True}
        self.m['retrieval_score'] = 1.0

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def activate(self):
        self.c.set_capability('B1_DETAIL', 'consecutive_user', True, 'test_declared_capability')
        self.c.set_layout('source_bound_user')
        self.c.set_mode('ACTIVE', 'EXPLICIT_HUMAN')

    def volatile(self, query, item=None):
        items = self.r.memory.report_context(query, [self.m]) if item is None else [item]
        return [('ACTIVE_VIEW', '\nStored user corrections:', items),
                ('LATENT_STATE', '\nTask:', {'task_request': query})]

    def plan(self, query=MATCH, item=None, session=None):
        eid = self.r.store.event(session or self.r.session, query)['event_id']
        return self.c.plan(eid, 'B1_DETAIL', 'SYS', self.volatile(query, item), [], query)

    def test_default_shadow_and_capability_fail_closed(self):
        self.assertEqual(self.c.report()['layout'], 'append_only')
        self.c.set_layout('source_bound_user')
        self.c.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
        p = self.plan()
        self.assertEqual(p['plan']['layout'], 'legacy')
        self.assertEqual(len(p['messages']), 2)
        self.assertEqual(p['plan']['cache']['fallback_reason'], 'template_capability_unknown')
        self.c.set_capability('B1_DETAIL', 'consecutive_user', True, 'test')
        self.c.set_mode('SHADOW')
        p = self.plan()
        self.assertFalse(p['applied'])
        self.assertEqual(p['messages'], p['legacy'])

    def test_exact_verified_human_source_moves_to_user_context(self):
        self.activate()
        p = self.plan()
        self.assertTrue(p['applied'])
        self.assertEqual(p['plan']['layout'], 'source_bound_user')
        self.assertEqual([m['role'] for m in p['messages']], ['system', 'user', 'user'])
        self.assertNotIn('400 Euro', p['messages'][0]['content'])
        self.assertIn('400 Euro', p['messages'][-2]['content'])
        self.assertEqual(p['messages'][-1]['content'], MATCH)
        self.assertEqual(p['plan']['bound_source_refs'], [self.m['source_ref']])
        self.assertIn(self.m['source_ref'], p['plan']['provenance'])
        self.assertEqual(self.r.store.integrity(True), [])
        self.assertIn('source_bound_user_exact', p['plan']['decisions'])

    def test_wrong_topic_and_wrong_entity_never_move_source(self):
        self.activate()
        for q in (WRONG_TOPIC, WRONG_ENTITY):
            p = self.plan(q)
            self.assertEqual(p['plan']['layout'], 'legacy')
            self.assertEqual(p['plan']['cache']['fallback_reason'], 'no_verified_current_source')
            self.assertNotIn('source_bound_user_exact', p['plan']['decisions'])
            self.assertEqual(p['plan']['bound_source_refs'], [])

    def test_unmatched_or_forged_current_claim_cannot_authorize(self):
        self.activate()
        original = self.volatile(MATCH)[0][2][0]
        for item in (dict(original, matched_query='another query'),
                     dict(original, relevance='model guessed relevance'),
                     dict(original, correction='900 Euro')):
            self.assertEqual(self.plan(item=item)['plan']['layout'], 'legacy')

    def test_other_session_cannot_reuse_private_correction(self):
        self.activate()
        other = self.r.store.new_session('Other session')
        self.assertEqual(self.plan(session=other)['plan']['layout'], 'legacy')

    def test_forget_blocks_stale_source(self):
        self.activate()
        item = self.volatile(MATCH)[0][2][0]
        self.r.memory.forget(self.m['id'])
        self.assertEqual(self.plan(item=item)['plan']['layout'], 'legacy')

    def test_conflicting_current_memories_fail_closed(self):
        self.activate()
        e = self.r.store.event(self.r.session, 'Projekt Kelmo16 Budget')
        self.r.memory.feedback(e['event_id'], 'fact', '900 Euro', key='Projekt Kelmo16 Budget')
        self.assertEqual(self.plan()['plan']['layout'], 'legacy')

    def test_compacted_away_source_cannot_be_resurrected_by_layout(self):
        self.activate()
        self.c.cfg = dict(self.r.cfg, context_tokens=800, answer_tokens=64)
        eid = self.r.store.event(self.r.session, MATCH)['event_id']
        actual = self.volatile(MATCH)[0][2][0]
        vol = [('ACTIVE_VIEW', '\nStored user corrections:',
                [{'topic': 'irrelevant', 'correction': 'x' * 1300}, actual]),
               ('LATENT_STATE', '\nTask:', {'task_request': MATCH})]
        p = self.c.plan(eid, 'B1_DETAIL', 'SYS', vol, [], MATCH)
        self.assertIn('compact_active_view', p['plan']['decisions'])
        self.assertEqual(p['plan']['layout'], 'legacy')
        self.assertEqual(p['plan']['bound_source_refs'], [])

    def test_budget_overflow_never_applies_source_user_layout(self):
        self.activate()
        self.c.cfg = dict(self.r.cfg, context_tokens=120, answer_tokens=64)
        p = self.plan()
        self.assertFalse(p['applied'])
        self.assertIn('budget_unmet_fallback', p['plan']['decisions'])

    def test_actual_runtime_uses_opt_in_layout_with_real_sqlite_memory(self):
        self.activate()
        self.r.cfg.update(observer_mode='off', route_override='detail', history_turns=0)
        self.r._route = Mock(return_value=('detail', {'source': 'TEST_ROUTE_SEAM'}))
        self.r.memory.recall = Mock(return_value=[self.m])
        seen = []
        def generate(messages, *a, **k):
            seen.append(messages)
            yield 'Source noted.'  # synthetic fake runner, not native proof
        self.r.pool.get = Mock(return_value=SimpleNamespace(role='B1_DETAIL', last_metrics={}, generate=generate))
        self.r.submit(MATCH)
        end = time.monotonic() + 10
        while not self.r.idle() and time.monotonic() < end:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')
        self.assertTrue(seen)
        self.assertIn('400 Euro', seen[-1][-2]['content'])
        self.assertEqual(seen[-1][-1]['content'], MATCH)


if __name__ == '__main__':
    unittest.main()

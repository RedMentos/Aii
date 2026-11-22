"""Real ContextOS/SQLite regressions; no native or Android speed proof."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import types
import unittest
from unittest.mock import Mock, patch as mock_patch

from scripts import context_offer_budget_candidate_20261116 as patch
from v13.common import dumps
from v13.runtime import Runtime


CODE = Path(__file__).resolve().parents[1]
SOURCE = CODE / 'v13/context_os.py'


def load_context(raw):
    module = types.ModuleType('v13._context_offer_budget_test')
    module.__package__ = 'v13'
    exec(compile(raw, '<test-context-os>', 'exec'), module.__dict__)
    return module


def staged_context():
    path = CODE / 'scripts/termux_runtime_recovery_candidate_20261112.py'
    spec = importlib.util.spec_from_file_location('context_budget_stage', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_sources(CODE)['v13/context_os.py']


class ContextOfferBudget(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Runtime(Path(self.temp.name))
        self.addCleanup(self.runtime.close)
        self.runtime.sleep.cycle.set_policy('enabled', 'off')

    def plan(self, raw, *, active=True, layout='legacy', overflow=False,
             selected_first=False, tool_as_list=True):
        context = load_context(raw).ContextOS(
            self.runtime.store,
            dict(self.runtime.cfg, context_tokens=1800 if not overflow else 400,
                 answer_tokens=128))
        context.set_mode('ACTIVE', 'EXPLICIT_HUMAN') if active else context.set_mode('SHADOW')
        context.set_capability('C3_LANGUAGE', 'consecutive_user', True)
        context.set_layout(layout)
        text = 'Compare both contributions exactly.'
        event = self.runtime.store.event(self.runtime.session, text)
        offers = [
            {'role': 'B1_DETAIL', 'offer_packet_id': 'offer-detail',
             'summary': 'DETAIL_UNIQUE_' + 'D' * 1650,
             'source_refs': [event['source_ref']]},
            {'role': 'B2_GIST', 'offer_packet_id': 'offer-gist',
             'summary': 'GIST_UNIQUE_' + 'G' * 1650,
             'source_refs': [event['source_ref']]},
        ]
        tool = [{'result': 'EXACT_42'}, {'result': 'EXACT_43'}] if tool_as_list else {'result': 'EXACT_42'}
        memories = [{'fact': 'optional-memory-' + str(i) + '-' + 'x' * 350}
                    for i in range(6)]
        selected = [('HYPOTHESES', '\nOFFERS:', offers),
                    ('TOOL_RESULT', '\nTOOL:', tool)]
        optional = [('ACTIVE_VIEW', '\nMEM:', memories)]
        volatile = selected + optional if selected_first else optional + selected
        result = context.plan(event['event_id'], 'C3_LANGUAGE', 'SYS',
                              volatile, [], text, provenance=[event['source_ref']])
        return result, event, offers, tool

    def test_old_counterexample_then_selected_inputs_preserved(self):
        raw = SOURCE.read_bytes()
        baseline, _, old_offers, _ = self.plan(raw)
        self.assertNotIn(dumps(old_offers), ''.join(x['content'] for x in baseline['messages']))
        self.assertIn('compact_hypotheses', baseline['plan']['decisions'])
        result, event, offers, tool = self.plan(patch.apply_source(raw))
        rendered = ''.join(m['content'] for m in result['messages'])
        self.assertIn(dumps(offers), rendered)
        self.assertIn(dumps(tool), rendered)
        self.assertEqual(result['messages'][-1],
                         {'role': 'user', 'content': 'Compare both contributions exactly.'})
        self.assertEqual(self.runtime.store.read_source(event['source_ref']),
                         'Compare both contributions exactly.')
        items = {x['item_id']: x for x in result['plan']['items']}
        self.assertEqual((items['HYPOTHESES']['form'], items['HYPOTHESES']['pointers']), ('RAW', 0))
        self.assertEqual(items['TOOL_RESULT']['form'], 'RAW')
        self.assertGreater(items['ACTIVE_VIEW']['pointers'], 0)
        self.assertNotIn('compact_hypotheses', result['plan']['decisions'])
        self.assertIn(event['source_ref'], result['plan']['provenance'])
        row = self.runtime.store.one('SELECT payload FROM packets WHERE id=?', (result['packet_id'],))
        self.assertEqual(json.loads(row['payload'])['budget'], result['plan']['budget'])

    def test_protected_layers_first_and_dict_tool_are_also_preserved(self):
        result, _, offers, tool = self.plan(patch.apply_source(SOURCE.read_bytes()),
                                            selected_first=True, tool_as_list=False)
        rendered = ''.join(m['content'] for m in result['messages'])
        self.assertIn(dumps(offers), rendered)
        self.assertIn(dumps(tool), rendered)
        self.assertGreater(next(x for x in result['plan']['items'] if x['item_id'] == 'ACTIVE_VIEW')['pointers'], 0)

    def test_real_integrated_stage_and_stable_prefix(self):
        raw = staged_context()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'e4962d932294490b8f4b63a79115212a7000285290444484ec3bf7e50b243cad')
        result, _, offers, tool = self.plan(raw, layout='stable_prefix')
        rendered = ''.join(m['content'] for m in result['messages'])
        self.assertIn(dumps(offers), rendered)
        self.assertIn(dumps(tool), rendered)
        self.assertEqual(result['plan']['layout'], 'stable_prefix')
        self.assertTrue(result['applied'])

    def test_overflow_is_explicit_and_keeps_required_inputs(self):
        result, _, offers, tool = self.plan(patch.apply_source(SOURCE.read_bytes()), overflow=True)
        rendered = ''.join(m['content'] for m in result['messages'])
        self.assertIn(dumps(offers), rendered)
        self.assertIn(dumps(tool), rendered)
        self.assertTrue(result['plan']['budget']['planned_over_budget'])
        self.assertTrue(result['plan']['budget']['returned_over_budget'])
        self.assertTrue(result['plan']['budget']['estimate_only'])
        self.assertIn('estimated_budget_exceeded', result['plan']['decisions'])

    def test_shadow_preserves_legacy_messages(self):
        result, _, offers, tool = self.plan(patch.apply_source(SOURCE.read_bytes()), active=False)
        self.assertFalse(result['applied'])
        self.assertEqual(result['messages'], result['legacy'])
        rendered = ''.join(m['content'] for m in result['messages'])
        self.assertIn(dumps(offers), rendered)
        self.assertIn(dumps(tool), rendered)

    def test_actual_runtime_selected_offers_reach_c3_in_active_mode(self):
        """Real Runtime/C4/SQLite; all three language runners are synthetic."""
        from v13 import context_os
        from v13.operator import Operator
        from v13.prompts import text as prompt

        question = ('Compare details with planning. The rent is 120 euros. '
                    'The plan preserves a long-term reserve.')

        def exercise(fixed):
            calls = []
            with TemporaryDirectory() as home:
                r = Runtime(Path(home))
                try:
                    r.sleep.cycle.set_policy('enabled', 'off')
                    r.cfg.update(context_tokens=512, answer_tokens=128, deadline_seconds=90,
                                 observer_mode='background', observer_schedule='A_THEN_B_SEQUENTIAL',
                                 b2_quote_select='off', offer_quote_context_chars=0, b2_state_slots=0)
                    op = Operator(r)
                    op.run(':effort max')
                    op.run(':ctxos active')
                    r._route = Mock(return_value=('both', {'source': 'TEST_BOTH'}))
                    r.learner.output_delta = Mock(return_value=None)

                    class Runner:
                        def __init__(self, role):
                            self.role = role
                            self.last_metrics = {'status': 'FINAL', 'role': role, 'synthetic': True}

                        def generate(self, messages, cancel, deadline, *args, **kwargs):
                            calls.append((self.role, messages))
                            if self.role == 'B1_DETAIL':
                                result = {'summary': 'The rent is 120 euros.',
                                          'quotes': ['The rent is 120 euros.'],
                                          'uncertainty': 'low', 'needs_reentry': False}
                            elif self.role == 'B2_GIST':
                                result = {'summary': 'A long-term reserve is needed.',
                                          'quotes': ['The plan preserves a long-term reserve.'],
                                          'uncertainty': 'low', 'needs_reentry': False}
                            else:
                                yield 'One combined response.'
                                return
                            yield json.dumps(result)

                    runners = {role: Runner(role) for role in ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE')}
                    r.pool.get = Mock(side_effect=lambda role: runners[role])
                    plan = (load_context(patch.apply_source(SOURCE.read_bytes())).ContextOS.plan
                            if fixed else context_os.ContextOS.plan)
                    with mock_patch.object(context_os.ContextOS, 'plan', plan):
                        event_id = op.run(question)
                        deadline = time.monotonic() + 12
                        while not r.idle() and time.monotonic() < deadline:
                            time.sleep(.01)
                        self.assertTrue(r.idle())
                    answer = r.last_answer()
                    self.assertEqual((answer['status'], answer['text']), ('FINAL', 'One combined response.'))
                    selected_ids = json.loads(answer['metadata'])['selected_offer_ids']
                    self.assertEqual(len(selected_ids), 2)
                    messages = next(messages for role, messages in calls if role == 'C3_LANGUAGE')
                    heading = '\n' + prompt(r.cfg, 'hypotheses')
                    for message in messages:
                        start = message['content'].find(heading)
                        if start >= 0:
                            payload, _ = json.JSONDecoder().raw_decode(message['content'], start + len(heading))
                            break
                    else:
                        self.fail('C3 did not receive its hypotheses layer')
                    packet = r.store.one("SELECT payload FROM packets WHERE kind='ContextPlan' AND event_id=?", (event_id,))
                    return selected_ids, payload, json.loads(packet['payload'])
                finally:
                    r.close()

        selected, baseline, before = exercise(False)
        self.assertEqual(len(baseline), 1)
        self.assertIn('compact_hypotheses', before['decisions'])
        selected, after, plan = exercise(True)
        self.assertEqual({x['offer_packet_id'] for x in after}, set(selected))
        self.assertEqual({x['role'] for x in after}, {'B1_DETAIL', 'B2_GIST'})
        self.assertNotIn('compact_hypotheses', plan['decisions'])

    def test_unknown_modified_and_repeated_sources_fail_closed(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(set(patch.INPUT_SHA256),
                         {hashlib.sha256(raw).hexdigest(), 'a35966dbe77a603470d73285eac9c8087163d8cf675a1b8516e3b9f38b267232'})
        self.assertEqual(hashlib.sha256(staged_context()).hexdigest(),
                         'e4962d932294490b8f4b63a79115212a7000285290444484ec3bf7e50b243cad')
        for data in (raw + b'\n# edited\n', patch.apply_source(raw), b''):
            with self.subTest(size=len(data)), self.assertRaisesRegex(ValueError, 'hash mismatch'):
                patch.apply_source(data)
        self.assertEqual(patch.build_sources(CODE)['v13/context_os.py'], patch.apply_source(raw))


    def test_restored_source_links_are_not_silently_compacted(self):
        raw = SOURCE.read_bytes()
        question = 'Compare earlier sources'
        event = self.runtime.store.event(self.runtime.session, question)
        refs = [self.runtime.store.source('first source'),
                self.runtime.store.source('second source')]
        sources = [{'source_ref': ref, 'excerpt': 'VALUE_%d_' % i + 'x' * 480}
                   for i, ref in enumerate(refs)]
        volatile = [('SOURCE_LINKS', '\nSOURCES:', sources)]
        cfg = dict(self.runtime.cfg, context_tokens=750, answer_tokens=128)
        def do_plan(source):
            ctx = load_context(source).ContextOS(self.runtime.store, cfg)
            ctx.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
            return ctx.plan(event['event_id'], 'C3_LANGUAGE', 'SYS', volatile,
                            [], question, provenance=refs)
        before = do_plan(raw)
        self.assertIn('compact_source_links', before['plan']['decisions'])
        after = do_plan(patch.apply_source(raw))
        rendered = ''.join(m['content'] for m in after['messages'])
        self.assertIn(dumps(sources), rendered)
        self.assertNotIn('compact_source_links', after['plan']['decisions'])
        self.assertTrue(all(ref in after['plan']['provenance'] for ref in refs))
        self.assertFalse(after['plan']['budget']['returned_over_budget'])

    def test_shadow_marks_the_budget_of_messages_actually_returned(self):
        cfg = dict(self.runtime.cfg, context_tokens=512, answer_tokens=48)
        ctx = load_context(patch.apply_source(SOURCE.read_bytes())).ContextOS(
            self.runtime.store, cfg)
        ctx.set_mode('SHADOW')
        event = self.runtime.store.event(self.runtime.session, 'CURRENT')
        history = []
        for i in range(4):
            history.extend([{'event_id': 'old-%d' % i, 'role': 'user', 'text': 'Q' * 800},
                            {'event_id': 'old-%d' % i, 'role': 'assistant', 'text': 'A' * 800}])
        result = ctx.plan(event['event_id'], 'C3_LANGUAGE', 'SYS', [], history, 'CURRENT')
        self.assertFalse(result['applied'])
        self.assertTrue(result['plan']['budget']['returned_over_budget'])
        self.assertIn('estimated_returned_budget_exceeded', result['plan']['decisions'])
        self.assertTrue(result['plan']['budget']['estimate_only'])


if __name__ == '__main__':
    unittest.main()

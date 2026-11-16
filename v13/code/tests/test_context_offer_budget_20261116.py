"""Real ContextOS/SQLite regressions; no native or Android speed proof."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import types
import unittest

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
        self.assertIn(hashlib.sha256(raw).hexdigest(), patch.INPUT_SHA256)
        result, _, offers, tool = self.plan(patch.apply_source(raw), layout='stable_prefix')
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

    def test_unknown_modified_and_repeated_sources_fail_closed(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(set(patch.INPUT_SHA256),
                         {hashlib.sha256(raw).hexdigest(), hashlib.sha256(staged_context()).hexdigest()})
        for data in (raw + b'\n# edited\n', patch.apply_source(raw), b''):
            with self.subTest(size=len(data)), self.assertRaisesRegex(ValueError, 'hash mismatch'):
                patch.apply_source(data)
        self.assertEqual(patch.build_sources(CODE)['v13/context_os.py'], patch.apply_source(raw))


if __name__ == '__main__':
    unittest.main()

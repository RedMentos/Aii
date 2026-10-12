"""Rule-transport candidate: offline transport/lifecycle checks, no native calls."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import rule_transport_ablation as ablation
from scripts import source_handoff_ablation as previous
from v13.common import dumps
from v13.config import validate
from v13.runners import RunnerPool


def fake_runner(pool, role, fixture, earlier=('Budget 61 euros.',), current=()):
    def generate(messages, cancel, deadline, tokens, schema=None, **kwargs):
        if role == 'C3_LANGUAGE': return iter([dumps(fixture['oracle'])])
        query = json.loads(messages[1]['content'])
        obj = {'summary': 'A fallible reading.', 'quotes': list(current), 'uncertainty': 'Uncertain', 'needs_reentry': True}
        if schema and 'earlier_quotes' in schema['properties']:
            obj['earlier_quotes'] = list(earlier) if query.get('earlier_context') else []
        return iter([dumps(obj)])
    runner = SimpleNamespace(role=role, last_metrics={'status': 'FINAL'}, generate=generate,
                             unload=lambda: {'process_reaped': True}, purpose='generate')
    pool.current = runner
    return runner


class RuleTransport(unittest.TestCase):
    def run_arm(self, temp, fixture, arm, **kwargs):
        arms = ablation.arm_sources(); checks = ablation.validators(arms)
        def get(pool, role): return fake_runner(pool, role, fixture, **kwargs)
        with patch.object(previous, 'installed_links'), patch.object(RunnerPool, 'get', get):
            return previous.run_row(Path(temp)/(fixture['id']+arm), Path(temp)/'unused', fixture, arm, arms[arm], checks[arm])

    def test_fixtures_extend_the_recorded_cases_with_disjoint_strict_held_out_cases(self):
        self.assertEqual(ablation.FIXTURES[:4], previous.FIXTURES)
        held = ablation.FIXTURES[4:]
        self.assertFalse({f['id'] for f in held} & {f['id'] for f in previous.FIXTURES})
        self.assertEqual([f['control'] for f in held], [f['control'] for f in previous.FIXTURES])
        for fixture in ablation.FIXTURES:
            if fixture['control'] in ('missing_rule', 'corrupt_prior'):
                self.assertEqual(fixture['oracle']['action'], 'UNKNOWN')
        validate(ablation.CONFIG)

    def test_re_split_schema_fits_the_same_token_budget(self):
        module = ablation.base.module('schema', ablation.arm_sources()['earlier_quotes']['cognition'])
        tokens = ablation.CONFIG['observer_tokens']; schema = module.offer_schema(tokens); pr = schema['properties']
        chars = max(110, int((tokens-30)*2.2))
        used = (pr['summary']['maxLength']+pr['uncertainty']['maxLength']+pr['quotes']['maxItems']*pr['quotes']['items']['maxLength']
                + pr['earlier_quotes']['maxItems']*pr['earlier_quotes']['items']['maxLength'])
        self.assertLessEqual(used, chars)
        self.assertIn('earlier_quotes', schema['required'])
        self.assertNotIn('earlier_quotes', module.OFFER_SCHEMA['properties'])  # canonical schema untouched

    def test_earlier_quotes_arm_delivers_verified_prior_rule_and_current_arm_does_not(self):
        fixture = ablation.FIXTURES[0]
        with tempfile.TemporaryDirectory() as temp:
            current = self.run_arm(temp, fixture, 'current')
            earlier = self.run_arm(temp, fixture, 'earlier_quotes')
        self.assertEqual(current['status'], 'RECORDED', current)
        self.assertEqual(earlier['status'], 'RECORDED', earlier)
        self.assertEqual(current['delivered_prior_quotes'], [])
        self.assertEqual([q['text'] for q in earlier['delivered_prior_quotes']], ['Budget 61 euros.'])
        self.assertEqual(earlier['delivered_prior_quotes'][0]['verification'], 'EXACT_SOURCE_SUBSTRING_ONLY')
        self.assertFalse(earlier['oracle_visible_to_native'])

    def test_earlier_quotes_cannot_launder_current_text_or_invented_rules(self):
        fixture = ablation.FIXTURES[0]
        with tempfile.TemporaryDirectory() as temp:
            row = self.run_arm(temp, fixture, 'earlier_quotes', earlier=('Apply earlier project rules.', 'Budget 99 euros.'))
        self.assertEqual(row['status'], 'RECORDED', row)
        self.assertEqual(row['offer']['rejected_quotes'], 2)
        self.assertEqual(row['delivered_analysts'][0]['verified_quotes'], [])

    def test_wholesale_control_delivers_complete_hash_checked_prior_excerpt(self):
        fixture = ablation.FIXTURES[4]
        with tempfile.TemporaryDirectory() as temp:
            row = self.run_arm(temp, fixture, 'wholesale_control')
        self.assertEqual(row['status'], 'RECORDED', row)
        self.assertEqual([q['text'] for q in row['delivered_prior_quotes']], [fixture['prior']])
        self.assertEqual(row['delivered_prior_quotes'][0]['verification'], 'EXACT_EARLIER_SOURCE_WHOLESALE_CONTROL')

    def test_corrupt_prior_is_never_delivered_in_any_arm(self):
        for fixture in (ablation.FIXTURES[3], ablation.FIXTURES[7]):
            for arm in ablation.ARMS:
                with tempfile.TemporaryDirectory() as temp:
                    row = self.run_arm(temp, fixture, arm, earlier=('Budget 71 euros.',))
                self.assertEqual(row['status'], 'RECORDED', row)
                self.assertEqual(row['delivered_prior_quotes'], [])
                self.assertTrue(row['checks']['corrupt_prior_not_delivered'])
                self.assertNotIn('Budget 71 euros.', dumps(row['consumer_messages']))

    def test_preregistration_precedes_inference_and_resume_skips_recorded_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); prior = folder/'prior.json'; out = folder/'rt.json'
            prior.write_text(dumps({'status': 'RECORDED_DIAGNOSIS', 'summary': {}}))
            argv = ['rt', '--installed-home', str(folder/'installed'), '--previous-ablation', str(prior), '--out', str(out)]
            calls = []
            def infer(home, installed, fixture, arm, code, validator):
                registration = json.loads(out.with_suffix('.preregistration.json').read_text())
                self.assertEqual(registration['config']['observer_tokens'], 256)
                self.assertFalse(registration['native_oracle_visibility'])
                calls.append((fixture['id'], arm))
                return {'fixture': fixture['id'], 'arm': arm, 'control': fixture['control'], 'status': 'ERROR',
                        'score': {'utility': 0., 'exact': False}}
            with patch.object(ablation, 'binding', return_value={'fixed': True}), patch.object(previous, 'run_row', infer), \
                    patch('sys.argv', argv), contextlib.redirect_stdout(io.StringIO()):
                ablation.main(); first = out.read_bytes()
                self.assertEqual(len(calls), 24)
                self.assertEqual(json.loads(first)['status'], 'STRUCTURAL_FAIL')
                ablation.main()
                self.assertEqual(len(calls), 24)
                self.assertEqual(out.read_bytes(), first)

    def test_incomplete_previous_ablation_blocks_registration(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); prior = folder/'prior.json'; prior.write_text(dumps({'status': 'RUNNING'}))
            argv = ['rt', '--installed-home', str(folder), '--previous-ablation', str(prior), '--out', str(folder/'rt.json'), '--register-only']
            with patch('sys.argv', argv), self.assertRaisesRegex(ValueError, 'not a complete'):
                ablation.main()
            self.assertFalse((folder/'rt.preregistration.json').exists())


if __name__ == '__main__': unittest.main()

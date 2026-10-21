"""Software checks for the WP-Z3 isolation script (no native inference)."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('z3', HERE / 'c3_consumer_isolation.py')
Z = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Z)
FIXTURES = Z.A.strict_json((Z.FIX / 'generated/fixtures.json').read_text())['fixtures']


class Z3Tests(unittest.TestCase):
    def test_tool_only_matches_every_oracle(self):
        for f in FIXTURES:
            current = Z.G.render_current(f['public'])
            raw = Z.tool_answer(f['public']['project'], Z.deterministic(current, [s['text'] for s in f['sources']]))
            self.assertTrue(Z.score_decision(raw, f['oracle'])['exact'], f['id'])

    def test_v2_commits_on_contradiction_strict_refuses(self):
        f = next(f for f in FIXTURES if f['kind'] == 'contradictory_rule')
        current = Z.G.render_current(f['public'])
        texts = [s['text'] for s in f['sources']]
        budget = min(Z.E.stated_values('budget', ' '.join(texts)))
        deadline = next(iter(Z.E.stated_values('deadline', ' '.join(texts))))
        local = next(iter(Z.E.stated_values('local_only', ' '.join(texts))))
        rules = {'budget': budget, 'deadline': deadline, 'local_only': local}
        options = Z.parse_options(current)
        self.assertNotEqual(Z.E.decide(rules, options, current, texts)['action'], 'UNKNOWN')
        self.assertEqual(Z.strict_decide(rules, options, current, texts)['action'], 'UNKNOWN')

    def test_missing_rule_unknown(self):
        for f in (f for f in FIXTURES if f['kind'] == 'missing_rule'):
            current = Z.G.render_current(f['public'])
            self.assertEqual(Z.deterministic(current, [s['text'] for s in f['sources']])['action'], 'UNKNOWN')

    def test_decision_exact_ignores_only_project(self):
        f = next(f for f in FIXTURES if f['oracle']['action'] in 'AB')
        answer = dict(f['oracle'], project='Project ' + f['oracle']['project'])
        s = Z.summarize_answer(json.dumps(answer), f['oracle'])
        self.assertFalse(s['score']['exact'])
        self.assertTrue(s['decision_exact'])
        wrong = dict(f['oracle'], action='NONE')
        s = Z.summarize_answer(json.dumps(wrong), f['oracle'])
        self.assertTrue(s['wrong_commit'])
        self.assertFalse(Z.summarize_answer(json.dumps(dict(f['oracle'], action='UNKNOWN')), f['oracle'])['wrong_commit'])

    def test_summary_verdict_order(self):
        rows = []
        for f in FIXTURES[:5]:
            for arm in Z.ARMS:
                good = arm in ('c3_extract_tool_strict', 'tool_only')
                ans = f['oracle'] if good else dict(f['oracle'], action='UNKNOWN' if f['oracle']['action'] != 'UNKNOWN' else 'A')
                rows.append({'fixture': f['id'], 'kind': f['kind'], 'seed': 13, 'arm': arm, 'status': 'RECORDED'}
                            | Z.summarize_answer(json.dumps(ans), f['oracle']))
        s = Z.summarize(rows, {'arms': Z.ARMS, 'seeds': [13]})
        self.assertEqual(s['verdict'], 'TOOL_COMPLEMENTS_C3')
        self.assertEqual(s['arms']['tool_only']['decision_exact'], 1.)


if __name__ == '__main__':
    unittest.main()

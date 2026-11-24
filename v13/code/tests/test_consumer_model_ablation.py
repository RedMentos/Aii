"""Consumer-model ablation: offline input binding, schema order and decision rule."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import consumer_model_ablation as ablation
from scripts.rule_transport_ablation import FIXTURES
from tests.integration_step2_utility import SCHEMA
from v13.common import digest, dumps
from v13.utility import score_decision


def recorded_report():
    rows = [{'fixture': f['id'], 'arm': 'wholesale_control', 'consumer_messages': [{'role': 'user', 'content': f['current']}]} for f in FIXTURES]
    return {'status': 'RECORDED_DIAGNOSIS', 'preregistration_sha256': 'x', 'rows': rows,
            'row_sha256': {r['fixture']+'/wholesale_control': digest(dumps(r)) for r in rows}}


class ConsumerAblation(unittest.TestCase):
    def test_options_first_only_reorders_keys(self):
        changed = ablation.schema('options_first')
        self.assertEqual(list(changed['properties']), ['project', 'options', 'action'])
        self.assertEqual(changed['required'], ['project', 'options', 'action'])
        self.assertEqual({k: changed['properties'][k] for k in SCHEMA['properties']}, SCHEMA['properties'])
        self.assertIs(ablation.schema('action_first'), SCHEMA)
        answer = dict(FIXTURES[0]['oracle']); reordered = {k: answer[k] for k in ('project', 'options', 'action')}
        self.assertTrue(score_decision(dumps(reordered), FIXTURES[0]['oracle'])['exact'])

    def test_recorded_inputs_are_digest_bound_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'r.json'; report = recorded_report()
            path.write_text(dumps(report))
            _, inputs = ablation.recorded_inputs(path)
            self.assertEqual(set(inputs), {f['id'] for f in FIXTURES})
            changed = copy.deepcopy(report); changed['rows'][0]['consumer_messages'][0]['content'] = 'tampered'
            path.write_text(dumps(changed))
            with self.assertRaisesRegex(ValueError, 'row changed'): ablation.recorded_inputs(path)
            missing = copy.deepcopy(report); missing['rows'].pop()
            path.write_text(dumps(missing))
            with self.assertRaisesRegex(ValueError, 'incomplete'): ablation.recorded_inputs(path)
            path.write_text(dumps(report | {'status': 'RUNNING'}))
            with self.assertRaisesRegex(ValueError, 'not a complete'): ablation.recorded_inputs(path)

    def test_decision_rule_requires_decisions_and_unknowns(self):
        def rows(arm, answer):
            out = []
            for f in FIXTURES:
                raw = dumps(answer(f)); out.append({'fixture': f['id'], 'arm': arm, 'status': 'RECORDED',
                                                    'score': score_decision(raw, f['oracle']), 'action': json.loads(raw)['action']})
            return out
        oracle = rows(ablation.ARMS[0], lambda f: f['oracle'])
        none = rows(ablation.ARMS[1], lambda f: f['oracle'] | {'action': 'NONE'})
        summary = ablation.aggregate(oracle+none)
        self.assertTrue(summary[ablation.ARMS[0]]['passes_decision_rule'])
        self.assertEqual(summary[ablation.ARMS[0]]['exact_on_decidable'], 4)
        self.assertFalse(summary[ablation.ARMS[1]]['passes_decision_rule'])
        self.assertEqual(summary[ablation.ARMS[1]]['non_none_actions'], 0)

    def test_arms_cover_three_installed_files_and_both_orders(self):
        self.assertEqual(len(ablation.ARMS), 6)
        self.assertEqual({a.split('/')[0] for a in ablation.ARMS}, {'C3_LANGUAGE', 'B2_GIST', 'B1_DETAIL'})


if __name__ == '__main__': unittest.main()

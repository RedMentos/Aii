import json
import unittest
from pathlib import Path

from scripts import calc_tool_producer_ablation as P
from scripts.rule_transport_ablation import FIXTURES
from v13.common import dumps

REPORT = Path(__file__).resolve().parents[1]/'docs/proofs/continuation-20261012/rule-transport-ablation/report.json'


class ProducerToolTests(unittest.TestCase):
    def test_arms_and_inputs(self):
        self.assertEqual(len(P.ARMS), 12)
        inputs = P.recorded_inputs(REPORT)
        self.assertEqual(len(inputs), 16)

    def test_truncated_handoff_is_refused(self):
        inputs = P.recorded_inputs(REPORT)
        f = next(x for x in FIXTURES if x['id'] == 'Orrin')
        msg = inputs[('earlier_quotes', 'Orrin')]
        current, quotes = P.evidence(msg)
        if not any('Deadline 6' in q for q in quotes): self.skipTest('recorded handoff differs')
        raw = dumps({'project': 'Orrin', 'options': [{k: o[k] for k in ('entity', 'cost', 'days', 'local')} for o in f['oracle']['options']],
                     'budget': 58, 'deadline': 6, 'local_only': True})
        answer, info = P.run_anchored(raw, msg)
        self.assertEqual(json.loads(answer)['action'], 'UNKNOWN')  # "Deadline 6" without "days" is not a stated rule
        self.assertIn('deadline:not_stated', info['rejected'])

    def test_verdict_logic(self):
        rows = []
        for m in P.consumer.MODELS:
            for s in P.SOURCE_ARMS:
                for mode in P.MODES:
                    for f in FIXTURES:
                        rows.append({'arm': m+'/'+s+'/'+mode, 'fixture': f['id'], 'decision_exact': mode == 'extract_anchored' and f['id'] == 'Mira',
                                     'wrong_committed': False, 'action': 'UNKNOWN', 'score': {'utility': .5}, 'status': 'RECORDED'})
        v = P.aggregate(rows)['C3_LANGUAGE/current/verdict']
        self.assertTrue(v['safe']); self.assertTrue(v['useful'])


if __name__ == '__main__':
    unittest.main()

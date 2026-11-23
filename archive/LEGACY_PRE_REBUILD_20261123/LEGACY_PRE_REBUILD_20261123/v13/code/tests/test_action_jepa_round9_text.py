"""Round-9 text driver: preregistration binding, topic exclusion, resume and the fixed family verdict."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_round9_text as r9


def metrics(passing):
    per = {str(j): {'prediction_mse': .1, 'copy_mse': 1., 'mean_delta_mse': .5, 'shuffled_target_mse': .9} for j in range(4)}
    return {'candidate_gate_pass': passing, 'gates': {'predictive_gain_over_controls': passing}, 'checkpoint_sha256': 'c',
            'actions': ['negate', 'question', 'summarize', 'translate_de'],
            'after': {'test': {'per_action': per}, 'retention': {'per_action': per}},
            'before': {'retention': {'per_action': per}}}


class Round9TextTests(unittest.TestCase):
    def prereg(self, **change):
        doc = {'sources': {'scripts/action_jepa_round6_ridge.py': r9.sha(r9.SCRIPTS / 'action_jepa_round6_ridge.py')},
               'inputs': {}, 'fresh_topics': ['zoos'], 'reserve_topics': ['deserts'], 'topics_used_before': ['dogs'],
               'decision_rule': 'rule'}
        doc.update(change)
        return doc

    def test_preregistration_binds_sources_and_excludes_used_topics(self):
        r9.check_preregistration(self.prereg())
        with self.assertRaisesRegex(ValueError, 'never used'):
            r9.check_preregistration(self.prereg(reserve_topics=['dogs']))
        with self.assertRaisesRegex(ValueError, 'never used'):
            r9.check_preregistration(self.prereg(reserve_topics=['zoos']))
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            r9.check_preregistration(self.prereg(sources={'scripts/action_jepa_round6_ridge.py': '0' * 64}))

    def test_step_records_result_and_is_skipped_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 's'
            first = r9.step('x', out, [sys.executable, '-c', 'print("noise"); print(\'{"ok": 1}\')'])
            self.assertEqual(first['result'], {'ok': 1})
            again = r9.step('x', out, [sys.executable, '-c', 'raise SystemExit(3)'])
            self.assertEqual(again, first)
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                r9.step('y', Path(tmp) / 't', [sys.executable, '-c', 'raise SystemExit(3)'])

    def test_verdict_needs_more_than_half_of_six_runs(self):
        for passing, verdict in ((3, 'NOT_CONFIRMED'), (4, 'CONFIRMED')):
            with tempfile.TemporaryDirectory() as tmp:
                w = Path(tmp)
                for i, (kind, seed) in enumerate(r9.RUNS):
                    d = w / 'results' / ('l11_last-%s-s%d' % (kind, seed))
                    d.mkdir(parents=True)
                    (d / 'metrics.json').write_text(json.dumps(metrics(i < passing)))
                for name, doc in (('generation/generation-report.json', {'topics': ['zoos'], 'sentences': {'zoos': 24}}),
                                  ('export-round3/export-receipt.json', {'episodes': {'test': 24}, 'excluded_fresh': 0}),
                                  ('capture-layers/capture-report.json', {'rows': 1})):
                    (w / name).parent.mkdir(parents=True, exist_ok=True)
                    (w / name).write_text(json.dumps(doc))
                p = w / 'prereg.json'
                p.write_text('{}')
                report = r9.summarize(w, {'decision_rule': 'rule'}, p)
                self.assertEqual((report['passes'], report['verdict']), (passing, verdict))
                self.assertEqual(report['runs']['full-s13']['test_ratio_to_best_control']['negate'], .2)
                self.assertEqual(report['receiver_authority'], 0)


if __name__ == '__main__':
    unittest.main()

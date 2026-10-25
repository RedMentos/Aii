"""Run339 source-only frozen cohort, train-stream, selector and audit controls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_c3_contrastive_run339 as R
import audit_native_c3_contrastive_run339 as A


class DummyServer:
    pass


def fake_turn(server, q, a):
    return '<P>'+q+'</P>', a, '<END>'


def evaluation(facts=4, para=2, leak=.2, abstain=3, forget=0, invalid=0):
    return {'facts': [{}]*8, 'paraphrases': [{}]*6,
            'near_miss': [{}]*5,
            'probes': [{'q': str(i), 'ok': i >= forget} for i in range(12)],
            'invalid_outputs': invalid,
            'summary': {'facts_strict': facts, 'paraphrases_strict': para,
                        'near_miss_leak_strict': leak,
                        'near_miss_abstain_strict': abstain}}


def raw_evaluation(data):
    result = {}
    for name, rows, key, flag in (
        ('facts', data['facts'], 'keys', 'ok'),
        ('paraphrases', data['paraphrases'], 'keys', 'ok'),
        ('near_miss', data['near_miss'], 'leak_keys', 'leak'),
        ('probes', R.old.PROBES, 'expect', 'ok')):
        result[name] = []
        for x in rows:
            q = x.get('q', x.get('prompt'))
            ans = (x['a'] if name in ('facts', 'near_miss') else x[key][0])
            row = {'q': q, 'a': ans,
                   flag: R.old.hit(ans, x[key]),
                   'strict': R.old.hit(R.old.first_sentence(ans), x[key])}
            if name == 'near_miss':
                row['abstain'] = R.abstain(ans)
            result[name].append(row)
    result['invalid_outputs'] = 0
    result['summary'] = {
        'facts_strict': sum(x['strict'] for x in result['facts']),
        'paraphrases_strict': sum(x['strict'] for x in result['paraphrases']),
        'near_miss_leak_strict': round(sum(x['strict'] for x in result['near_miss'])/5, 3),
        'near_miss_abstain_strict': sum(x['abstain'] for x in result['near_miss']),
        'probes_ok': sum(x['ok'] for x in result['probes']),
        'invalid_outputs': 0,
        'facts_n': 8, 'paraphrases_n': 6, 'near_miss_n': 5, 'probes_n': 12,
    }
    return result


class Run339SourceOnly(unittest.TestCase):
    def test_frozen_cohort_and_source_disjoint(self):
        d = R.cohort()
        self.assertEqual(d['seed'], 53)
        self.assertEqual((len(d['facts']), len(d['paraphrases']), len(d['near_miss'])), (8, 6, 5))
        self.assertTrue(all('I do not know' in x['a'] for x in d['near_miss']))
        self.assertNotEqual(R.COHORT_SHA, R.old.COHORT_SHA)

    def test_stream_markers_and_near_miss_training_only_in_contrastive_arms(self):
        d = R.cohort()
        anchors = [('anchor '+str(i), 'baseline '+str(i)) for i in range(6)]
        with patch.object(R.old, 'turn', side_effect=fake_turn):
            streams = {name: R.make_stream(DummyServer(), d['facts'], d['near_miss'], c, replay,
                                           anchors if replay else [])
                       for name, (c, replay) in R.ARMS.items()}
        self.assertEqual([streams[n].count('<END>') for n in R.ARMS], [96, 156, 168])
        self.assertEqual([streams[n].count('\x01') for n in R.ARMS], [96, 156, 168])
        self.assertEqual([streams[n].count('\x02') for n in R.ARMS], [96, 156, 168])
        for row in d['near_miss']:
            self.assertNotIn(row['q'], streams['A_ANSWER_FACTS_ONLY'])
            self.assertIn(row['q'], streams['B_ANSWER_FACTS_NEGATIVE'])
            self.assertIn(row['q'], streams['C_ANSWER_FACTS_NEGATIVE_REPLAY'])
        for q, _ in anchors:
            self.assertEqual(streams['C_ANSWER_FACTS_NEGATIVE_REPLAY'].count('<P>'+q+'</P>'), 2)

    def test_deterministic_stream(self):
        d = R.cohort()
        with patch.object(R.old, 'turn', side_effect=fake_turn):
            a = R.make_stream(DummyServer(), d['facts'], d['near_miss'], True, False, [])
            b = R.make_stream(DummyServer(), d['facts'], d['near_miss'], True, False, [])
        self.assertEqual(a, b)

    def test_unregistered_stream_rejected(self):
        d = R.cohort()
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            R.make_stream(DummyServer(), d['facts'], d['near_miss'], False, True, [])
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            R.make_stream(DummyServer(), d['facts'], d['near_miss'], 'yes', False, [])

    def test_abstention_conservative_first_sentence_only(self):
        for a in ('I do not know the answer.', "I don't know.", 'Unknown.',
                  'Not specified in this fictional registry.',
                  'Cannot determine from the prompt.', 'I cannot determine that.'):
            self.assertTrue(R.abstain(a), a)
        for a in ('The answer is quartz.', 'It may be unknown.',
                  'The code is quartz. I do not know more.', 'Maybe quartz.'):
            self.assertFalse(R.abstain(a), a)

    def test_earliest_passing_epoch_candidate_only(self):
        base = evaluation()
        r = R.select(base, [evaluation(), evaluation(facts=6)])
        self.assertEqual(r['selected_epoch'], 1)
        self.assertEqual(r['selection'], 'CANDIDATE_ONLY_NO_ACTIVATION')
        self.assertFalse(r['AG6_promoted'])
        self.assertFalse(r['Body_JEPA_promoted'])

    def test_all_thresholds_independently_bind(self):
        base = evaluation()
        for bad in (evaluation(facts=3), evaluation(para=1), evaluation(leak=.4),
                    evaluation(abstain=2), evaluation(forget=1), evaluation(invalid=1)):
            self.assertEqual(R.select(base, [bad, bad])['selection'], 'NONE')

    def test_missing_epoch_denominator_rejected(self):
        bad = evaluation()
        bad['near_miss'].pop()
        with self.assertRaisesRegex(ValueError, 'denominator'):
            R.select(evaluation(), [bad, evaluation()])

    def test_no_overwrite_even_without_native_model(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):
                R.run('tools', 'server', 'master', 'manifest', td)

    def test_negative_gates_and_training_recipe_unchanged(self):
        self.assertEqual(R.GATES, {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
                                   'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0,
                                   'V13': 'INCOMPLETE'})
        self.assertEqual(R.TRAIN['epochs'], 2)
        self.assertEqual(R.TRAIN['lr'], 1e-5)
        self.assertEqual(R.CRITERIA['near_miss_abstain_strict_min'], 3)
        self.assertEqual(R.CRITERIA['forgotten_baseline_probes_max'], 0)

    def test_independent_raw_recompute_synthetic_only(self):
        data = R.cohort()
        row = raw_evaluation(data)
        self.assertEqual(A.recompute(row, data), row['summary'])

    def test_forged_abstention_label_rejected(self):
        data = R.cohort()
        row = raw_evaluation(data)
        row['near_miss'][0]['abstain'] = False
        with self.assertRaisesRegex(ValueError, 'abstention label drift'):
            A.recompute(row, data)

    def test_forged_near_miss_leak_label_rejected(self):
        data = R.cohort()
        row = raw_evaluation(data)
        row['near_miss'][0]['leak'] = True
        with self.assertRaisesRegex(ValueError, 'raw label drift'):
            A.recompute(row, data)

    def test_incomplete_native_report_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            A.audit({'schema': R.SCHEMA, 'status': 'INCOMPLETE'}, '/tmp/does-not-exist')


if __name__ == '__main__':
    unittest.main()

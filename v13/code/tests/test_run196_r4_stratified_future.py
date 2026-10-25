"""Synthetic contract tests only; no native inference and no production authority."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run196_r4_stratified_future as P


def h(text):
    return hashlib.sha256(text.encode()).hexdigest()


def setup(tmp):
    entries = []
    for seed, fixture in sorted(P.EXPECTED):
        prompt = f'Question {seed}:{fixture}?'
        entries.append({'seed': seed, 'fixture': fixture, 'prompt': prompt, 'task_sha256': h(prompt)})
    manifest = {'schema': P.TASK_SCHEMA, 'rows': entries}
    path = Path(tmp)/'tasks.json'
    path.write_text(json.dumps(manifest))
    pins = dict(model_sha256='1'*64, runner_sha256='2'*64,
                capture_script_sha256='3'*64, source_tree_sha256='4'*64,
                source_commit='5'*40)
    candidate = P.prepare(path, pins)
    cp = Path(tmp)/'candidate.json'
    P.write_once(cp, candidate)
    reg = P.seal(cp)
    rp = Path(tmp)/'registration.json'
    P.write_once(rp, reg)
    return manifest, reg, rp


def capture(reg, reg_path, *, wrong=(), uncertain=()):
    rows = []
    for k, task_hash in reg['task_hashes'].items():
        seed, fixture = k.split(':')
        key = (int(seed), fixture)
        lp = -1.0 if key in uncertain else -.1
        rows.append({'seed': int(seed), 'fixture': fixture, 'task_sha256': task_hash,
                     'pass': key not in wrong, 'answer_stream_matches_output': True,
                     'features': {'digit_min_logprob': lp},
                     'tokens': [{'token': '42', 'logprob': lp}]})
    return {'schema': P.CAPTURE_SCHEMA, 'registration_sha256': P.sha(reg_path),
            **{k: reg[k] for k in ('model_sha256', 'runner_sha256', 'capture_script_sha256',
                                  'source_tree_sha256', 'source_commit', 'task_manifest_sha256')},
            'rows': rows}


class Protocol(unittest.TestCase):
    def test_prepare_and_seal_are_non_authoritative(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, _ = setup(d)
            self.assertEqual(len(reg['task_hashes']), 120)
            self.assertEqual(reg['threshold'], P.THRESHOLD)
            self.assertEqual(reg['production_authority'], 0)
            self.assertFalse(reg['canonical_gate_pass'])

    def test_cannot_evaluate_unsealed_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, _ = setup(d)
            with self.assertRaisesRegex(ValueError, 'REGISTRATION_NOT_SEALED'):
                P.validate_reg(P.read_json(Path(d)/'candidate.json'))

    def test_success_is_prospective_criteria_only(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            wrong = set(sorted(P.EXPECTED)[::6])  # 20 wrong across strata
            cp = Path(d)/'capture.json'
            P.write_once(cp, capture(reg, rp, wrong=wrong, uncertain=wrong))
            result = P.evaluate(rp, cp)
            self.assertEqual(result['verdict'], 'PROSPECTIVE_CRITERIA_MET_NO_DEPLOYMENT')
            self.assertEqual(result['failure_reasons'], [])
            self.assertEqual(result['production_authority'], 0)

    def test_compare_stratum_high_error_blocks_global_gain(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            compare = [x for x in sorted(P.EXPECTED) if x[1].startswith('compare')]
            wrong = set(compare[:10]) | set([x for x in sorted(P.EXPECTED) if not x[1].startswith('compare')][::9])
            uncertain = wrong - set(compare[:10])
            cp = Path(d)/'capture.json'
            P.write_once(cp, capture(reg, rp, wrong=wrong, uncertain=uncertain))
            result = P.evaluate(rp, cp)
            self.assertEqual(result['verdict'], 'NOT_SUPPORTED')
            self.assertIn('COMPARE_RISK_FAIL', result['failure_reasons'])

    def test_correct_abstention_has_explicit_cost(self):
        rows = [{'pass': True, '_selected': False}, {'pass': False, '_selected': False}]
        m = P._metrics(rows)
        self.assertEqual(m['correct_abstained'], 1)
        self.assertEqual(m['wrong_abstained'], 1)
        self.assertEqual(m['utility_quarters'], -3)
        self.assertEqual(m['raw_utility_quarters'], -4)

    def test_seed7_and_seed11_rejected_as_unseen(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            cp = Path(d)/'capture.json'
            c = capture(reg, rp)
            c['rows'][0]['seed'] = 11
            P.write_once(cp, c)
            with self.assertRaisesRegex(ValueError, 'TASK_SET_MISMATCH'):
                P.evaluate(rp, cp)

    def test_tampered_model_hash_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            cp = Path(d)/'capture.json'
            c = capture(reg, rp)
            c['model_sha256'] = 'a'*64
            P.write_once(cp, c)
            with self.assertRaisesRegex(ValueError, 'CAPTURE_MODEL_SHA256_MISMATCH'):
                P.evaluate(rp, cp)

    def test_tampered_task_binding_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            cp = Path(d)/'capture.json'
            c = capture(reg, rp)
            c['rows'][0]['task_sha256'] = 'f'*64
            P.write_once(cp, c)
            with self.assertRaisesRegex(ValueError, 'CAPTURE_TASK_MISMATCH'):
                P.evaluate(rp, cp)

    def test_missing_or_duplicate_task_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            cp = Path(d)/'capture.json'
            c = capture(reg, rp)
            c['rows'][0] = copy.deepcopy(c['rows'][1])
            P.write_once(cp, c)
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_FIXTURE'):
                P.evaluate(rp, cp)

    def test_no_digit_token_abstains(self):
        row = {'tokens': [{'token': 'no answer', 'logprob': -.01}],
               'features': {'digit_min_logprob': 0.0}}
        self.assertEqual(P._uncertainty(row), float('inf'))

    def test_nan_and_positive_logprob_refused(self):
        for lp in (float('nan'), .1):
            with self.subTest(lp=lp):
                with self.assertRaisesRegex(ValueError, 'FEATURE_INVALID'):
                    P._uncertainty({'tokens': [{'token': '42', 'logprob': -.1}],
                                    'features': {'digit_min_logprob': lp}})

    def test_changed_threshold_or_utility_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, _ = setup(d)
            for key, val, message in [('threshold', .2, 'THRESHOLD_RESELECTED'),
                                      ('min_stratum_coverage', .1, 'DECISION_RULE_CHANGED')]:
                bad = dict(reg, **{key: val})
                with self.assertRaisesRegex(ValueError, message):
                    P.validate_reg(bad)

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'evidence.json'
            P.write_once(p, {'x': 1})
            with self.assertRaisesRegex(ValueError, 'REFUSE_OVERWRITE'):
                P.write_once(p, {'x': 2})
            self.assertEqual(P.read_json(p), {'x': 1})

    def test_manifest_prompt_hash_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            manifest, reg, _ = setup(d)
            manifest['rows'][0]['prompt'] = 'tampered'
            p = Path(d)/'bad.json'; p.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'TASK_PROMPT_HASH_MISMATCH'):
                P.prepare(p, {k: reg[k] for k in ('model_sha256', 'runner_sha256',
                           'capture_script_sha256', 'source_tree_sha256', 'source_commit')})


if __name__ == '__main__': unittest.main()

# Independent adversarial additions: feature spoof and per-seed concentration.
class IndependentReview(unittest.TestCase):
    def test_forged_digit_feature_refused(self):
        with self.assertRaisesRegex(ValueError, 'FEATURE_TOKEN_MISMATCH'):
            P._uncertainty({'tokens': [{'token': '42', 'logprob': -2.0}],
                            'features': {'digit_min_logprob': -.1}})

    def test_duplicate_prompts_across_seeds_refused(self):
        with tempfile.TemporaryDirectory() as d:
            manifest, reg, _ = setup(d)
            manifest['rows'][1]['prompt'] = manifest['rows'][0]['prompt']
            manifest['rows'][1]['task_sha256'] = manifest['rows'][0]['task_sha256']
            p = Path(d)/'duplicate.json';p.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_TASK_PROMPT'):
                P.prepare(p, {k: reg[k] for k in ('model_sha256', 'runner_sha256',
                           'capture_script_sha256', 'source_tree_sha256', 'source_commit')})

    def test_one_seed_compare_failure_cannot_hide_in_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            _, reg, rp = setup(d)
            compare_one = [x for x in sorted(P.EXPECTED) if x[0] == P.SEEDS[0] and x[1].startswith('compare')]
            wrong = set(compare_one[:4])
            # Other errors are filtered by uncertainty, so combined looks acceptable.
            other = [x for x in sorted(P.EXPECTED) if x not in wrong and not x[1].startswith('compare')]
            wrong.update(other[::9])
            uncertain = wrong - set(compare_one[:4])
            cp = Path(d)/'capture.json'
            P.write_once(cp, capture(reg, rp, wrong=wrong, uncertain=uncertain))
            result = P.evaluate(rp, cp)
            self.assertIn(f'SEED_{P.SEEDS[0]}_COMPARE_RISK_FAIL', result['failure_reasons'])
            self.assertEqual(result['verdict'], 'NOT_SUPPORTED')
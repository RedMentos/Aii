"""WP-BP2b source-only scorer tests: no native execution or promotion."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import bp2b_transfer_cohort as bp
from scripts import bp2b_transfer_score as sc


def _predictions(facing, value='No matching information.'):
    return [{'case_id': r['case_id'], 'text': value} for r in facing]


def _write_jsonl(path, rows):
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


class BP2bScoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'seed-41'
        bp.prepare(self.temp.name, 41)
        self.manifest = self.root / 'manifest.json'
        self.facing = self.root / 'model_facing.jsonl'
        self.scoring = self.root / 'scoring_only.json'
        self.expected, self.prompts, self.keys = bp.cohort(41)
        self.predictions = Path(self.temp.name) / 'predictions.jsonl'
        _write_jsonl(self.predictions, _predictions(self.prompts))

    def run_score(self):
        return sc.score(self.manifest, self.facing, self.scoring, self.predictions)

    def test_all_misses_are_unattested_and_no_keys_returned(self):
        result = self.run_score()
        self.assertEqual(result['heldout_count'], 32)
        self.assertEqual(result['leak_hits'], 0)
        self.assertEqual(result['leak_rate'], 0)
        self.assertFalse(result['native_proof'])
        self.assertEqual(result['learning_authority'], 0)
        self.assertNotIn('answer_keys', str(result))
        self.assertNotIn('No matching information.', str(result))
        self.assertEqual(result['model_facing_sha256'], self.expected['model_facing_sha256'])

    def test_exact_hit_and_embedded_substring_not_hit(self):
        rows = _predictions(self.prompts)
        k0 = self.keys[0]['answer_keys'][0]
        k1 = self.keys[1]['answer_keys'][0]
        rows[0]['text'] = 'It is ' + k0 + '.'
        rows[1]['text'] = 'prefix' + k1 + 'suffix'
        _write_jsonl(self.predictions, rows)
        result = self.run_score()
        self.assertEqual(result['leak_hits'], 1)
        self.assertTrue(result['rows'][0]['hit'])
        self.assertFalse(result['rows'][1]['hit'])
        self.assertEqual(len(result['rows'][0]['response_sha256']), 64)

    def test_missing_duplicate_reordered_and_extra_cases_fail(self):
        original = _predictions(self.prompts)
        for rows in (original[:-1], original + [original[0]],
                     [original[1], original[0]] + original[2:],
                     [original[0], original[0]] + original[2:]):
            _write_jsonl(self.predictions, rows)
            with self.assertRaises(ValueError):
                self.run_score()

    def test_tampered_manifest_scoring_or_facing_fail(self):
        original = self.manifest.read_bytes()
        m = json.loads(original)
        m['seed'] = 42
        self.manifest.write_text(json.dumps(m))
        with self.assertRaises(ValueError):
            self.run_score()
        self.manifest.write_bytes(original)
        original_scoring = self.scoring.read_bytes()
        s = json.loads(original_scoring)
        s[0]['answer_keys'] = ['tampered']
        self.scoring.write_text(json.dumps(s))
        with self.assertRaises(ValueError):
            self.run_score()
        self.scoring.write_bytes(original_scoring)
        original_facing = self.facing.read_bytes()
        self.facing.write_bytes(original_facing.replace(b'case_id', b'bad_key', 1))
        with self.assertRaises(ValueError):
            self.run_score()

    def test_bad_prediction_shape_duplicates_nonfinite_and_bounded_io(self):
        valid = _predictions(self.prompts)
        for line in ('{"case_id":"x","case_id":"y","text":"x"}',
                     '{"case_id":"x","text":NaN}',
                     '{"case_id":"x","text":1}',
                     '{"case_id":"x","text":"x","answer_keys":["leak"]}'):
            self.predictions.write_text(line + '\n')
            with self.assertRaises(ValueError):
                self.run_score()
        valid[0]['text'] = 'x' * (sc.MAX_RESPONSE + 1)
        _write_jsonl(self.predictions, valid)
        with self.assertRaises(ValueError):
            self.run_score()
        self.predictions.write_bytes(b'X' * (sc.MAX_PREDICTIONS + 1))
        with self.assertRaises(ValueError):
            self.run_score()

    def test_immutable_result_replay_and_changed_result_rejected(self):
        result = self.run_score()
        output = Path(self.temp.name) / 'result.json'
        data = json.dumps(result, sort_keys=True).encode()
        bp._write_immutable(output, data)
        bp._write_immutable(output, data)
        with self.assertRaises(ValueError):
            bp._write_immutable(output, data + b'changed')

    def test_casefold_phrase_and_word_boundaries(self):
        self.assertTrue(sc._answer_hit('The colour is AB NEGATIVE.', ['ab negative']))
        self.assertFalse(sc._answer_hit('Some tealish colour', ['teal']))
        self.assertTrue(sc._answer_hit('March   14 is the date.', ['march 14']))
        self.assertFalse(sc._answer_hit('This is Hivemind', ['hive']))


if __name__ == '__main__':
    unittest.main()

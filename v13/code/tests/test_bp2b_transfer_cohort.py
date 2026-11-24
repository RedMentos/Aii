"""WP-BP2b frozen transfer cohort, source-only software tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import bp2b_transfer_cohort as bp


class BP2bTransferTests(unittest.TestCase):
    def test_fixed_24x2_source_disjoint_and_hashes(self):
        proof = bp.validate()
        self.assertEqual(proof['all_heldout_count'], 48)
        self.assertEqual(len(proof['source_sha256']), 64)
        self.assertEqual(len(proof['heldout_sha256']), 64)
        self.assertEqual(proof, bp.validate())

    def test_three_new_seeds_and_model_facing_schema(self):
        indices = set()
        for seed in bp.SEEDS:
            manifest, prompts, scoring = bp.cohort(seed)
            self.assertEqual(manifest['seed'], seed)
            self.assertEqual(manifest['facts'], 16)
            self.assertEqual(manifest['heldout_rows'], 32)
            self.assertEqual(len(prompts), 32)
            self.assertEqual(len(scoring), 32)
            self.assertEqual(len(set(r['case_id'] for r in prompts)), 32)
            self.assertEqual([r['case_id'] for r in prompts], [r['case_id'] for r in scoring])
            self.assertEqual(manifest['model_facing_sha256'], bp._hash(prompts))
            self.assertEqual(manifest['scoring_only_sha256'], bp._hash(scoring))
            self.assertTrue(all(set(r) == {'case_id', 'prompt'} for r in prompts))
            self.assertTrue(all('target' not in r and 'answer_keys' not in r for r in prompts))
            self.assertTrue(all('answer_keys' in r and 'prompt' not in r for r in scoring))
            self.assertEqual(manifest['status'], 'SOURCE_ONLY_NATIVE_NOT_RUN')
            indices.add(tuple(manifest['selected_indices']))
        self.assertEqual(len(indices), 3)

    def test_prepare_immutable_restart_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            m = bp.prepare(d, 41)
            self.assertEqual(m, bp.prepare(d, 41))
            root = Path(d) / 'seed-41'
            prompt_rows = [json.loads(s) for s in (root/'model_facing.jsonl').read_text().splitlines()]
            self.assertEqual(len(prompt_rows), 32)
            self.assertEqual(bp._hash(prompt_rows), m['model_facing_sha256'])
            self.assertTrue(all(set(r) == {'case_id', 'prompt'} for r in prompt_rows))
            self.assertEqual(json.loads((root/'manifest.json').read_text()), m)
            (root/'model_facing.jsonl').write_text('TAMPERED\n')
            with self.assertRaises(ValueError):
                bp.prepare(d, 41)

    def test_reject_outside_seeds_and_boolean(self):
        for seed in (1, 2, 13, 42.0, True, -1):
            with self.assertRaises(ValueError):
                bp.cohort(seed)

    def test_reject_duplicate_and_train_subject_contamination(self):
        original = bp.HOLDOUT
        bad = list(original)
        bad[0] = (original[0][0], original[0][0])
        with patch.object(bp, 'HOLDOUT', tuple(bad)):
            with self.assertRaises(ValueError):
                bp.validate()
        bad[0] = ('What name does my friend use for their cat?', original[0][1])
        with patch.object(bp, 'HOLDOUT', tuple(bad)):
            with self.assertRaises(ValueError):
                bp.validate()

    def test_reject_expected_answer_leakage(self):
        original = bp.HOLDOUT
        bad = list(original)
        bad[0] = ('What name is Mitzi?', original[0][1])
        with patch.object(bp, 'HOLDOUT', tuple(bad)):
            with self.assertRaises(ValueError):
                bp.validate()


if __name__ == '__main__':
    unittest.main()

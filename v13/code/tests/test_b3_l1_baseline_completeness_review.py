"""B3 L1 may not advance from incomplete or malformed paired evidence."""
import copy
import math
import unittest

from v13 import b3bridge as BB

REQUIRED = ('NO_MESSAGE', 'LATENT', 'LATENT_SHUFFLED', 'LATENT_RANDOM',
            'EXACT', 'CONTROL', 'SYMBOLIC')


def complete():
    return {
        'acc': {
            'NO_MESSAGE': [.6]*5,
            'LATENT': [.90, .91, .90, .92, .90],
            'LATENT_SHUFFLED': [.6]*5,
            'LATENT_RANDOM': [.6]*5,
            'EXACT': [.95]*5,
            'CONTROL': [.7]*5,
            'SYMBOLIC': [.7]*5,
        },
        'bytes': {'NO_MESSAGE': 0, 'LATENT': 64, 'LATENT_SHUFFLED': 64,
                  'LATENT_RANDOM': 64, 'EXACT': 3900, 'CONTROL': 200,
                  'SYMBOLIC': 60},
        'role_drop': 0.0, 'ood_rate': 0.01, 'reload_identical': True,
    }


class B3L1BaselineCompletenessReview(unittest.TestCase):
    def test_complete_positive_control_passes_without_runtime_authority(self):
        result = BB.l1_gate(complete())
        self.assertEqual(result['verdict'], 'PASS')
        self.assertEqual(result['missing_baselines'], [])
        self.assertIn('L2', result['consequence'])
        self.assertNotIn('LATENT authority granted', result['consequence'])

    def test_every_required_comparator_is_mandatory(self):
        for channel in REQUIRED:
            with self.subTest(channel=channel):
                item = complete()
                del item['acc'][channel]
                result = BB.l1_gate(item)
                self.assertEqual(result['verdict'], 'FAIL')
                self.assertIn(channel, result['missing_baselines'])

    def test_mismatched_lengths_cannot_pass_by_zip_truncation(self):
        for channel in REQUIRED:
            with self.subTest(channel=channel):
                item = complete()
                item['acc'][channel] = item['acc'][channel][:4]
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_nonfinite_empty_or_out_of_range_evidence_fails_closed(self):
        for channel in REQUIRED:
            for bad in ([], [float('nan')]*5, [float('inf')]*5, [-.1]*5, [1.1]*5):
                with self.subTest(channel=channel, bad=str(bad)):
                    item = complete()
                    item['acc'][channel] = bad
                    self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_invalid_bytes_and_truthy_flags_cannot_pass(self):
        for channel in REQUIRED:
            for bad in (-1, float('nan'), '64'):
                with self.subTest(channel=channel, bad=str(bad)):
                    item = complete()
                    item['bytes'][channel] = bad
                    self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')
        for field, bad in (('reload_identical', 'yes'), ('role_drop', -0.5),
                           ('ood_rate', -0.2), ('role_drop', float('nan')),
                           ('ood_rate', float('inf'))):
            with self.subTest(field=field, bad=str(bad)):
                item = complete()
                item[field] = bad
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_actual_negative_controls_remain_negative(self):
        cheap_exact = complete()
        cheap_exact['bytes']['EXACT'] = 40
        self.assertEqual(BB.l1_gate(cheap_exact)['verdict'], 'FAIL')
        role_drop = complete()
        role_drop['role_drop'] = .05
        self.assertEqual(BB.l1_gate(role_drop)['verdict'], 'FAIL')


if __name__ == '__main__':
    unittest.main()

"""B3 L1 diagnostic pairing requires declared unique ordered seed IDs for all arms."""
import unittest
from v13 import b3bridge as BB
from tests.test_b3_l1_baseline_completeness_review import complete

REQUIRED = ('NO_MESSAGE', 'LATENT', 'LATENT_SHUFFLED', 'LATENT_RANDOM',
            'EXACT', 'CONTROL', 'SYMBOLIC')
SEEDS = ['s01', 's02', 's03', 's04', 's05']


def paired_complete():
    item = complete()
    item['seed_ids'] = {channel: list(SEEDS) for channel in REQUIRED}
    return item


class B3L1SeedIdentityReview(unittest.TestCase):
    def test_complete_paired_synthetic_control_still_passes_only_diagnostic(self):
        result = BB.l1_gate(paired_complete())
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertIn('authority stays 0', result['consequence'])

    def test_missing_identity_cannot_be_a_paired_pass(self):
        result = BB.l1_gate(complete())
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('seed_ids', ' '.join(result.get('invalid_evidence', [])))

    def test_permuted_channel_ids_are_not_paired(self):
        for channel in REQUIRED:
            with self.subTest(channel=channel):
                item = paired_complete()
                item['seed_ids'][channel] = list(reversed(SEEDS))
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_different_seed_with_same_length_is_not_paired(self):
        for channel in REQUIRED:
            with self.subTest(channel=channel):
                item = paired_complete()
                item['seed_ids'][channel][-1] = 'unregistered'
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_duplicate_ids_cannot_fake_independent_replicates(self):
        for channel in REQUIRED:
            with self.subTest(channel=channel):
                item = paired_complete()
                item['seed_ids'][channel][1] = SEEDS[0]
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_missing_channel_or_short_ids_fail_closed(self):
        item = paired_complete()
        del item['seed_ids']['CONTROL']
        self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')
        item = paired_complete()
        item['seed_ids']['LATENT'] = item['seed_ids']['LATENT'][:-1]
        self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_invalid_ids_are_refused(self):
        for bad in ('', '  ', 'x'*33, True, 1.0, None, [], 'space here', '../escape'):
            with self.subTest(bad=repr(bad)):
                item = paired_complete()
                item['seed_ids']['LATENT'][2] = bad
                self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_nonzero_no_message_cost_refused(self):
        item = paired_complete()
        item['bytes']['NO_MESSAGE'] = 200
        self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')

    def test_original_negative_controls_stay_negative(self):
        item = paired_complete()
        item['bytes']['EXACT'] = 40
        self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')
        item = paired_complete()
        item['role_drop'] = .05
        self.assertEqual(BB.l1_gate(item)['verdict'], 'FAIL')


if __name__ == '__main__':
    unittest.main()

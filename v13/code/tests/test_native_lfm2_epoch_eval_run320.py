"""Run320 source/selector fixture tests only; never native weight-training proof."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import native_lfm2_epoch_eval_run320 as R


def evaluation(facts=3, para=2, leak=0.2, invalid=0, lost=()):
    probes = [{'q': 'probe-' + str(i), 'ok': i not in lost} for i in range(12)]
    return {
        'facts': [{'q': str(i)} for i in range(8)],
        'paraphrases': [{'q': str(i)} for i in range(6)],
        'near_miss': [{'q': str(i)} for i in range(5)],
        'probes': probes, 'invalid_outputs': invalid,
        'summary': {'facts_strict': facts, 'para_strict': para,
                    'near_miss_leak_strict': leak},
    }


class NativeLFM2EpochRun320(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_registered_source_and_denominators(self):
        R.verify_sources()
        self.assertEqual((len(R.FACTS), len(R.PARAPHRASES), len(R.NEAR_MISS), len(R.PROBES)), (8, 6, 5, 12))
        self.assertEqual(R.TRAIN['epochs'], 2)
        self.assertEqual(R.TRAIN['seed'], 13)
        self.assertEqual(R.HF_REVISION, '9e6c6ccf47cd318696e137d381a7ded8fe4df09f')

    def test_earliest_passing_epoch_never_promotes_authority(self):
        base = evaluation(facts=0, para=0, leak=0)
        e1 = evaluation(facts=3, para=2, leak=0.2)
        e2 = evaluation(facts=4, para=3, leak=0.0)
        out = R.select(base, [e1, e2])
        self.assertEqual(out['selected_epoch'], 1)
        self.assertEqual(out['selection'], 'CANDIDATE_ONLY_NO_ACTIVATION')
        self.assertFalse(out['AG6_promoted'])
        self.assertFalse(out['body_jepa_promoted'])

    def test_none_selected_on_retention_loss_even_if_facts_improve(self):
        base = evaluation(facts=0, para=0, leak=0)
        e1 = evaluation(facts=8, para=6, leak=0, lost=(0,))
        e2 = evaluation(facts=8, para=6, leak=0.4)
        out = R.select(base, [e1, e2])
        self.assertIsNone(out['selected_epoch'])
        self.assertEqual(out['selection'], 'NONE')
        self.assertEqual(out['rows'][0]['forgotten_baseline_probes'], 1)

    def test_near_miss_or_invalid_outputs_veto(self):
        base = evaluation()
        out = R.select(base, [evaluation(leak=0.4), evaluation(invalid=1)])
        self.assertEqual(out['selection'], 'NONE')
        self.assertEqual([x['diagnostic_pass'] for x in out['rows']], [False, False])

    def test_denominator_mismatch_is_fail_closed(self):
        base = evaluation()
        bad = evaluation()
        bad['near_miss'].pop()
        with self.assertRaisesRegex(ValueError, 'denominator'):
            R.select(base, [bad])
        base['probes'].pop()
        with self.assertRaisesRegex(ValueError, 'baseline probe'):
            R.select(base, [evaluation()])

    def test_native_receipt_validation_fixture_not_proof(self):
        out = self.root / 'trained.gguf'
        rows = []
        for i in (1, 2):
            p = Path(str(out) + '.epoch' + str(i) + '.gguf')
            p.write_bytes(bytes([i]) * 2048)
            rows.append({'epoch': i, 'out': str(p), 'bytes': 2048})
        text = '\n'.join('V13_EPOCH_CHECKPOINT ' + json.dumps(x) for x in rows)
        got = R.validate_receipts(text, out, 2)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]['sha256'], R.digest(Path(rows[0]['out'])))
        Path(rows[1]['out']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'byte count'):
            R.validate_receipts(text, out, 2)
        with self.assertRaisesRegex(ValueError, 'missing or extra'):
            R.validate_receipts(text.splitlines()[0], out, 2)

    def test_invalid_master_or_existing_out_never_trains(self):
        master = self.root / 'fake.gguf'
        master.write_bytes(b'not-a-master')
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps({'hf_repo': R.HF_REPO, 'hf_revision': R.HF_REVISION,
                                        'master_sha256': R.digest(master),
                                        'conversion_outtype': 'f32',
                                        'llama_source_sha256': '4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe'}))
        server = self.root / 'server'
        server.write_text('fake')
        with self.assertRaisesRegex(ValueError, 'suspiciously small'):
            R.run(self.root, server, master, manifest, self.root / 'new')


if __name__ == '__main__':
    unittest.main()

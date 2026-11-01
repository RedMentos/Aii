import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import action_jepa_delta_storage as delta
import capture_action_jepa_taps as cap
from export_action_jepa_dataset import ACTIONS


class DeltaStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        topics = {f'topic{i:02d}': [f'sentence{i}'] for i in range(16)}
        outcomes = {s: {a: f'{a}:{s}' for a in ACTIONS} for values in topics.values() for s in values}
        for name, value in [('sentences', topics), ('actions', outcomes)]:
            cap.atomic_json(self.root/name, value)
        _, _, self.texts = cap.corpus(self.root/'sentences', self.root/'actions')
        self.capture, self.base = self.root/'capture', self.root/'base'
        self.capture.mkdir(); self.base.mkdir()
        reg = {'expected_dim': 1024, 'expected_rows': len(self.texts), 'texts_sha256': cap.json_sha(self.texts)}
        reg.update({name: cap.artifact(self.root/name) for name in ('sentences', 'actions')})
        cap.atomic_json(self.capture/'registration.json', reg)
        (self.base/'registration.json').write_bytes((self.capture/'registration.json').read_bytes())
        self.rs = cap.sha(self.capture/'registration.json')
        records = []
        chunks = []
        for start in (0, 16, 32):
            payload = {'model': 'unit-fixture', 'data': [{'index': i, 'embedding': [float(start+i)/81]*1024} for i in range(16)]}
            raw = {'registry_sha256': self.rs, 'start': start, 'end': start+16, 'inputs': self.texts[start:start+16], 'response': payload, 'model_alias': 'unit-fixture'}
            name = f'batch-{start}.json'
            cap.atomic_json(self.capture/name, raw)
            records.append({'path': name, 'sha256': cap.sha(self.capture/name)})
            chunks.append(cap.validate_response(payload, 16, 'unit-fixture'))
            if start == 0:
                (self.base/name).write_bytes((self.capture/name).read_bytes())
                cap.write_checkpoint(self.base, chunks[0], self.texts, self.rs, records.copy())
        cap.write_checkpoint(self.capture, np.concatenate(chunks), self.texts, self.rs, records)
        self.archive = self.root/'delta.zip'

    def sealed(self):
        return delta.seal(self.capture, self.archive, 16)

    def mutate(self, change):
        with zipfile.ZipFile(self.archive) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        receipt = json.loads(entries['DELTA-RECEIPT.json'])
        change(entries, receipt)
        entries['DELTA-RECEIPT.json'] = json.dumps(receipt).encode()
        self.archive.unlink()
        delta.deterministic_zip(self.archive, entries)

    def rejected(self):
        out = self.root/'restored'
        with self.assertRaises((ValueError, KeyError)):
            delta.restore(self.base, [self.archive], out)
        self.assertFalse(out.exists())

    def test_exact_whole_npz_and_raw_bytes_roundtrip(self):
        receipt = self.sealed()
        self.assertTrue(receipt['original_whole_npz_byte_regeneration_verified'])
        out = self.root/'restored'
        report = delta.restore(self.base, [self.archive], out)
        self.assertEqual(report['completed_rows'], 48)
        self.assertEqual((out/'taps.npz').read_bytes(), (self.capture/'taps.npz').read_bytes())
        for name in ('batch-0.json', 'batch-16.json', 'batch-32.json'):
            self.assertEqual((out/name).read_bytes(), (self.capture/name).read_bytes())

    def test_missing_raw_batch_is_rejected(self):
        self.sealed(); self.mutate(lambda e, r: e.pop('batch-16.json')); self.rejected()

    def test_reordered_raw_records_are_rejected(self):
        self.sealed()
        def change(e, r):
            r['all_batch_records'][1:] = r['all_batch_records'][1:][::-1]
        self.mutate(change); self.rejected()

    def test_digest_changed_raw_response_is_rejected(self):
        self.sealed(); self.mutate(lambda e, r: e.update({'batch-16.json': e['batch-16.json']+b' '})); self.rejected()

    def test_malformed_receipt_or_npz_digest_is_rejected(self):
        self.sealed(); self.mutate(lambda e, r: r.update({'original_npz_sha256': 'invalid'})); self.rejected()

    def test_no_approximate_regeneration_allowed(self):
        with patch.object(delta, 'regenerate', return_value=b'different'):
            with self.assertRaisesRegex(ValueError, 'whole NPZ bytes'):
                self.sealed()
        self.assertFalse(self.archive.exists())

    def test_changed_source_corpus_is_rejected(self):
        self.sealed(); (self.root/'actions').write_text('tampered'); self.rejected()

    def test_wrong_base_boundary_and_duplicate_delta_fail(self):
        with self.assertRaises(ValueError):
            delta.seal(self.capture, self.archive, 17)
        self.sealed()
        out = self.root/'restored'
        with self.assertRaises(ValueError):
            delta.restore(self.base, [self.archive, self.archive], out)
        self.assertFalse(out.exists())

    def test_archive_cannot_overwrite_existing_evidence(self):
        self.sealed()
        with self.assertRaisesRegex(ValueError, 'never overwrite'):
            self.sealed()

    def test_full_array_digest_is_strict(self):
        self.sealed(); self.mutate(lambda e, r: r.update({'array_sha256': '0'*64})); self.rejected()


if __name__ == '__main__':
    unittest.main()

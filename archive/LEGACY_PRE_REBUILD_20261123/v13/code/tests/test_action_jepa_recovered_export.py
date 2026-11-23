"""Recovered-capture export guards; all taps are generated test data, no native model starts."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_objective as aj
import capture_action_jepa_taps as cap
import export_action_jepa_dataset as ex
import export_action_jepa_recovered_dataset as rec
import tests.test_action_jepa_export as export_tests


class RecoveredExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = self.root = Path(self.temp.name)
        self.sp, self.ap, self.pp, taps, mp, raw, texts = export_tests.ExportTests().fixture(root)
        manifest = json.loads(mp.read_text())
        # Recovered capture: same registration, new raw responses with identical floats.
        self.restored = root / 'restored'
        self.restored.mkdir()
        reg = {'plan': cap.artifact(self.pp), 'sentences': cap.artifact(self.sp), 'actions': cap.artifact(self.ap),
               'texts_sha256': cap.json_sha(texts), 'artifacts': manifest['artifacts'],
               'runtime_libraries': manifest['runtime_libraries']}
        cap.atomic_json(self.restored / 'registration.json', reg)
        rs = cap.sha(self.restored / 'registration.json')
        records = []
        for start in range(0, len(texts), 16):
            end = min(start + 16, len(texts))
            payload = {'model': 'unit-recovered', 'data': [{'index': i - start, 'embedding': raw[i].tolist()} for i in range(start, end)]}
            name = f'batches/batch-{start:05d}-{end:05d}.json'
            (self.restored / 'batches').mkdir(exist_ok=True)
            cap.atomic_json(self.restored / name, {'registry_sha256': rs, 'start': start, 'end': end,
                                                   'inputs': texts[start:end], 'response': payload,
                                                   'model_alias': 'unit-recovered'})
            records.append({'path': name, 'sha256': cap.sha(self.restored / name)})
        cap.write_checkpoint(self.restored, raw, texts, rs, records)
        # Reference (preregistered) export from the original, now "lost" taps file.
        manifest['registration_sha256'] = rs
        mp.write_text(json.dumps(manifest))
        ex.export_dataset(self.pp, self.sp, self.ap, taps, mp, root / 'reference')
        self.zip = root / 'dataset-metadata.zip'
        self.write_reference((root / 'reference/dataset.json').read_bytes())

    def write_reference(self, dataset_bytes, encoder=None):
        with zipfile.ZipFile(self.zip, 'w') as z:
            z.writestr('RESTORE.json', json.dumps({'dataset_uncompressed_sha256': hashlib.sha256(dataset_bytes).hexdigest()}))
            z.writestr('encoder-binding.json', encoder or (self.root / 'reference/encoder-binding.json').read_bytes())
            z.writestr('dataset.json.gz', gzip.compress(dataset_bytes))

    def export(self, out='out'):
        return rec.export(self.restored, self.zip, self.pp, self.sp, self.ap, self.root / out)

    def test_recovered_export_keeps_preregistered_rows_and_records_deviation(self):
        receipt = self.export()
        self.assertTrue(receipt['rows_identical_to_preregistered_dataset'])
        self.assertEqual(receipt['pairs'], 16 * 3 * 4)
        self.assertEqual(receipt['native_taps_sha256'], cap.sha(self.restored / 'taps.npz'))
        manifest = json.loads((self.root / 'out/encoder-binding.json').read_text())
        self.assertFalse(manifest['recovered_export']['artifact_bytes_rehashed_locally'])
        self.assertFalse(manifest['recovered_export']['superseded_taps_bytes_available'])
        doc, x, *_ = aj.load_dataset(self.root / 'out/dataset.json')
        ref = json.loads((self.root / 'reference/dataset.json').read_text())
        self.assertEqual(doc['rows'], ref['rows'])
        self.assertEqual(receipt['receiver_authority'], 0)

    def test_reference_with_other_native_artifact_hash_is_rejected(self):
        manifest = json.loads((self.root / 'reference/encoder-binding.json').read_text())
        manifest['artifacts']['runner']['sha256'] = '0' * 64
        encoder = json.dumps(manifest).encode()
        ref = json.loads((self.root / 'reference/dataset.json').read_text())
        ref['bindings']['encoder']['sha256'] = hashlib.sha256(encoder).hexdigest()
        self.write_reference(json.dumps(ref).encode(), encoder)
        with self.assertRaisesRegex(ValueError, 'hashes differ'):
            self.export()
        self.assertFalse((self.root / 'out').exists())

    def test_edited_registration_breaks_native_lineage(self):
        reg = json.loads((self.restored / 'registration.json').read_text())
        reg['artifacts']['runner']['sha256'] = '0' * 64
        cap.atomic_json(self.restored / 'registration.json', reg)
        with self.assertRaisesRegex(ValueError, 'Checkpoint source'):
            self.export()

    def test_raw_batch_differing_from_floats_is_rejected(self):
        name = 'batches/batch-00016-00032.json'
        batch = json.loads((self.restored / name).read_text())
        batch['response']['data'][0]['embedding'][0] += 1
        cap.atomic_json(self.restored / name, batch)
        with self.assertRaisesRegex(ValueError, 'batch bytes changed'):
            self.export()

    def test_tampered_reference_dataset_is_rejected(self):
        with zipfile.ZipFile(self.zip) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        ref = json.loads(gzip.decompress(entries['dataset.json.gz']))
        ref['rows'][0]['partition'] = 'test'
        entries['dataset.json.gz'] = gzip.compress(json.dumps(ref).encode())
        with zipfile.ZipFile(self.zip, 'w') as z:
            for n, b in entries.items():
                z.writestr(n, b)
        with self.assertRaisesRegex(ValueError, 'Reference dataset bytes changed'):
            self.export()

    def test_nonempty_destination_is_rejected(self):
        (self.root / 'out').mkdir()
        (self.root / 'out/keep.txt').write_text('existing proof')
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.export()
        self.assertEqual((self.root / 'out/keep.txt').read_text(), 'existing proof')


if __name__ == '__main__':
    unittest.main()

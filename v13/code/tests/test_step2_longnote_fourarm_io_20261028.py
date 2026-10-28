"""Hash-bound on-disk STEP2 analysis, using synthetic closed evidence only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.step2_longnote_fourarm_io import load
from tests.test_step2_longnote_fourarm_analysis_20261028 import IDS, fixture


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FourArmSealedIO(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entries = []
        for r in fixture():
            arm, seed = r['arm'], r['seed']
            rawname = f'{arm}_s{seed}.raw'
            summaryname = f'{arm}_s{seed}.json'
            raw = f'closed-synthetic-evidence-{arm}-{seed}'.encode()
            r['raw_sha256'] = sha(raw)
            summary = json.dumps(r, sort_keys=True).encode()
            (self.root / rawname).write_bytes(raw)
            (self.root / summaryname).write_bytes(summary)
            self.entries.append({'arm': arm, 'seed': seed, 'summary': summaryname,
                                 'summary_sha256': sha(summary),
                                 'raw': rawname, 'raw_sha256': sha(raw)})
        self.seal()

    def seal(self):
        self.manifest = {'schema': 'V13_STEP2_FOURARM_EVIDENCE_V1',
                         'fixture_ids': list(IDS), 'runs': self.entries}
        data = json.dumps(self.manifest, sort_keys=True).encode()
        (self.root / 'manifest.json').write_bytes(data)
        self.pin = sha(data)

    def check(self):
        return load(self.root, 'manifest.json', self.pin, IDS, '2' * 64)

    def test_read_only_pinned_positive_and_no_gate_promotion(self):
        before = {p.name: sha(p.read_bytes()) for p in self.root.iterdir()}
        result = self.check()
        self.assertTrue(result['candidate_supported'])
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(before, {p.name: sha(p.read_bytes()) for p in self.root.iterdir()})

    def test_tampered_raw_summary_or_manifest_fail(self):
        for name in ('TC_s27.raw', 'TC_s27.json', 'manifest.json'):
            with self.subTest(name=name):
                p = self.root / name
                original = p.read_bytes()
                p.write_bytes(original + b'\n')
                with self.assertRaises(ValueError):
                    self.check()
                p.write_bytes(original)
        with self.assertRaises(ValueError):
            load(self.root, 'manifest.json', '0' * 64, IDS)

    def test_traversal_symlink_duplicate_paths_and_missing_run_fail(self):
        original = self.entries[0]['summary']
        for name in ('../outside.json', '/tmp/x.json', '..', 'x/y.json'):
            with self.subTest(name=name):
                self.entries[0]['summary'] = name
                self.seal()
                with self.assertRaises(ValueError):
                    self.check()
        self.entries[0]['summary'] = original
        self.entries[0]['raw'] = self.entries[1]['raw']
        self.seal()
        with self.assertRaises(ValueError):
            self.check()
        self.entries[0]['raw'] = 'TC_s27.raw'
        last = self.entries.pop()
        self.seal()
        with self.assertRaises(ValueError):
            self.check()
        self.entries.append(last)
        p = self.root / 'TC_s27.json'
        p.unlink()
        os.symlink('TC_s28.json', p)
        self.seal()
        with self.assertRaises((OSError, ValueError)):
            self.check()

    def test_duplicate_json_keys_and_nonfinite_constants_fail(self):
        p = self.root / 'manifest.json'
        data = p.read_bytes()
        p.write_bytes(data.replace(b'"schema":', b'"schema":"OTHER", "schema":', 1))
        self.pin = sha(p.read_bytes())
        with self.assertRaises(ValueError):
            self.check()
        p.write_bytes(data.replace(b'"schema":', b'"junk": NaN, "schema":', 1))
        self.pin = sha(p.read_bytes())
        with self.assertRaises(ValueError):
            self.check()

    def test_wrong_fixture_identity_and_unregistered_seed_fail(self):
        self.manifest['fixture_ids'][0] = 'OTHER'
        data = json.dumps(self.manifest).encode()
        (self.root / 'manifest.json').write_bytes(data)
        self.pin = sha(data)
        with self.assertRaises(ValueError):
            self.check()
        self.manifest['fixture_ids'][0] = IDS[0]
        self.entries[0]['seed'] = 100
        self.seal()
        with self.assertRaises(ValueError):
            self.check()


if __name__ == '__main__':
    unittest.main()

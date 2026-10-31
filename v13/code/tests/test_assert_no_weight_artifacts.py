"""Future-only artifact no-export guard, including Run117BJ failure shape."""
from pathlib import Path
import os
import tempfile
import unittest
from scripts.assert_no_weight_artifacts import inspect, main


class NoWeightArtifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'evidence'
        self.root.mkdir()
    def tearDown(self):
        self.tmp.cleanup()
    def test_raw_evidence_allowed(self):
        (self.root / 'NATIVE_RAW.log').write_text('native error\n')
        (self.root / 'SHA256SUMS').write_text('hash  file\n')
        (self.root / 'report.json').write_text('{"status":"RED"}\n')
        self.assertEqual(inspect(self.root)['status'], 'RAW_TELEMETRY_ONLY')
        self.assertEqual(main([str(self.root)]), 0)
    def test_run117bj_predictor_pt_refused(self):
        p = self.root / 'NATIVE_CASE' / 'work' / '263-CE'
        p.mkdir(parents=True)
        (p / 'predictor.pt').write_bytes(b'PK\x03\x04')
        r = inspect(self.root)
        self.assertEqual(r['status'], 'EXPORT_BOUNDARY_RED')
        self.assertIn('NOT_RAW_TELEMETRY:NATIVE_CASE/work/263-CE/predictor.pt', r['violations'])
        self.assertTrue((p / 'predictor.pt').exists())
        self.assertEqual(main([str(self.root)]), 1)
    def test_other_weight_extensions_refused(self):
        for n in ('adapter.safetensors', 'model.gguf', 'adapter.npz', 'pytorch_model.bin'):
            (self.root / n).write_bytes(b'abc')
        self.assertEqual(len(inspect(self.root)['violations']), 4)
    def test_disguised_binary_rejected(self):
        (self.root / 'metrics.json').write_bytes(b'\x80\x04\x00pickle')
        self.assertIn('BINARY_CONTENT:metrics.json', inspect(self.root)['violations'])
    def test_invalid_utf8_rejected(self):
        (self.root / 'metrics.json').write_bytes(b'\xff\xfe')
        self.assertIn('UNREADABLE_OR_NONUTF8:metrics.json', inspect(self.root)['violations'])
    def test_symlink_dir_refused_without_follow(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (outside / 'model.pt').write_bytes(b'secret')
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        self.assertIn('LINK_DIR:linked', inspect(self.root)['violations'])
    def test_symlink_file_refused(self):
        p = self.root / 'report.json'
        p.symlink_to(Path(self.tmp.name) / 'missing')
        self.assertIn('NOT_EXCLUSIVE_REGULAR_FILE:report.json', inspect(self.root)['violations'])
    def test_hardlink_refused(self):
        original = self.root / 'report.json'
        original.write_text('{}')
        os.link(original, self.root / 'duplicate.json')
        self.assertEqual(len(inspect(self.root)['violations']), 2)
    def test_empty_dir_and_missing_root(self):
        self.assertEqual(inspect(self.root)['status'], 'RAW_TELEMETRY_ONLY')
        self.assertEqual(inspect(self.root / 'missing')['status'], 'EXPORT_BOUNDARY_RED')


if __name__ == '__main__':
    unittest.main()

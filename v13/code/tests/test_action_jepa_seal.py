"""Byte-preserving archive helpers; partial native captures never become complete."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import seal_action_jepa_evidence as sealer


class SealTests(unittest.TestCase):
    def test_archive_is_byte_preserving_deterministic_and_nonoverwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            entries={'sources/example.txt':'Genaue Quelle üöß\n'.encode(), 'raw.json':b'{"x":[1.0000000000000002,2.7e-18]}\n'}
            sealer.deterministic_zip(root/'one.zip',entries)
            sealer.deterministic_zip(root/'two.zip',entries)
            self.assertEqual((root/'one.zip').read_bytes(),(root/'two.zip').read_bytes())
            with zipfile.ZipFile(root/'one.zip') as z:
                for name,raw in entries.items(): self.assertEqual(z.read(name),raw)
            with self.assertRaisesRegex(ValueError,'never overwrite'):
                sealer.deterministic_zip(root/'one.zip',entries)

    def test_partial_capture_cannot_be_sealed_as_completed_native_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            capture=root/'capture';capture.mkdir()
            (capture/'capture-manifest.json').write_text(json.dumps({'native_extraction_observed':False,'worker_reaped':True}))
            (capture/'registration.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Complete reaped actual'):
                sealer.seal(capture,root/'dataset.json',root/'sealed')
            self.assertFalse((root/'sealed').exists())


if __name__=='__main__':
    unittest.main()

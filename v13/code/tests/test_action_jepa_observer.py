"""Immutable source-check snapshot guards; no native process is started."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import resume_action_jepa_capture_observed as observer


class ObserverTests(unittest.TestCase):
    def files(self, root):
        raw = b'Original source bytes, not the changed current working tree.'
        report = root/'report.json'
        report.write_text(json.dumps({'proof_version': 3, 'status': 'UTILITY_FAIL', 'rows': [{}]*70,
                                     'source_hashes': {'v13/example.py': hashlib.sha256(raw).hexdigest()}}))
        archive = root/'source.tar.gz'
        with tarfile.open(archive, 'w:gz') as output:
            item = tarfile.TarInfo('v13/example.py')
            item.size = len(raw)
            output.addfile(item, io.BytesIO(raw))
        return archive, report, raw

    def test_exact_snapshot_checks_frozen_bytes_and_restores_APP_global(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive, report, raw=self.files(root)
            previous=observer.producer.APP
            source, result=observer.verify_snapshot(archive, observer.producer.sha(archive), report, root/'snapshot')
            self.assertTrue(result['frozen_source_intact'])
            self.assertFalse(result['utility_gate_inferred'])
            self.assertEqual((source/'v13/example.py').read_bytes(),raw)
            self.assertEqual(observer.producer.APP,previous)

    def test_changed_archive_or_snapshot_cannot_override_source_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            archive, report, _=self.files(root)
            with self.assertRaisesRegex(ValueError,'expected hash'):
                observer.verify_snapshot(archive,'0'*64,report,root/'snapshot')
            observer.verify_snapshot(archive,observer.producer.sha(archive),report,root/'snapshot')
            p=root/'snapshot/v13/example.py'
            p.chmod(0o644)
            p.write_text('changed')
            with self.assertRaisesRegex(ValueError,'snapshot changed'):
                observer.verify_snapshot(archive,observer.producer.sha(archive),report,root/'snapshot')


if __name__=='__main__':
    unittest.main()

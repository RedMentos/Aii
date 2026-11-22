"""Read-only sealed evidence audit regression tests (no native model dependencies)."""
import json
import os
from pathlib import Path
import tempfile
import unittest

try:
    from scripts import sealed_storage_streaming_candidate as seal
    from scripts import sealed_storage_integrity_audit as auditor
except ModuleNotFoundError:
    import sealed_storage_streaming_candidate as seal
    import sealed_storage_integrity_audit as auditor


class ReadonlyAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'original.closed.zip'
        self.parts=self.root/'parts'
        self.receipt=self.root/'verification.json'

    def fill(self,data):
        self.source.write_bytes(data)
        return seal.split(self.source,self.parts)

    def test_empty_small_exact_chunk_and_multichunk_full_hash(self):
        for n in (0, 1, seal.CHUNK_BYTES, seal.CHUNK_BYTES+7):
            with self.subTest(n=n):
                self.parts=self.root/f'parts-{n}'
                original=os.urandom(n)
                doc=self.fill(original)
                before={p.name:p.read_bytes() for p in self.parts.iterdir()}
                rec=auditor.audit(self.parts/'manifest.json')
                self.assertEqual(rec['expected_file_sha256'],doc['sha256'])
                self.assertEqual(rec['verified_file_sha256'],doc['sha256'])
                self.assertEqual(rec['verified_bytes'],n)
                self.assertFalse(rec['evidence_modified'])
                self.assertFalse(rec['native_models_launched'])
                self.assertFalse(rec['canonical_gate_pass'])
                self.assertEqual(before,{p.name:p.read_bytes() for p in self.parts.iterdir()})

    def test_corrupt_part_rejected_and_no_receipt(self):
        self.fill(os.urandom(seal.CHUNK_BYTES+4))
        path=self.parts/'part-00001.bin'
        path.write_bytes(b'nope')
        with self.assertRaisesRegex(ValueError,'bytes/hash mismatch'):
            auditor.audit(self.parts/'manifest.json')
        self.assertFalse(self.receipt.exists())

    def test_corrupt_full_manifest_hash_rejected(self):
        self.fill(b'x')
        path=self.parts/'manifest.json'
        doc=json.loads(path.read_text());doc['sha256']='0'*64
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'Whole evidence'):
            auditor.audit(path)

    def test_missing_symlinked_and_extra_parts_are_refused_correctly(self):
        self.fill(b'old bytes')
        part=self.parts/'part-00000.bin'
        part.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):
            auditor.audit(self.parts/'manifest.json')
        part.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError,'symlinked'):
            auditor.audit(self.parts/'manifest.json')
        part.unlink();part.write_bytes(self.source.read_bytes())
        (self.parts/'part-00999.bin').write_bytes(b'orphan')
        self.assertEqual(auditor.audit(self.parts/'manifest.json')['verified_parts'],1)
        with self.assertRaisesRegex(ValueError,'Unlisted'):
            auditor.audit(self.parts/'manifest.json',reject_unlisted=True)

    def test_publish_report_idempotent_but_never_overwrites_conflict(self):
        self.fill(b'evidence')
        report=auditor.audit(self.parts/'manifest.json')
        auditor.publish_report(report,self.receipt)
        saved=self.receipt.read_bytes()
        auditor.publish_report(report,self.receipt)
        self.assertEqual(saved,self.receipt.read_bytes())
        changed=dict(report,verified_bytes=99)
        with self.assertRaisesRegex(ValueError,'refusing overwrite'):
            auditor.publish_report(changed,self.receipt)
        self.assertEqual(saved,self.receipt.read_bytes())

    def test_report_path_symlink_refused(self):
        self.fill(b'evidence')
        self.receipt.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError,'symlink'):
            auditor.publish_report(auditor.audit(self.parts/'manifest.json'),self.receipt)
        self.assertEqual(self.source.read_bytes(),b'evidence')

    def test_bool_and_negative_manifest_counts_rejected(self):
        self.fill(b'evidence')
        path=self.parts/'manifest.json'
        doc=json.loads(path.read_text())
        for value in (True,-1,'7'):
            with self.subTest(value=value):
                copy=dict(doc,bytes=value)
                path.write_text(json.dumps(copy))
                with self.assertRaises(ValueError):auditor.audit(path)

if __name__ == '__main__':unittest.main()

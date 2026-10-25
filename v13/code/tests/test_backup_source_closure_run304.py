"""Run304 RED-first: a V13 backup must be closed over its live SQLite source blobs.

Actual Runtime/Store SQLite; synthetic text only. Software proof, not native/Redmi.
"""
import io
import json
import tarfile
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from v13 import backup as backup_module
from v13.backup import backup, unpack_verified
from v13.runtime import Runtime


class BackupSourceClosureRun304(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.ref = self.r.store.source('RUN304 synthetic exact source value', 'USER')
        self.blob = self.home / 'data' / 'blobs' / self.ref['sha256']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def snapshot(self, name='run304.tar.gz'):
        return backup(self.r.store, self.home / 'backups' / name)

    def unpack(self, archive):
        stage = self.home / 'tmp' / ('verify-' + archive.stem.replace('.', '-'))
        stage.mkdir(exist_ok=True)
        return unpack_verified(archive, stage, 1 << 30)

    def test_valid_plain_source_roundtrip(self):
        archive = self.snapshot()
        self.unpack(archive)
        self.assertEqual(self.r.store.read_source(self.ref), 'RUN304 synthetic exact source value')

    def test_live_blob_omitted_during_copy_rejects_snapshot_without_publishing(self):
        original = backup_module.shutil.copytree
        target = self.home / 'backups' / 'run304-omitted.tar.gz'

        def omit_after_copy(src, dst, *args, **kwargs):
            result = original(src, dst, *args, **kwargs)
            if Path(src).name == 'blobs':
                (Path(dst) / self.ref['sha256']).unlink()
            return result

        with patch.object(backup_module.shutil, 'copytree', side_effect=omit_after_copy):
            with self.assertRaisesRegex(ValueError, 'Source-Blob'):
                backup(self.r.store, target)
        self.assertFalse(target.exists())
        self.assertFalse(target.with_suffix('.partial').exists())
        self.assertEqual(self.r.store.read_source(self.ref), 'RUN304 synthetic exact source value')

    def test_live_plain_blob_tamper_rejected_before_publishing(self):
        self.blob.write_bytes(b'RUN304 tampered content')
        target = self.home / 'backups' / 'run304-corrupt.tar.gz'
        with self.assertRaisesRegex(ValueError, 'Source-Blob'):
            backup(self.r.store, target)
        self.assertFalse(target.exists())

    def test_valid_archived_blob_is_accepted_and_checked(self):
        b = self.blob.read_bytes()
        self.blob.with_name(self.blob.name + '.z').write_bytes(zlib.compress(b))
        self.blob.unlink()
        archive = self.snapshot('run304-archived.tar.gz')
        self.unpack(archive)
        self.assertEqual(self.r.store.read_source(self.ref), b.decode())

    def test_corrupt_archived_blob_is_rejected(self):
        self.blob.with_name(self.blob.name + '.z').write_bytes(zlib.compress(b'wrong content'))
        self.blob.unlink()
        with self.assertRaisesRegex(ValueError, 'Source-Blob'):
            self.snapshot('run304-archived-corrupt.tar.gz')

    def test_repacked_archive_missing_live_blob_is_rejected_even_with_consistent_manifest(self):
        good = self.snapshot('run304-good.tar.gz')
        with tarfile.open(good, 'r:gz') as tf:
            members = {m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
        blob_name = 'data/blobs/' + self.ref['sha256']
        self.assertIn(blob_name, members)
        del members[blob_name]
        manifest = json.loads(members['backup_manifest.json'])
        del manifest['hashes'][blob_name]
        members['backup_manifest.json'] = json.dumps(manifest).encode()
        forged = self.home / 'backups' / 'run304-repacked.tar.gz'
        with tarfile.open(forged, 'w:gz') as tf:
            for name, payload in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                tf.addfile(info, io.BytesIO(payload))
        with self.assertRaisesRegex(ValueError, 'Source-Blob'):
            self.unpack(forged)
        self.assertEqual(self.r.store.read_source(self.ref), 'RUN304 synthetic exact source value')

    def test_revoked_source_does_not_require_its_old_blob(self):
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (self.ref['source_id'],))
        self.blob.unlink()
        archive = self.snapshot('run304-revoked.tar.gz')
        self.unpack(archive)
        with self.assertRaises(ValueError):
            self.r.store.read_source(self.ref)


if __name__ == '__main__':
    unittest.main()

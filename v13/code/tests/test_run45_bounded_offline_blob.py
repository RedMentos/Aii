"""Run45 isolated descriptor-bounded offline blob reader regression (software only)."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run44_b2_shadow_readonly_cli as offline


class DescriptorBoundedBlobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plain = self.root / 'plain'
        self.plain.write_bytes(b'fixed-source')

    def test_regular_bytes_without_unbounded_path_read(self):
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded pathname read')):
            self.assertEqual(offline._read_bounded_regular_file(self.plain), b'fixed-source')

    def test_oversized_sparse_file_rejected_without_read(self):
        with (self.root / 'oversized').open('wb') as f:
            f.truncate(offline.MAX_BLOB + 1)
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded pathname read')):
            with self.assertRaisesRegex(ValueError, 'RUN44_BLOB_CAP'):
                offline._read_bounded_regular_file(self.root / 'oversized')

    def test_symlink_is_never_followed(self):
        (self.root / 'link').symlink_to(self.plain)
        with self.assertRaisesRegex(ValueError, 'RUN44_BLOB_FILE_UNSAFE'):
            offline._read_bounded_regular_file(self.root / 'link')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX')
    def test_fifo_refused_without_blocking(self):
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'RUN44_BLOB_FILE_UNSAFE'):
            offline._read_bounded_regular_file(fifo)

    def test_packed_blob_descriptor_path_does_not_call_path_read_bytes(self):
        import hashlib
        import sqlite3
        import zlib
        text = 'Project Orion. Binding rules: Budget 160 euros.'
        data = text.encode('utf-8')
        digest = hashlib.sha256(data).hexdigest()
        (self.root / 'data/blobs').mkdir(parents=True)
        (self.root / 'data/blobs' / (digest + '.z')).write_bytes(zlib.compress(data))
        view = object.__new__(offline.OfflineView)
        view.home = self.root
        view.db = sqlite3.connect(':memory:')
        self.addCleanup(view.db.close)
        view.db.row_factory = sqlite3.Row
        view.db.execute('CREATE TABLE sources(id TEXT,hash TEXT,deleted INTEGER)')
        view.db.execute('INSERT INTO sources VALUES(?,?,0)', ('src_demo', digest))
        ref = dict(source_id='src_demo', sha256=digest, char_start=0, char_end=len(text), modality='text')
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded pathname read')):
            self.assertEqual(view.read_source(ref), text)


if __name__ == '__main__':
    unittest.main()

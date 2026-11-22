"""Phone bootstrap tar extraction: real production entry and failure/retry paths."""
import io
from pathlib import Path
import os
from unittest.mock import patch
import tarfile
import tempfile
import unittest

from v13.safe_tar import extract
from v13.bootstrap import extract as bootstrap_extract


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as out:
        for name, kind, data in entries:
            m = tarfile.TarInfo(name)
            if kind == 'dir':
                m.type = tarfile.DIRTYPE
                out.addfile(m)
            elif kind == 'link':
                m.type = tarfile.SYMTYPE
                m.linkname = data
                out.addfile(m)
            elif kind == 'hardlink':
                m.type = tarfile.LNKTYPE
                m.linkname = data
                out.addfile(m)
            else:
                data = data.encode()
                m.size = len(data)
                out.addfile(m, io.BytesIO(data))


class PhoneBootstrapSafeTar(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / 'dest'
        self.tar = self.root / 'bundle.tar.gz'

    def test_real_bootstrap_uses_safe_extractor(self):
        self.assertIs(bootstrap_extract, extract)

    def test_good_and_retry_replaces_old_tree(self):
        archive(self.tar, [('./', 'dir', ''), ('pkg', 'dir', ''),
                           ('pkg/a', 'file', 'v1'), ('pkg/b', 'link', 'a')])
        bootstrap_extract(self.tar, self.dest)
        self.assertEqual((self.dest / 'pkg/b').read_text(), 'v1')
        (self.dest / 'stale').write_text('old')
        archive(self.tar, [('pkg/a', 'file', 'v2')])
        bootstrap_extract(self.tar, self.dest)
        self.assertEqual((self.dest / 'pkg/a').read_text(), 'v2')
        self.assertFalse((self.dest / 'stale').exists())

    def test_unsafe_path_preserves_old_tree(self):
        self.dest.mkdir()
        (self.dest / 'original').write_text('old')
        archive(self.tar, [('../escape', 'file', 'bad')])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertFalse((self.root / 'escape').exists())
        self.assertEqual((self.dest / 'original').read_text(), 'old')

    def test_symlink_member_cannot_have_child(self):
        archive(self.tar, [('pkg', 'dir', ''), ('pkg/alias', 'link', '.'),
                           ('pkg/alias/payload', 'file', 'bad')])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertFalse(self.dest.exists())

    def test_rejects_symlink_escape_and_hardlinks(self):
        for entries in ([('link', 'link', '../escape')],
                        [('a', 'file', 'ok'), ('b', 'hardlink', 'a')]):
            archive(self.tar, entries)
            with self.assertRaises(ValueError):
                bootstrap_extract(self.tar, self.dest)
            self.assertFalse(self.dest.exists())

    def test_rejects_duplicate_normalized_names(self):
        archive(self.tar, [('pkg/a', 'file', '1'), ('./pkg/a', 'file', '2')])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertFalse(self.dest.exists())

    def test_rejects_existing_destination_symlink(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.dest.symlink_to(outside, target_is_directory=True)
        archive(self.tar, [('new', 'file', 'bad')])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertFalse((outside / 'new').exists())

    def test_empty_archive_preserves_original(self):
        self.dest.mkdir()
        (self.dest / 'original').write_text('old')
        archive(self.tar, [])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertEqual((self.dest / 'original').read_text(), 'old')

    def test_failed_promotion_restores_original(self):
        self.dest.mkdir()
        (self.dest / 'original').write_text('old')
        archive(self.tar, [('new', 'file', 'v2')])
        real_replace = os.replace

        def fail_stage(src, dst):
            if Path(src).name == 'tree' and Path(dst) == self.dest:
                raise OSError('injected promote failure')
            return real_replace(src, dst)

        with patch('v13.safe_tar.os.replace', side_effect=fail_stage):
            with self.assertRaises(OSError):
                bootstrap_extract(self.tar, self.dest)
        self.assertEqual((self.dest / 'original').read_text(), 'old')
        self.assertFalse((self.dest / 'new').exists())
        self.assertEqual(list(self.root.glob('.dest.extract-*')), [])

    def test_symlink_cycle_rejected(self):
        archive(self.tar, [('a', 'link', 'b'), ('b', 'link', 'a')])
        with self.assertRaises(ValueError):
            bootstrap_extract(self.tar, self.dest)
        self.assertFalse(self.dest.exists())

    def test_file_directory_conflict_preserves_original(self):
        self.dest.mkdir()
        (self.dest / 'original').write_text('old')
        archive(self.tar, [('a', 'file', 'x'), ('a/b', 'file', 'y')])
        with self.assertRaises((ValueError, OSError)):
            bootstrap_extract(self.tar, self.dest)
        self.assertEqual((self.dest / 'original').read_text(), 'old')


if __name__ == '__main__':
    unittest.main()

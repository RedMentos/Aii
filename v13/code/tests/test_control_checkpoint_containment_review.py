"""WP-T14 control parameter accounting must never escape home/checkpoints."""
import tempfile
import unittest
from pathlib import Path
from v13 import control_budget as cb


class _Generation:
    def __init__(self, paths):
        self.paths = paths

    def generation(self):
        return {'components': {'candidate_paths': self.paths}}


class CheckpointContainmentReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.cp = self.home / 'checkpoints'
        self.cp.mkdir(parents=True)
        (self.home / 'models').mkdir()
        self.valid = self.cp / 'valid.npz'
        self.valid.write_bytes(b'valid')
        self.outside = self.home / 'outside.npz'
        self.outside.write_bytes(b'outside')
        self.external = self.root / 'external.npz'
        self.external.write_bytes(b'external')

    def test_only_real_contained_checkpoint_counts(self):
        store = _Generation([
            'checkpoints/valid.npz', str(self.valid),
            str(self.external), 'checkpoints/../outside.npz',
            str(self.home / 'models' / 'body.gguf'),
        ])
        (self.home / 'models' / 'body.gguf').write_bytes(b'model')
        out = cb.checkpoints(store, self.home)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['path'], 'checkpoints/valid.npz')
        self.assertEqual(out[0]['bytes'], 5)
        self.assertNotIn(str(self.external), repr(out))
        self.assertNotIn('outside.npz', repr(out))

    def test_symlink_and_intermediate_symlink_escape_rejected(self):
        link = self.cp / 'alias.npz'
        link.symlink_to(self.external)
        extdir = self.root / 'external-dir'
        extdir.mkdir()
        (extdir / 'child.npz').write_bytes(b'child')
        (self.cp / 'linked').symlink_to(extdir, target_is_directory=True)
        store = _Generation([
            str(link), 'checkpoints/linked/child.npz',
            'checkpoints/valid.npz',
        ])
        out = cb.checkpoints(store, self.home)
        self.assertEqual([x['path'] for x in out], ['checkpoints/valid.npz'])

    def test_missing_checkpoint_root_does_not_count_external(self):
        self.valid.unlink()
        self.cp.rmdir()
        out = cb.checkpoints(_Generation([str(self.external)]), self.home)
        self.assertEqual(out, [])


if __name__ == '__main__':
    unittest.main()

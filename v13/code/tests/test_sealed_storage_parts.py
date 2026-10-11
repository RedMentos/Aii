import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('sealed_parts', Path(__file__).resolve().parents[1] / 'scripts/sealed_storage_parts.py')
parts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parts)


class SealedStoragePartsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'closed.bin'
        self.source.write_bytes(bytes(range(256)) * 9000)
        self.folder = self.root / 'parts'
        self.doc = parts.split(self.source, self.folder)
        self.manifest = self.folder / 'manifest.json'
        self.out = self.root / 'restored.bin'

    def test_round_trip_and_idempotent_replay(self):
        self.assertEqual(len(self.doc['parts']), 3)
        parts.restore(self.manifest, self.out)
        self.assertEqual(self.source.read_bytes(), self.out.read_bytes())
        self.assertEqual(parts.split(self.source, self.folder), self.doc)
        parts.restore(self.manifest, self.out)

    def test_corrupt_part_never_installs_or_leaves_partial(self):
        p = self.folder / 'part-00001.bin'
        p.write_bytes(b'x' + p.read_bytes()[1:])
        with self.assertRaises(ValueError): parts.restore(self.manifest, self.out)
        self.assertFalse(self.out.exists())
        self.assertEqual(set(p.name for p in self.root.iterdir()), {'closed.bin', 'parts'})

    def test_wrong_final_hash_never_installs(self):
        self.doc['sha256'] = '0' * 64
        self.manifest.write_text(json.dumps(self.doc))
        with self.assertRaises(ValueError): parts.restore(self.manifest, self.out)
        self.assertFalse(self.out.exists())

    def test_invalid_order_and_traversal_rejected(self):
        for name in ['../closed.bin', '/tmp/closed.bin', 'part-00002.bin']:
            self.doc['parts'][0]['name'] = name
            self.manifest.write_text(json.dumps(self.doc))
            with self.assertRaises(ValueError): parts.restore(self.manifest, self.out)

    def test_different_existing_evidence_not_overwritten(self):
        self.out.write_bytes(b'previous closed artifact')
        with self.assertRaises(ValueError): parts.restore(self.manifest, self.out)
        self.assertEqual(self.out.read_bytes(), b'previous closed artifact')
        self.source.write_bytes(b'different')
        with self.assertRaises(ValueError): parts.split(self.source, self.folder)

    def test_symlink_part_rejected(self):
        p = self.folder / 'part-00000.bin'
        saved = self.root / 'external.bin'; saved.write_bytes(p.read_bytes())
        p.unlink(); p.symlink_to(saved)
        with self.assertRaises(ValueError): parts.restore(self.manifest, self.out)

    def test_empty_closed_artifact_supported(self):
        source = self.root / 'empty'; source.write_bytes(b'')
        folder = self.root / 'empty-parts'; parts.split(source, folder)
        out = self.root / 'empty-restored'; parts.restore(folder / 'manifest.json', out)
        self.assertEqual(out.read_bytes(), b'')

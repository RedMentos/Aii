"""Fail-closed bounded file IO for explicit/offline World-JEPA SHADOW probe.

RED before source fix: the old loaders call Path.read_bytes on caller-controlled
oversized inputs, allocating the whole file before enforcing documented caps.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.world_jepa_shadow_probe import (
    _json_file, MAX_REQUEST_BYTES, MAX_PROVENANCE_BYTES,
)
from v13.world_jepa_slots import SlotWorldJEPA, MAX_CHECKPOINT_BYTES


PROVENANCE = {'cohort_sha256': 'e' * 64, 'source_sha256': 'f' * 64}


class BoundedProbeFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def sparse(self, name, length):
        path = self.root / name
        with path.open('wb') as handle:
            handle.truncate(length)
        return path

    def test_oversized_observation_never_uses_unbounded_read_bytes(self):
        path = self.sparse('observation.json', MAX_REQUEST_BYTES + 1)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read_bytes')):
            with self.assertRaises(ValueError):
                _json_file(path, MAX_REQUEST_BYTES)

    def test_oversized_provenance_never_uses_unbounded_read_bytes(self):
        path = self.sparse('provenance.json', MAX_PROVENANCE_BYTES + 1)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read_bytes')):
            with self.assertRaises(ValueError):
                _json_file(path, MAX_PROVENANCE_BYTES)

    def test_oversized_checkpoint_never_uses_unbounded_read_bytes(self):
        path = self.sparse('checkpoint.npz', MAX_CHECKPOINT_BYTES + 1)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read_bytes')):
            with self.assertRaises(ValueError):
                SlotWorldJEPA.load(path, expected_provenance=PROVENANCE,
                                   expected_sha256='0' * 64)

    def test_small_valid_json_keeps_exact_decoding(self):
        path = self.root / 'ok.json'
        value = {'before': [[1, 2]], 'actions': [[0, 1]]}
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(_json_file(path, MAX_REQUEST_BYTES), value)

    def test_small_malformed_checkpoint_still_fails_closed(self):
        path = self.root / 'broken.npz'
        raw = b'not a zip archive' * 9
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
            SlotWorldJEPA.load(path, expected_provenance=PROVENANCE,
                               expected_sha256=hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()

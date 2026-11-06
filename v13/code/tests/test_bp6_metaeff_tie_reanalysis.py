import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bp6_metaeff_tie_reanalysis as reanalysis


class SourceBinding(unittest.TestCase):
    def test_legacy_replay_preserves_the_known_tie_artifact(self):
        pairs = [(0.5, 1)] * 50 + [(0.5, 0)] * 50
        self.assertAlmostEqual(reanalysis.legacy_meta_i(pairs), 0.8)
        self.assertEqual(reanalysis.metaeff.meta_i(pairs), 0.0)

    def test_reanalysis_rejects_modified_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            original = b'{"answer": 1}'
            expected = hashlib.sha256(original).hexdigest()
            path.write_bytes(original)
            self.assertEqual(reanalysis.load_json(path, expected)[0], {'answer': 1})
            path.write_bytes(b'{"answer": 2}')
            with self.assertRaisesRegex(ValueError, 'unexpected source hash'):
                reanalysis.load_json(path, expected)


if __name__ == '__main__':
    unittest.main()

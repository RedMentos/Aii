"""Round-4 tap-arm export swaps only the native array; explicit test data, no native tool runs."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_objective as aj
import action_jepa_round3 as r3
import action_jepa_round4 as r4
import tests.test_action_jepa_round3 as round3_tests


class Round4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.args3 = round3_tests.Round3Tests().fixture(self.root)
        r3.export(self.args3)
        with np.load(self.args3.taps) as z:
            self.texts = z['texts'].tolist()
        self.arm = self.root / 'arm.npz'
        np.savez(self.arm, x=np.random.default_rng(9).normal(size=(len(self.texts), 1024)), texts=np.asarray(self.texts))
        (self.root / 'capture-report.json').write_text('{"test_fixture": true}')

    def args(self, out='r4'):
        return argparse.Namespace(round3_export=self.args3.out, taps=self.arm, arm='l11_last',
                                  capture_report=self.root / 'capture-report.json', out=self.root / out)

    def test_rows_unchanged_and_new_array_bound(self):
        r4.export(self.args())
        new = json.loads((self.root / 'r4/dataset.json').read_text())
        old = json.loads((self.args3.out / 'dataset.json').read_text())
        self.assertEqual(new['rows'], old['rows'])
        doc, x, *_ = aj.load_dataset(self.root / 'r4/dataset.json')
        with np.load(self.arm) as z:
            raw = z['x'][doc['rows'][0]['context_artifact_index']]
        np.testing.assert_allclose(x[0], raw / np.sqrt(np.mean(raw * raw)))

    def test_reordered_texts_are_rejected(self):
        np.savez(self.arm, x=np.zeros((len(self.texts), 1024)) + 1, texts=np.asarray(self.texts[::-1]))
        with self.assertRaisesRegex(ValueError, 'texts/shape'):
            r4.export(self.args())


if __name__ == '__main__':
    unittest.main()

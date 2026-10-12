"""Round-5 tool world: real calc transactions in a sandbox store; taps are explicit test data."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_objective as aj
import action_jepa_round5_tools as r5


class Round5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = r5.world(argparse.Namespace(out=self.root / 'world', states=40, seed=5))

    def test_outcomes_come_from_executed_tool_transactions(self):
        w = json.loads((self.root / 'world/world.json').read_text())
        e = w['episodes'][0]
        tx = json.loads((self.root / 'world' / e['tx']['quarter']['path']).read_text())
        self.assertEqual(tx['status'], 'EXECUTED')
        self.assertEqual(tx['tool'], 'calc')
        self.assertEqual(e['outcomes']['quarter'], r5.TEMPLATE.format(n=tx['result']))
        self.assertEqual(tx['result'], e['value'] / 4 if e['value'] % 4 else e['value'] // 4)
        self.assertEqual(sum(self.report['partitions'].values()), 40)

    def test_export_is_partition_disjoint_and_binds_transactions(self):
        texts = json.loads((self.root / 'world/texts.json').read_text())
        np.savez(self.root / 'taps.npz', x=np.random.default_rng(1).normal(size=(len(texts), 1024)), texts=np.asarray(texts))
        (self.root / 'cap.json').write_text('{"test_fixture": true}')
        out = r5.export(argparse.Namespace(world=self.root / 'world', taps=self.root / 'taps.npz',
                                           capture_report=self.root / 'cap.json', arm='fixture', out=self.root / 'exp'))
        doc, *_ = aj.load_dataset(self.root / 'exp/dataset.json')
        self.assertTrue(all(any(s.startswith('tx-') for s in r['source_ids']) for r in doc['rows']))
        self.assertEqual(out['pairs'], 4 * (40 - out['dropped']))
        (self.root / 'world/tx' / next(iter(sorted((self.root / 'world/tx').iterdir()))).name).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'transaction record changed'):
            r5.export(argparse.Namespace(world=self.root / 'world', taps=self.root / 'taps.npz',
                                         capture_report=self.root / 'cap.json', arm='fixture', out=self.root / 'exp2'))


if __name__ == '__main__':
    unittest.main()

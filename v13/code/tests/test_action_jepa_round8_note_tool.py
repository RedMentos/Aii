"""Round-8 note-tool world on a small sandbox; taps are an explicit synthetic array."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_round8_note_tool as r8
import action_jepa_objective as aj


class Round8NoteToolTests(unittest.TestCase):
    def test_world_uses_approved_writes_and_registry_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = type('A', (), {'out': str(root / 'w'), 'states': 20, 'seed': 3})
            report = r8.world(args)
            self.assertEqual(report['counts'], {'proposed': 160, 'approved_executed': 160, 'undone': 20})
            doc = json.loads((root / 'w/world.json').read_text())
            e = doc['episodes'][0]
            self.assertEqual(e['outcomes']['undo'], 'After undo, the note reads: ' + e['content'])
            self.assertEqual(e['outcomes']['uppercase'], 'After uppercasing, the note reads: ' + e['content'].upper())
            action = json.loads((root / 'w' / e['tx']['append_done'][1]['path']).read_text())
            self.assertEqual((action['status'], action['reason'], action['risk']), ('EXECUTED', 'USER_APPROVED', 'WRITE_LOCAL'))
            self.assertEqual(len(e['tx']['undo']), 3)
            self.assertEqual(len(set(r8.contents())), 600)

    def test_export_binds_every_transaction_and_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r8.world(type('A', (), {'out': str(root / 'w'), 'states': 40, 'seed': 5}))
            texts = json.loads((root / 'w/texts.json').read_text())
            taps = root / 'taps.npz'
            np.savez(taps, x=np.random.default_rng(1).normal(size=(len(texts), 1024)), texts=np.asarray(texts))
            (root / 'cap.json').write_text('{}')
            out = r8.export(type('A', (), {'world': str(root / 'w'), 'taps': str(taps), 'capture_report': str(root / 'cap.json'),
                                          'arm': 'synthetic', 'out': str(root / 'x')}))
            self.assertEqual(out['pairs'], 160)
            doc, x, y, a, actions, masks = aj.load_dataset(root / 'x/dataset.json')
            self.assertEqual(sorted(actions), sorted(r8.ACTIONS))
            undo_row = next(r for r in doc['rows'] if r['action'] == 'undo')
            self.assertEqual(len(undo_row['source_ids']), 5)
            texts[0] = 'changed'
            np.savez(taps, x=np.zeros((len(texts), 1024)), texts=np.asarray(texts))
            with self.assertRaisesRegex(ValueError, 'Tap texts differ'):
                r8.export(type('A', (), {'world': str(root / 'w'), 'taps': str(taps), 'capture_report': str(root / 'cap.json'),
                                        'arm': 'synthetic', 'out': str(root / 'y')}))


if __name__ == '__main__':
    unittest.main()

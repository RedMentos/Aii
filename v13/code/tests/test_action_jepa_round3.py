"""Round-3 fresh-topic export on explicit test data; no native server starts."""
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
import export_action_jepa_dataset as ex
import tests.test_action_jepa_export as export_tests


class Round3Tests(unittest.TestCase):
    def test_sentence_parser_strips_numbering_and_filters(self):
        text = '1. Bees make honey.\n- Bees make honey!\nToo short.\n2) The hive is warm in winter.\nNo end mark here'
        self.assertEqual(r3.parse_sentences(text), ['Bees make honey.', 'The hive is warm in winter.'])

    def fixture(self, root, leak=False):
        sp, ap, pp, *_ = export_tests.ExportTests().fixture(root)
        fresh = {'fresh topic a': ['TEST fresh a %d' % i for i in range(3)],
                 'fresh topic b': ['TEST fresh b %d' % i for i in range(3)]}
        acts = {s: {a: 'TEST fresh out %s %s' % (a, s) for a in ex.ACTIONS} for v in fresh.values() for s in v}
        plan = json.loads(pp.read_text())
        if leak:  # one fresh outcome equals an old training-side input
            train_index = next(e['original_index'] for e in plan['kept_episodes'] if e['partition'] == 'train')
            _, rows, _ = ex.corpus(sp, ap)
            acts['TEST fresh a 0']['negate'] = rows[train_index]['input'].upper()
        fsp, fap = root / 'fresh-sentences.json', root / 'fresh-actions.json'
        fsp.write_text(json.dumps(fresh))
        fap.write_text(json.dumps(acts))
        args = argparse.Namespace(old_sentences=sp, old_actions=ap, fresh_sentences=fsp, fresh_actions=fap,
                                  old_plan=pp, out=root / 'export')
        old, new = r3.all_texts(args)
        texts = old + new
        np.savez(root / 'taps.npz', x=np.random.default_rng(3).normal(size=(len(texts), 1024)), texts=np.asarray(texts))
        (root / 'registration.json').write_text('{"test_fixture": true}')
        args.taps, args.registration = root / 'taps.npz', root / 'registration.json'
        return args

    def test_export_uses_only_fresh_topics_for_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.fixture(Path(tmp))
            receipt = r3.export(args)
            doc, *_ = aj.load_dataset(args.out / 'dataset.json')
            tests = {r['topic'] for r in doc['rows'] if r['partition'] == 'test'}
            self.assertEqual(tests, {'fresh topic a', 'fresh topic b'})
            self.assertEqual(receipt['episodes']['test'], 6)
            plan = json.loads(args.old_plan.read_text())
            old_test = set(plan['new_topics']['test'])
            self.assertFalse(old_test & {r['topic'] for r in doc['rows']})

    def test_fresh_episode_sharing_training_text_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.fixture(Path(tmp), leak=True)
            receipt = r3.export(args)
            self.assertEqual(receipt['excluded_fresh'], 1)
            self.assertEqual(receipt['episodes']['test'], 5)

    def test_changed_capture_texts_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.fixture(Path(tmp))
            with np.load(args.taps) as z:
                x, texts = z['x'], z['texts'].tolist()
            texts[-1] = 'changed'
            np.savez(args.taps, x=x, texts=np.asarray(texts))
            with self.assertRaisesRegex(ValueError, 'Capture texts'):
                r3.export(args)


if __name__ == '__main__':
    unittest.main()

"""Offline source-disjoint native export checks; all generated taps are test data."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import export_action_jepa_dataset as ex
import action_jepa_objective as aj


class ExportTests(unittest.TestCase):
    def fixture(self, root):
        sentences = {f'topic{i}': [f'TEST input {i}:{j}' for j in range(3)] for i in range(16)}
        actions = {s: {a: 'TEST output ' + a + ' ' + s for a in ex.ACTIONS} for ss in sentences.values() for s in ss}
        sp, ap = root / 'sentences.json', root / 'actions.json'
        sp.write_text(json.dumps(sentences))
        ap.write_text(json.dumps(actions))
        plan = ex.build_plan(sp, ap)
        pp = root / 'plan.json'
        pp.write_text(json.dumps(plan))
        _, rows, texts = ex.corpus(sp, ap)
        raw = np.random.default_rng(2).normal(size=(len(texts), 1024))
        np.savez(root/'taps.npz', x=raw, texts=np.asarray(texts))
        runner = root / 'bin/runner'
        runner.parent.mkdir()
        runner.write_bytes(b'TEST static runner')
        model = root / 'model.gguf'
        model.write_bytes(b'TEST gguf')
        # The real extractor source is bound, but no native extractor is called.
        extractor = Path(ex.__file__).with_name('jepa_ablation_bench.py').resolve()
        manifest = {'schema': ex.CAPTURE_SCHEMA, 'native_extraction_observed': True,
                    'tap_kind': 'llama.cpp-mean-last-layer-embedding',
                    'plan_sha256': ex.sha(pp), 'texts_sha256': plan['texts_sha256'],
                    'taps_sha256': ex.sha(root/'taps.npz'), 'shape': list(raw.shape), 'dtype': str(raw.dtype),
                    'artifacts': {'model_gguf': {'path': str(model), 'sha256': ex.sha(model)},
                                  'runner': {'path': str(runner), 'sha256': ex.sha(runner)},
                                  'extractor': {'path': str(extractor), 'sha256': ex.sha(extractor)}},
                    'runtime_libraries': {}}
        mp = root / 'capture.json'
        mp.write_text(json.dumps(manifest))
        return sp, ap, pp, root/'taps.npz', mp, raw, texts

    def export(self, root, args):
        return ex.export_dataset(args[2], args[0], args[1], args[3], args[4], root/'export')

    def test_plan_preserves_old_test_and_unseen_new_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sp, ap, pp, *_ = self.fixture(root)
            plan = json.loads(pp.read_text())
            self.assertEqual(plan['new_topics']['test'], plan['legacy_topics']['test'])
            new_train = sum([plan['new_topics'][p] for p in ('train', 'calibration', 'retention')], [])
            self.assertEqual(set(new_train), set(plan['legacy_topics']['train']))
            self.assertEqual(len(new_train), len(set(new_train)))
            self.assertFalse(plan['fresh_held_out_data'])
            self.assertEqual(plan, ex.build_plan(sp, ap))

    def test_export_matches_native_array_and_detects_changed_state_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.fixture(root)
            receipt = self.export(root, args)
            self.assertEqual(receipt['pairs'], 16*3*4)
            dataset = root/'export/dataset.json'
            doc, x, *_ = aj.load_dataset(dataset)
            i = doc['rows'][0]['context_artifact_index']
            np.testing.assert_array_equal(x[0], args[5][i]/np.sqrt(np.mean(args[5][i]**2)))
            row = doc['rows'][0]
            row['context_state'] = x[0].tolist()
            raw_y = args[5][row['future_artifact_index']]
            row['future_state'] = (raw_y/np.sqrt(np.mean(raw_y**2))).tolist()
            row['context_state'][0] += 1
            dataset.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'bound native tap rows'):
                aj.load_dataset(dataset)

    def test_no_manifest_missing_taps_never_exports_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.fixture(root)
            args[3].unlink()
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                self.export(root, args)
            self.assertFalse((root/'export').exists())

    def test_actual_tap_must_bind_matching_text_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.fixture(root)
            self.export(root, args)
            dataset = root/'export/dataset.json'
            doc = json.loads(dataset.read_text())
            doc['rows'][0]['source_ids'] = [doc['rows'][0]['source_ids'][1]]
            dataset.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'exact input/output source'):
                aj.load_dataset(dataset)

    def test_text_order_or_library_change_blocks_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.fixture(root)
            manifest = json.loads(args[4].read_text())
            np.savez(args[3], x=args[5], texts=np.asarray(list(reversed(args[6]))))
            manifest['taps_sha256'] = ex.sha(args[3])
            args[4].write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'text order'):
                self.export(root, args)
            (root/'bin/libggml.so').write_bytes(b'New previously unbound library')
            with self.assertRaisesRegex(ValueError, 'shared-library inventory'):
                self.export(root, args)

    def test_declared_plan_cannot_change_after_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.fixture(root)
            changed = json.loads(args[2].read_text())
            changed['kept_episodes'][0]['partition'] = 'test'
            args[2].write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'Preregistered plan'):
                self.export(root, args)

    def test_cross_partition_output_collisions_dropped_before_taps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sp, ap, pp, *_ = self.fixture(root)
            plan = json.loads(pp.read_text())
            s = json.loads(sp.read_text())
            a = json.loads(ap.read_text())
            train_sentence = s[plan['new_topics']['train'][0]][0]
            test_sentence = s[plan['new_topics']['test'][0]][0]
            a[train_sentence]['negate'] = 'Shared TEST outcome'
            a[test_sentence]['negate'] = ' shared   test OUTCOME '
            ap.write_text(json.dumps(a))
            new = ex.build_plan(sp, ap)
            self.assertEqual(len(new['excluded_episodes']), 2)
            self.assertTrue(all(r['reason'] == 'cross_partition_source_text' for r in new['excluded_episodes']))


if __name__ == '__main__':
    unittest.main()

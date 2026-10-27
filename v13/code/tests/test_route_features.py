import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from v13 import route_features as RF
from v13.learning_worker import features, objective, gradient_check, train


class RouteFeaturesTest(unittest.TestCase):
    def test_lexical_is_deterministic_bounded_and_ignores_numbers(self):
        a = RF.lexical(['Wie viel ist die Hälfte von 120 Euro?'])
        b = RF.lexical(['Wie viel ist die Hälfte von 48 Euro?'])
        self.assertTrue(np.array_equal(a, b))
        self.assertAlmostEqual(float(np.linalg.norm(a)), RF.LEX_SCALE)
        self.assertEqual(RF.lexical(['']).tolist(), [[0.] * RF.LEX_DIM])
        self.assertFalse(np.array_equal(a, RF.lexical(['Rechne bitte 12 mal 3 aus.'])))

    def test_zero_extended_head_keeps_logits(self):
        rng = np.random.default_rng(1); base = features(rng.normal(size=(3, 6)))
        w = rng.normal(size=(7, 4)); tr = np.ones(7)
        w2, tr2 = RF.extend(w, tr, 7 + RF.LEX_DIM)
        x2 = RF.for_head(base, ['a b', 'Hälfte von', 'Kern'], w2.shape[0])
        self.assertTrue(np.allclose(base @ w, x2 @ w2)); self.assertEqual(tr2.shape, (7 + RF.LEX_DIM,))
        with self.assertRaises(ValueError): RF.for_head(base, ['x'] * 3, 9)

    def test_recency_weights(self):
        self.assertEqual(RF.recency_weights(4, 0).tolist(), [1.] * 4)
        w = RF.recency_weights(10, 2)
        self.assertAlmostEqual(float(w.mean()), 1.); self.assertTrue(np.all(np.diff(w) > 0))
        self.assertAlmostEqual(float(w[-1] / w[-3]), 2.)

    def test_weighted_objective_gradient(self):
        rng = np.random.default_rng(2); x = features(rng.normal(size=(9, 5))); y = rng.integers(0, 4, 9)
        w = rng.normal(size=(6, 4)) * .1; sw = RF.recency_weights(9, 3)
        self.assertLess(gradient_check(x, y, w, sw), 1e-6)
        self.assertAlmostEqual(objective(x, y, w, np.ones(9))[0], objective(x, y, w)[0])

    def test_word_channel_learns_a_boundary_the_embedding_cannot_see(self):
        # identical embeddings for "half" and "third" questions: only the words differ
        texts, labels = [], []
        for i in range(10):
            texts += ['Was ist die Hälfte von %d?' % i, 'Was ist ein Drittel von %d?' % i, 'Hallo Anna %d' % i, 'Vergleiche Bus und Bahn %d' % i]
            labels += [0, 1, 0, 3]
        emb = [[1., 0., 0.] if lab in (0, 1) and 'Hallo' not in t else ([0., 1., 0.] if 'Hallo' in t else [0., 0., 1.]) for t, lab in zip(texts, labels)]
        texts += ['Fasse zusammen: Kern %d' % i for i in range(4)]; labels += [2] * 4; emb += [[0., .5, .5]] * 4
        cfg = {'learning_steps': 400, 'eligibility_decay': .95, 'learning_rate': .5, 'max_update_norm': 1., 'retention_max_delta': .02, 'route_recency_half_life': 0}
        with tempfile.TemporaryDirectory() as d:
            m0 = train({'config': cfg, 'embeddings': emb, 'labels': labels, 'scaffold_labels': [0] * len(labels)}, d)
            m1 = train({'config': cfg, 'embeddings': emb, 'labels': labels, 'scaffold_labels': [0] * len(labels), 'texts': texts}, d)
            self.assertEqual(m1['feature_view'], 'needle+words'); self.assertEqual(m0['feature_view'], 'needle')
            self.assertGreater(m1['held_out']['accuracy'], m0['held_out']['accuracy'])
            self.assertTrue(m1['gradient_check']); self.assertTrue(m1['deterministic_repeat'])
            with np.load(Path(d) / 'candidate.npz') as z: self.assertEqual(z['route_w'].shape, (4 + RF.LEX_DIM, 4))

    def test_cv_gate_adopts_a_changed_preference_without_scope_words(self):
        # old: "half" questions labelled 1 (detail); newer evidence: label 0 (simple). Embeddings identical for all arithmetic.
        texts, labels, emb = [], [], []
        def add(t, lab, e): texts.append(t); labels.append(lab); emb.append(e)
        for i in range(8):
            add('Was ist die Hälfte von %d?' % i, 1, [1., 0., 0.]); add('Rechne %d mal 3 aus.' % i, 1, [1., 0., 0.])
            add('Hallo Anna %d' % i, 0, [0., 1., 0.]); add('Vergleiche Bus und Bahn %d' % i, 3, [0., 0., 1.]); add('Fasse zusammen: Kern %d' % i, 2, [0., .5, .5])
        cfg = {'learning_steps': 300, 'eligibility_decay': .95, 'learning_rate': .5, 'max_update_norm': 1., 'retention_max_delta': .02, 'route_recency_half_life': 8, 'route_gate_folds': 4}
        with tempfile.TemporaryDirectory() as d:
            train({'config': cfg, 'embeddings': emb, 'labels': labels, 'scaffold_labels': [0] * len(labels), 'texts': texts}, d)
            parent = Path(d) / 'parent.npz'; (Path(d) / 'candidate.npz').rename(parent)
            for i in range(8):
                add('Wie viel ist die Hälfte von %d Euro?' % i, 0, [1., 0., 0.]); add('Rechne bitte %d mal 4 aus.' % i, 1, [1., 0., 0.])
            m = train({'config': cfg, 'embeddings': emb, 'labels': labels, 'scaffold_labels': [0] * len(labels), 'texts': texts, 'active_checkpoint': str(parent)}, d)
            self.assertEqual(m['held_out']['folds'], 4); self.assertTrue(m['gradient_check']); self.assertTrue(m['deterministic_repeat'])
            self.assertTrue(m['commit_eligible'], m['held_out'])
            for ov in (1, 2):
                m2 = train({'config': dict(cfg, route_gate_outvoted=ov), 'embeddings': emb, 'labels': labels, 'scaffold_labels': [0] * len(labels), 'texts': texts, 'active_checkpoint': str(parent)}, d)
                self.assertIn('outvoted', m2['held_out']); self.assertTrue(m2['gradient_check'])
            with np.load(Path(d) / 'candidate.npz') as z: w = z['route_w']
            x = RF.build(features([[1., 0., 0.], [1., 0., 0.]]), ['Wie viel ist die Hälfte von 70 Euro?', 'Rechne 7 mal 5 aus.'])
            self.assertEqual(np.argmax(x @ w, axis=1).tolist(), [0, 1])

    def test_cv_gate_with_too_few_corrections_is_not_eligible(self):
        cfg = {'learning_steps': 20, 'eligibility_decay': .95, 'learning_rate': .01, 'max_update_norm': .02, 'retention_max_delta': .02, 'route_recency_half_life': 16, 'route_gate_folds': 4}
        rng = np.random.default_rng(0)
        with tempfile.TemporaryDirectory() as d:
            m = train({'config': cfg, 'embeddings': rng.normal(size=(8, 5)).tolist(), 'labels': [0, 0, 1, 1, 2, 2, 3, 3], 'scaffold_labels': [0] * 8, 'texts': ['a b'] * 8}, d)
            self.assertFalse(m['commit_eligible']); self.assertEqual(m['held_out']['n'], 0)


if __name__ == '__main__':
    unittest.main()

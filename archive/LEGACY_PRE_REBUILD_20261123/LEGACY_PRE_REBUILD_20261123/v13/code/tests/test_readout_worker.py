import tempfile
import unittest
from pathlib import Path
import numpy as np

from v13.readout_worker import infer, partitions, train
from v13.store import telemetry_metrics


CFG = {
    'learning_steps': 200,
    'eligibility_decay': .9,
    'learning_rate': .1,
    'max_update_norm': .2,
    'retention_max_delta': .02,
}


def corpus(component, per_class=12):
    classes = 4 if component == 'wake' else 2
    embeddings, labels, hashes = [], [], []
    for k in range(classes):
        for j in range(per_class):
            # Separable deterministic fixture. This tests the readout mechanics,
            # never native semantic quality or a production calibration claim.
            v = np.zeros(classes + 2)
            v[k] = 1.
            v[-1] = .01 * (j + 1)
            embeddings.append(v.tolist())
            labels.append(k)
            hashes.append(f'{component}-{k}-{j}')
    return embeddings, labels, hashes


class ReadoutWorker(unittest.TestCase):
    def test_readout_telemetry_keeps_numeric_decision_metrics_but_drops_unknown_text(self):
        clean = telemetry_metrics({
            'component': 'wake', 'action': 'both', 'learned': True,
            'prediction': {'index': 3, 'probabilities': [.1, .1, .2, .6],
                           'confidence': .6, 'support_cosine': .8,
                           'support_floor': .7, 'in_support': True,
                           'temperature': 1., 'calibration_scope': 'held_out_bounded_readout'},
            'fallback_reason': 'APPROVED_BOUNDED_READOUT',
            'untrusted_text': 'must never enter diagnostic telemetry'})
        self.assertEqual(clean['component'], 'wake')
        self.assertEqual(clean['prediction']['confidence'], .6)
        self.assertNotIn('untrusted_text', clean)

    def test_partitions_are_disjoint_and_require_six_per_class(self):
        y = np.asarray([k for k in range(4) for _ in range(6)])
        train_i, cal_i, test_i = partitions(y, 4)
        self.assertFalse(set(train_i) & set(cal_i))
        self.assertFalse(set(train_i) & set(test_i))
        self.assertFalse(set(cal_i) & set(test_i))
        self.assertEqual(set(np.concatenate((train_i, cal_i, test_i))), set(range(len(y))))
        with self.assertRaises(ValueError):
            partitions(np.asarray([k for k in range(4) for _ in range(5)]), 4)

    def test_wake_candidate_is_reloadable_calibrated_and_support_gated(self):
        emb, labels, hashes = corpus('wake')
        # Deliberately weak scaffold: bounded fixture must improve held-out labels.
        request = {'component': 'wake', 'config': CFG, 'embeddings': emb,
                   'labels': labels, 'scaffold_labels': [0] * len(labels),
                   'context_hashes': hashes, 'active_checkpoint': None}
        with tempfile.TemporaryDirectory() as td:
            metrics = train(request, td)
            self.assertTrue(metrics['commit_eligible'])
            self.assertTrue(metrics['gradient_check'])
            self.assertTrue(metrics['deterministic_repeat'])
            self.assertTrue(metrics['checkpoint_reload'])
            self.assertTrue(metrics['calibration_pass'])
            self.assertEqual(metrics['body_parameters_modified'], 0)
            pred = infer(emb[17], Path(td) / 'candidate.npz')
            self.assertEqual(pred['index'], labels[17])
            self.assertTrue(pred['in_support'])
            # Orthogonal vector is outside all fitted support centres.
            ood = np.zeros(len(emb[0])); ood[-2] = 1.
            self.assertFalse(infer(ood.tolist(), Path(td) / 'candidate.npz')['in_support'])

    def test_duplicate_contexts_rejected_and_halt_never_promotes_cost_regression(self):
        emb, labels, hashes = corpus('halt')
        duplicate = list(hashes); duplicate[-1] = duplicate[0]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                train({'component': 'halt', 'config': CFG, 'embeddings': emb,
                       'labels': labels, 'scaffold_labels': [0] * len(labels),
                       'context_hashes': duplicate, 'active_checkpoint': None}, td)
        # A classifier can be accurate yet still fail promotion when it adds
        # re-entry cost versus the scaffold. This is an intentional halt gate.
        with tempfile.TemporaryDirectory() as td:
            metrics = train({'component': 'halt', 'config': CFG, 'embeddings': emb,
                             'labels': labels, 'scaffold_labels': [0] * len(labels),
                             'context_hashes': hashes, 'active_checkpoint': None}, td)
            self.assertEqual(metrics['held_out']['after']['accuracy'], 1.)
            self.assertEqual(metrics['missed_continue'], 0)
            self.assertGreater(metrics['cost_after'], metrics['cost_before'])
            self.assertFalse(metrics['bounded_label_cost_pareto'])
            self.assertFalse(metrics['commit_eligible'])


if __name__ == '__main__':
    unittest.main()

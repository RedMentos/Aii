"""WP-T10 neuromod comparisons through real SQLite/packet processing.

Software fixtures only: these are not paired retention outcomes or model/device utility proofs.
"""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13 import authority as AU
from v13 import neuromod as N
from v13.runtime import Runtime


class NeuromodLiveComparisons(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.n = N.Neuromod(self.r.store)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, 'software fixture')['event_id']

    def retention(self, event, label, path='weights'):
        self.r.store.add_packet('PlasticityState', N.packet(
            'PlasticityState', 'F7_PLASTICITY', event, self.r.store.generation_id, [],
            component=path, consolidation_ready=False, retention_pass=label,
            update_id='software-fixture', trials=1, plasticity_gain=1.,
            stability_score=.5, saturation=None, semantic_truth_authority=False))

    def train(self, count=N.META_MIN_N, label=True):
        for _ in range(count):
            event = self.event()
            self.n.touch('weights', event)
            self.retention(event, label)
        self.n.sync()

    def ledger(self):
        return self.r.store.state(AU.KEY, AU.empty())[0]['ledger']

    def test_minimum_training_requires_actual_snapshot_and_retention_label(self):
        self.n.touch('weights', self.event())
        self.assertIsNone(self.n.gate('weights')['meta']['learned_p_help'])
        self.retention(self.event(), True)
        self.n.sync()
        self.train(N.META_MIN_N - 2)
        self.assertEqual(self.n._load()[0]['meta_head']['n'], N.META_MIN_N - 1)
        self.assertIsNone(self.n.gate('weights')['meta']['learned_p_help'])
        self.assertEqual(self.ledger(), {})
        # A retention result without a fresh trace snapshot is not another training sample.
        self.retention(self.event(), False)
        self.n.sync()
        self.assertEqual(self.n._load()[0]['meta_head']['n'], N.META_MIN_N - 1)
        self.assertEqual(self.ledger(), {})

    def test_same_features_compare_actual_scalar_proposals_before_application(self):
        self.train()
        baseline = self.n.gate('weights', observe=False)
        head_before = self.n._load()[0]['meta_head']
        with patch('v13.authority.observe', wraps=AU.observe) as observed, \
                patch.object(self.r.pool, 'get', side_effect=AssertionError('extra model call')):
            gate = self.n.gate('weights')
        features = gate['meta']['features']
        score = sum(w * features[k] for w, k in zip(head_before['w'], N.META_FEATURES)) + head_before['b']
        probability = round(1 / (1 + math.exp(-score)), 6)
        self.assertEqual(gate['meta']['learned_p_help'], probability)
        self.assertEqual(gate['meta']['rule_p'], N.Neuromod.meta_rule(features))
        self.assertEqual(gate['meta']['p_applied'], round(N.clamp(gate['meta']['rule_p'] * (.5 + probability)), 6))
        self.assertNotEqual(gate['meta']['rule_p'], gate['meta']['p_applied'])
        observed.assert_called_once_with(self.r.store, 'neuromod_meta', gate['meta']['rule_p'], gate['meta']['p_applied'])
        self.assertEqual(gate['factor'], baseline['factor'])  # SHADOW still uses its existing budget.
        self.assertEqual(gate['meta']['mode'], 'SHADOW')
        self.assertEqual(gate['native_parameter_authority'], 0)
        self.assertEqual(self.n._load()[0]['meta_head'], head_before)
        self.assertEqual(self.ledger()['neuromod_meta'], {
            'n': 1, 'same': 0, 'n_out': 0, 'scaffold_fail': 0, 'learned_fail': 0})

    def test_diagnostic_reports_and_repeated_gate_polling_do_not_inflate_evidence(self):
        self.train()
        for _ in range(AU.MIN_N):
            self.n.report('weights')
            self.n.report()
        self.assertEqual(self.ledger(), {})
        for _ in range(AU.MIN_N):
            self.n.gate('weights')
        self.assertEqual(self.ledger()['neuromod_meta']['n'], 1)
        self.assertEqual(AU.assess(self.r, 'neuromod_meta')['verdict']['reason'], 'TOO_FEW_SHADOW_DECISIONS')

    def test_unseen_path_veto_and_conflict_do_not_supply_live_decisions(self):
        self.train()
        self.n.gate('unseen-path')
        self.n.signal(self.event(), path='weights', safety_veto=True)
        self.assertEqual(self.n.gate('weights')['factor'], 0.)
        self.assertEqual(self.ledger(), {})
        self.n.clear_veto('weights')
        def conflict(state):
            state['paths']['weights'].update(support=.8, contra=.8)
        self.n._mutate(conflict)
        gate = self.n.gate('weights')
        self.assertTrue(gate['conflict']['verify_first'])
        self.assertEqual(gate['factor'], 0.)
        self.assertEqual(self.ledger(), {})

    def test_restart_preserves_dedup_and_only_new_traces_add_comparisons(self):
        self.train()
        self.n.gate('weights')
        head = self.n._load()[0]['meta_head']
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.n = N.Neuromod(self.r.store)
        self.n.gate('weights')
        self.assertEqual(self.ledger()['neuromod_meta']['n'], 1)
        self.assertEqual(self.n._load()[0]['meta_head'], head)
        self.n.touch('weights', self.event())
        self.n.gate('weights')
        self.assertEqual(self.ledger()['neuromod_meta']['n'], 2)
        self.assertEqual(self.ledger()['neuromod_meta']['n_out'], 0)
        self.assertEqual(self.n.meta_mode(), 'SHADOW')
        with self.assertRaises(PermissionError):
            AU.promote(self.r, 'neuromod_meta', 'SYSTEM')

    def test_head_updates_and_explicit_active_keep_existing_application_semantics(self):
        self.train()
        self.n.gate('weights')
        # New observed retention trains exactly once and changes the head fingerprint.
        self.n.touch('weights', self.event())
        self.n.sync()
        self.retention(self.event(), False)
        self.n.sync()
        self.assertEqual(self.n._load()[0]['meta_head']['n'], N.META_MIN_N + 1)
        self.n.gate('weights')
        self.assertEqual(self.ledger()['neuromod_meta']['n'], 2)
        before = self.n.gate('weights', observe=False)
        with self.assertRaises(PermissionError):
            self.n.set_meta_mode('ACTIVE')
        self.n.set_meta_mode('ACTIVE', 'EXPLICIT_HUMAN')
        after = self.n.gate('weights')
        self.assertEqual(after['factor'], round(N.clamp(before['factor'] * after['meta']['p_applied'], N.EPS, 1.), 6))
        self.assertEqual(self.ledger()['neuromod_meta']['n'], 2)  # Same proposal, different application mode.
        self.assertEqual(self.ledger()['neuromod_meta']['n_out'], 0)


if __name__ == '__main__':
    unittest.main()

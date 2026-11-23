"""WP-T10: real controller decisions reach the existing shadow authority ledger.

These are software integration checks, not model utility or Redmi proofs.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import authority as AU
from v13.attention import Attention
from v13.callosum import Callosum, MIN_N as CHANNEL_MIN
from v13.deliberation import Deliberation, MIN_N as MODE_MIN


class LiveComparisons(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, 'test')['event_id']

    def ledger(self):
        return self.r.store.state(AU.KEY, AU.empty())[0]['ledger']

    def train_attention(self, attention):
        for _ in range(5):
            event = self.event()
            world = attention.request(event, 'JEF', 'WORLD', 'verify', priority=.3)
            body = attention.request(event, 'JEF', 'B1', 'verify', priority=.6)
            for response in attention.admit(event, [world, body], budget=128):
                attention.outcome(response['packet_id'], 1. if response['request_packet_id'] == world['packet_id'] else -1.)

    def test_untrained_scaffold_is_not_counted_as_learned_evidence(self):
        event = self.event()
        attention = Attention(self.r.store)
        request = attention.request(event, 'JEF', 'MEMORY', 'recall')
        attention.admit(event, [request])
        Deliberation(self.r.store).order(['HYPOTHESIS', 'SOURCE_CHECK'], ['NOVELTY'], True)
        Callosum(self.r.store).choose('B1_DETAIL', 'B2_GIST', 'SOURCE_EXACT', 'rev1')
        self.assertEqual(self.ledger(), {})

    def test_attention_records_ranking_without_duplicate_provider_or_fake_outcome(self):
        attention = Attention(self.r.store)
        self.train_attention(attention)
        event = self.event()
        world = attention.request(event, 'JEF', 'WORLD', 'verify', priority=.3)
        body = attention.request(event, 'JEF', 'B1', 'verify', priority=.6)
        calls = []
        def deliver(request):
            calls.append(request['packet_id'])
            return {'observed': True}
        responses = attention.admit(event, [world, body], budget=64, providers={'WORLD': deliver, 'B1': deliver})
        self.assertEqual(calls, [body['packet_id']])  # SHADOW keeps the scaffold budget decision
        self.assertEqual([x['request_packet_id'] for x in responses if x['status'] == 'GRANTED'], calls)
        self.assertEqual(self.ledger()['attention'], {'n': 1, 'same': 0, 'n_out': 0, 'scaffold_fail': 0, 'learned_fail': 0})
        assessed = AU.assess(self.r, 'attention')
        self.assertFalse(assessed['candidate_ok'])
        self.assertIn('OBJECTIVE_PARTIAL', assessed['blockers'])
        self.assertEqual(assessed['mode'], 'SHADOW')
        attention.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
        calls.clear()
        attention.admit(event, [world, body], budget=64, providers={'WORLD': deliver, 'B1': deliver})
        self.assertEqual(calls, [world['packet_id']])
        self.assertEqual(self.ledger()['attention']['n_out'], 0)

    def test_expired_or_foreign_attention_requests_do_not_supply_comparisons(self):
        attention = Attention(self.r.store)
        self.train_attention(attention)
        event = self.event()
        expired = attention.request(event, 'JEF', 'WORLD', 'verify', expires_at=1.)
        foreign = attention.request(self.event(), 'JEF', 'WORLD', 'verify')
        attention.admit(event, [expired, foreign])
        self.assertNotIn('attention', self.ledger())

    def test_deliberation_compares_learned_order_and_keeps_age_and_objective_gates(self):
        controller = Deliberation(self.r.store)
        modes = ['HYPOTHESIS', 'COUNTEREXAMPLE', 'SOURCE_CHECK']
        for _ in range(MODE_MIN):
            controller.record(self.event(), ['NOVELTY'], 'ANSWER', 2, [
                {'mode': 'HYPOTHESIS', 'verdict': 'PROPOSED'},
                {'mode': 'COUNTEREXAMPLE', 'verdict': 'NO_TARGET'},
                {'mode': 'SOURCE_CHECK', 'verdict': 'SUPPORTED'},
            ])
        actual, proposal, applied = controller.order(modes, ['NOVELTY'], True)
        self.assertEqual(actual, modes)
        self.assertEqual(proposal, ['HYPOTHESIS', 'SOURCE_CHECK', 'COUNTEREXAMPLE'])
        self.assertFalse(applied)
        self.assertEqual(self.ledger()['deliberation']['n'], 1)
        self.assertEqual(self.ledger()['deliberation']['same'], 0)
        controller.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
        self.assertEqual(controller.order(modes, ['NOVELTY'], False)[0], modes)
        self.assertFalse(controller.order(modes, ['NOVELTY'], False)[2])
        self.assertEqual(self.ledger()['deliberation']['n_out'], 0)

    def test_callosum_compares_only_measured_policy_and_resets_receiver_fallback(self):
        controller = Callosum(self.r.store)
        controller.choose('B1_DETAIL', 'B2_GIST', 'SOURCE_EXACT', 'rev1')
        def train(state):
            for _ in range(CHANNEL_MIN):
                controller._update(state, 'B1_TO_B2', 'NO_MESSAGE', .1)
                controller._update(state, 'B1_TO_B2', 'CONTROL', 1.)
        controller._mutate(train)
        actual, proposal, applied = controller.choose('B1_DETAIL', 'B2_GIST', 'SOURCE_EXACT', 'rev1')
        self.assertEqual((actual, proposal, applied), ('SOURCE_EXACT', 'CONTROL', False))
        self.assertEqual(self.ledger()['callosum']['n'], 1)
        self.assertEqual(self.ledger()['callosum']['same'], 0)
        self.assertEqual(controller.choose('B2_GIST', 'B1_DETAIL', 'SOURCE_EXACT', 'other'), ('SOURCE_EXACT', 'SOURCE_EXACT', False))
        self.assertEqual(controller.choose('B1_DETAIL', 'B2_GIST', 'SOURCE_EXACT', 'rev2'), ('SOURCE_EXACT', 'SOURCE_EXACT', False))
        self.assertEqual(self.ledger()['callosum']['n'], 1)
        self.assertEqual(controller.probabilities(controller._load()[0]['dirs']['B1_TO_B2'])['LATENT'], 0.)

    def test_comparisons_survive_restart_and_do_not_promote_partial_objectives(self):
        controller = Deliberation(self.r.store)
        modes = ['HYPOTHESIS', 'SOURCE_CHECK']
        for _ in range(MODE_MIN):
            controller.record(self.event(), ['NOVELTY'], 'ANSWER', 1, [{'mode': 'SOURCE_CHECK', 'verdict': 'SUPPORTED'}])
        for _ in range(AU.MIN_N):
            controller.order(modes, ['NOVELTY'], True)
        before = self.ledger()['deliberation']
        self.r.close()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.ledger()['deliberation'], before)
        report = AU.review(self.r)['heads']['deliberation']
        self.assertEqual(report['evidence']['agreement'], 1.)
        self.assertEqual(report['evidence']['n'], AU.MIN_N)
        self.assertEqual(report['level'], 0)
        self.assertIn('OBJECTIVE_PARTIAL', report['blockers'])
        with self.assertRaises(ValueError):
            AU.promote(self.r, 'deliberation', 'EXPLICIT_HUMAN')


if __name__ == '__main__':
    unittest.main()

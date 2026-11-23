"""Finite-world geometry and source visibility, no model or runtime mutation."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_fixture_generator', HERE / 'generate_fixtures.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


class PrivateFixtureGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = G.generate()
        cls.primary = [f for f in cls.doc['fixtures'] if f['kind'] == 'complementary']

    def test_every_primary_has_disjoint_necessary_sources_and_unique_paired_decision(self):
        self.assertEqual(len(self.primary), 30)
        self.assertEqual({f['oracle']['action'] for f in self.primary}, {'A', 'B', 'NONE'})
        for fixture in self.primary:
            self.assertEqual({s['owner'] for s in fixture['sources']}, set(G.ROLES))
            detail, gist = (G.facts(s['text'] for s in fixture['sources'] if s['owner'] == role) for role in G.ROLES)
            self.assertTrue(detail['budget'])
            self.assertFalse(detail['deadline'] or detail['local_only'])
            self.assertFalse(gist['budget'])
            self.assertTrue(gist['deadline'] and gist['local_only'])
            for role in G.ROLES:
                witnesses = G.completion_witnesses(fixture, [role])
                self.assertGreaterEqual(len(witnesses), 2, (fixture['id'], role))
                self.assertEqual(set(witnesses), set(fixture['visibility_proof'][role]['actions']))
                for action, witness in witnesses.items():
                    self.assertEqual(G.solve(fixture['public'], witness['rules']), witness['answer'])
                    self.assertEqual(action, witness['answer']['action'])
                self.assertEqual(G.oracle_for_quotes(fixture, G.exact_quotes(fixture, [role]))['action'], 'UNKNOWN')
            paired = G.completion_witnesses(fixture, G.ROLES)
            self.assertEqual(list(paired), [fixture['oracle']['action']])
            self.assertEqual(next(iter(paired.values()))['answer'], fixture['oracle'])
            self.assertEqual(G.completion_witnesses(fixture, ['B1_DETAIL', 'B1_DETAIL']),
                             G.completion_witnesses(fixture, ['B1_DETAIL']))  # Same-policy duplication gains no peer fact.

    def test_controls_abstain_on_missing_and_conflicting_required_rules(self):
        controls = [f for f in self.doc['fixtures'] if f['kind'] in ('missing_rule', 'contradictory_rule')]
        self.assertEqual(len(controls), 6)
        for fixture in controls:
            self.assertEqual(fixture['oracle']['action'], 'UNKNOWN')
            self.assertTrue(all(o['remaining'] is None and o['eligible'] is None for o in fixture['oracle']['options']))
            if fixture['kind'] == 'contradictory_rule':
                self.assertEqual(G.completion_witnesses(fixture, G.ROLES), {})
            else:
                self.assertEqual(G.facts(s['text'] for s in fixture['sources'])['local_only'], set())

    def test_exact_controls_supply_source_facts_not_an_oracle_answer(self):
        controls = [f for f in self.doc['fixtures'] if f['kind'] == 'exact_control']
        self.assertEqual(len(controls), 3)
        for fixture in controls:
            user = json.loads(G.consumer_messages(fixture, G.exact_quotes(fixture))[1]['content'])
            self.assertEqual(set(user), {'current_source', 'verified_quotes'})
            self.assertEqual(len(user['verified_quotes']), 2)
            self.assertEqual(G.oracle_for_quotes(fixture, user['verified_quotes']), fixture['oracle'])
            self.assertNotIn('oracle', G.canonical(user))

    def test_unobserved_peer_and_oracle_do_not_influence_producer_messages(self):
        fixture = self.primary[0]
        baseline = {role: G.producer_messages(fixture, role) for role in G.ROLES}
        poisoned = copy.deepcopy(fixture)
        poisoned['oracle'] = {'project': 'ORACLE_LEAK_SENTINEL', 'action': 'ORACLE_LEAK_SENTINEL'}
        poisoned['visibility_proof'] = {'bad': 'ORACLE_LEAK_SENTINEL'}
        for role in G.ROLES:
            self.assertEqual(G.producer_messages(poisoned, role), baseline[role])
        self.assertEqual(G.consumer_messages(poisoned), G.consumer_messages(fixture))
        poisoned.pop('oracle')
        self.assertEqual(G.consumer_messages(poisoned, G.exact_quotes(poisoned)),
                         G.consumer_messages(fixture, G.exact_quotes(fixture)))
        for role in G.ROLES:
            peer_changed = copy.deepcopy(fixture)
            peer = next(s for s in peer_changed['sources'] if s['owner'] != role)
            peer_changed['sources'] = [G.source(s['owner'], 'PEER_CONTENT_SENTINEL') if s is peer else s
                                       for s in peer_changed['sources']]
            self.assertEqual(G.producer_messages(peer_changed, role), baseline[role])
            view = json.loads(baseline[role][1]['content'])
            self.assertEqual(len(view['private_sources']), 1)
            self.assertEqual(view['private_sources'][0]['source_id'],
                             next(s['source_id'] for s in fixture['sources'] if s['owner'] == role))

    def test_consumer_has_no_hidden_source_fallback_and_rejects_forged_quotes(self):
        fixture = self.primary[0]
        user = json.loads(G.consumer_messages(fixture)[1]['content'])
        self.assertEqual(user['verified_quotes'], [])
        self.assertEqual(G.facts([user['current_source']]), {k: set() for k in G.REQUIRED})
        self.assertEqual(G.oracle_for_quotes(fixture, [])['action'], 'UNKNOWN')
        genuine = G.exact_quotes(fixture)
        for mutate in ('text', 'sha256', 'source_id', 'extra'):
            bad = copy.deepcopy(genuine[:1])
            if mutate == 'extra':
                bad[0]['oracle'] = fixture['oracle']
            else:
                bad[0][mutate] = 'FORGED'
            with self.assertRaises(ValueError):
                G.consumer_messages(fixture, bad)
        with self.assertRaises(ValueError):
            G.consumer_messages(fixture, [genuine[0], genuine[0]])
        other = self.primary[1]
        with self.assertRaises(ValueError):
            G.consumer_messages(fixture, G.exact_quotes(other))

    def test_generator_varies_labels_and_local_constraints_without_changing_proof(self):
        for seed in (13, 21, 34):
            fixtures = [f for f in G.generate(seed, 9)['fixtures'] if f['kind'] == 'complementary']
            self.assertEqual({f['oracle']['action'] for f in fixtures}, {'A', 'B', 'NONE'})
            for f in fixtures:
                self.assertEqual(len(f['paired_actions']), 1)
                self.assertTrue(all(len(f['visibility_proof'][r]['actions']) >= 2 for r in G.ROLES))
        local_values = set().union(*(G.facts(s['text'] for s in f['sources'])['local_only'] for f in self.primary))
        self.assertEqual(local_values, {True, False})

    def test_fresh_exports_are_byte_reproducible_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'one', Path(d) / 'two'
            G.export(a, primary_count=3)
            G.export(b, primary_count=3)
            self.assertEqual(sorted(p.name for p in a.iterdir()), sorted(p.name for p in b.iterdir()))
            for path in a.iterdir():
                self.assertEqual(path.read_bytes(), (b / path.name).read_bytes())
            with self.assertRaises(FileExistsError):
                G.export(a, primary_count=3)
        for invalid in (0, 1, -3, True):
            with self.assertRaises(ValueError):
                G.generate(primary_count=invalid)

    def test_original_decision_scorer_compatible_and_old_seventy_row_fixture_unchanged(self):
        app = HERE.parents[3]
        sys.path.insert(0, str(app))
        from v13.utility import score_decision
        original_path = app / 'tests/integration_step2_utility.py'
        before = G.digest(original_path.read_bytes())
        spec = importlib.util.spec_from_file_location('original_step2_fixture_geometry', original_path)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        self.assertEqual((len(original.FIXTURES), len(original.VARIANTS)), (10, 7))
        self.assertEqual(len(original.FIXTURES) * len(original.VARIANTS), 70)
        for fixture in self.doc['fixtures']:
            self.assertTrue(score_decision(fixture['oracle'], fixture['oracle'])['exact'])
        self.assertEqual(G.digest(original_path.read_bytes()), before)
        self.assertFalse(self.doc['gate_promotion'])
        self.assertEqual(self.doc['historical_step2_utility'], 'UTILITY_FAIL_UNCHANGED')


if __name__ == '__main__':
    unittest.main()

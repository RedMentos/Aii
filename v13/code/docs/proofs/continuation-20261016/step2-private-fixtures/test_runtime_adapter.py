"""Software runner-seam tests with real Runtime, SQLite, blobs and SourceRefs.

The fake generates scripted bytes; these tests provide no native utility result.
"""
import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_runtime_adapter', HERE / 'runtime_adapter.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class ScriptedRunner:
    def __init__(self, role, owner):
        self.role, self.owner, self.last_metrics = role, owner, {}

    def generate(self, messages, cancel, deadline, tokens, schema, seed=13):
        self.owner.calls.append({'role': self.role, 'messages': copy.deepcopy(messages),
                                 'tokens': tokens, 'schema': copy.deepcopy(schema), 'seed': seed})
        if self.role == 'C3_LANGUAGE':
            raw = self.owner.consumer
        else:
            view = json.loads(messages[1]['content'])
            raw = A.dumps({'quotes': [{'source_ref': item['source_ref'], 'text': item['text']}
                                      for item in view['private_sources']]})
            if self.owner.producer is not None:
                raw = self.owner.producer(self.role, view)
        self.last_metrics = {'status': 'FINAL', 'evidence_level': 'SOFTWARE_SCRIPTED_NO_NATIVE_PROCESS'}
        yield raw


class RunnerSeam:
    def __init__(self, consumer, producer=None):
        self.consumer, self.producer, self.calls = consumer, producer, []

    def get(self, role):
        return ScriptedRunner(role, self)


@contextmanager
def real_runtime():
    with tempfile.TemporaryDirectory() as root:
        home = Path(root) / 'home'
        A.initialize(home)
        A.save_config(home, A.CONFIG)
        A.disable_background_sleep(home)
        runtime = A.Runtime(home)
        try:
            yield runtime
        finally:
            runtime.close()


class PrivateRuntimeAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = A.G.generate()
        cls.fixture = next(f for f in cls.doc['fixtures'] if f['kind'] == 'complementary')

    def run_fake(self, variant, fixture=None, consumer=None, producer=None):
        fixture = fixture or self.fixture
        seam = RunnerSeam(A.dumps(fixture['oracle']) if consumer is None else consumer, producer)
        with real_runtime() as runtime:
            with patch.object(runtime.pool, 'get', side_effect=seam.get):
                row = A.run_row(runtime, fixture, variant)
            self.assertFalse(runtime.store.integrity(True))
        return row, seam

    def test_runner_boundary_gets_role_private_sources_and_common_public_options(self):
        row, seam = self.run_fake('paired_model_quotes')
        self.assertEqual(row['status'], 'RECORDED')
        self.assertTrue(row['score']['exact'])
        self.assertEqual([call['role'] for call in seam.calls], ['B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'])
        producer_views = [json.loads(call['messages'][1]['content']) for call in seam.calls[:2]]
        self.assertEqual(producer_views[0]['current_source'], producer_views[1]['current_source'])
        self.assertEqual(producer_views[0]['current_source'], A.G.render_current(self.fixture['public']))
        detail, gist = [view['private_sources'][0]['text'] for view in producer_views]
        self.assertTrue(A.G.facts([detail])['budget'])
        self.assertFalse(A.G.facts([detail])['deadline'] or A.G.facts([detail])['local_only'])
        self.assertFalse(A.G.facts([gist])['budget'])
        self.assertTrue(A.G.facts([gist])['deadline'] and A.G.facts([gist])['local_only'])
        for call, recorded in zip(seam.calls, row['calls']):
            self.assertEqual(call['messages'], recorded['messages'])
        consumer = json.loads(seam.calls[-1]['messages'][1]['content'])
        self.assertEqual(set(consumer), {'current_source', 'verified_quotes'})
        self.assertEqual(consumer['verified_quotes'], row['delivered_quotes'])
        self.assertEqual(len(consumer['verified_quotes']), 2)
        self.assertNotIn('oracle', A.dumps(seam.calls))
        self.assertEqual(row['evidence_level'], 'UNCLASSIFIED_RUNNER_BOUNDARY')

    def test_same_policy_dual_is_two_identical_b1_private_inputs_never_union(self):
        row, seam = self.run_fake('same_policy_dual')
        self.assertEqual(row['status'], 'RECORDED')
        self.assertEqual([call['role'] for call in seam.calls], ['B1_DETAIL', 'B1_DETAIL', 'C3_LANGUAGE'])
        self.assertEqual(seam.calls[0]['messages'], seam.calls[1]['messages'])
        self.assertEqual(len(row['delivered_quotes']), 1)  # duplicate transport gives no new source
        quoted = A.G.facts(q['text'] for q in row['delivered_quotes'])
        self.assertTrue(quoted['budget'])
        self.assertFalse(quoted['deadline'] or quoted['local_only'])

    def test_solos_and_no_message_never_recover_unseen_private_sources(self):
        for variant, expected_roles in [('b1_model_quotes', ['B1_DETAIL', 'C3_LANGUAGE']),
                                        ('b2_model_quotes', ['B2_GIST', 'C3_LANGUAGE']),
                                        ('no_message', ['B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'])]:
            with self.subTest(variant=variant):
                row, seam = self.run_fake(variant)
                self.assertEqual([call['role'] for call in seam.calls], expected_roles)
                self.assertEqual(len(row['delivered_quotes']), 0 if variant == 'no_message' else 1)
        # A producer deliberately returns no evidence. The consumer is still
        # invoked with EMPTY quotes; supplied source text is never substituted.
        row, seam = self.run_fake('paired_model_quotes', producer=lambda *unused: '{"quotes":[]}')
        self.assertEqual(row['delivered_quotes'], [])
        self.assertEqual(json.loads(seam.calls[-1]['messages'][1]['content'])['verified_quotes'], [])

    def test_exact_control_has_no_producer_and_is_labeled_deterministic(self):
        row, seam = self.run_fake('exact_source_control')
        self.assertEqual([call['role'] for call in seam.calls], ['C3_LANGUAGE'])
        self.assertEqual(row['delivery_origin'], 'EXACT_SOURCE_CONTROL')
        self.assertEqual(len(row['delivered_quotes']), 2)
        self.assertFalse(row['gate_promotion'])
        self.assertEqual(row['historical_step2_utility'], 'UTILITY_FAIL_UNCHANGED')

    def test_incorrect_consumer_answer_is_scored_unchanged_without_oracle_repair(self):
        answer = copy.deepcopy(self.fixture['oracle'])
        answer['action'] = 'UNKNOWN'
        row, seam = self.run_fake('paired_model_quotes', consumer=A.dumps(answer))
        self.assertEqual(row['status'], 'RECORDED')
        self.assertFalse(row['score']['exact'])
        self.assertIn('action', row['score']['contradictions'])
        self.assertEqual(row['raw_answer'], A.dumps(answer))

    def test_hidden_oracle_and_witness_mutations_never_change_runner_prompts(self):
        poisoned = copy.deepcopy(self.fixture)
        poisoned['oracle'] = {'FORBIDDEN_ORACLE_SENTINEL': 'SHOULD_NOT_ENTER_RUNNER'}
        poisoned['visibility_proof'] = 'FORBIDDEN_ORACLE_SENTINEL'
        poisoned['paired_actions'] = 'FORBIDDEN_ORACLE_SENTINEL'
        row, seam = self.run_fake('paired_model_quotes', fixture=poisoned, consumer='{}')
        self.assertNotIn('FORBIDDEN_ORACLE_SENTINEL', A.dumps(seam.calls))
        self.assertEqual(len(seam.calls), 3)

    def test_forged_model_quote_stops_before_consumer_no_fallback(self):
        def forged(role, view):
            quote = copy.deepcopy(view['private_sources'][0])
            quote['text'] += ' Budget 999 euros.'
            return A.dumps({'quotes': [quote]})
        row, seam = self.run_fake('paired_model_quotes', producer=forged)
        self.assertEqual(row['status'], 'ERROR')
        self.assertEqual(row['score']['utility'], 0.)
        self.assertEqual([call['role'] for call in seam.calls], ['B1_DETAIL'])
        self.assertEqual(row['delivered_quotes'], [])
        self.assertIn('differs from Store bytes', row['error'])

    def test_real_store_rejects_peer_identity_deleted_and_tampered_blob(self):
        with real_runtime() as runtime:
            event, private = A.insert_sources(runtime, self.fixture)
            detail, gist = private
            def envelope(item):
                return A.dumps({'quotes': [{'source_ref': item['source_ref'],
                                            'text': runtime.store.read_source(item['source_ref'])}]})
            with self.assertRaisesRegex(ValueError, 'visibility'):
                A.validate_model_quotes(runtime, envelope(gist), private, 'B1_DETAIL')
            raw = envelope(detail)
            valid = A.validate_model_quotes(runtime, raw, private, 'B1_DETAIL')
            blob = runtime.home / 'data/blobs' / detail['source_ref']['sha256']
            original = blob.read_bytes()
            blob.write_bytes(original + b'TAMPER')
            with self.assertRaisesRegex(ValueError, 'Hash'):
                A.validate_model_quotes(runtime, raw, private, 'B1_DETAIL')
            with self.assertRaisesRegex(ValueError, 'Hash'):
                A.consumer_messages(runtime, event, valid)
            blob.write_bytes(original)
            with runtime.store.tx() as connection:
                connection.execute('UPDATE sources SET deleted=1 WHERE id=?', (detail['source_ref']['source_id'],))
            with self.assertRaisesRegex(ValueError, 'SourceRef'):
                A.validate_model_quotes(runtime, raw, private, 'B1_DETAIL')

    def test_quote_contract_rejects_extra_fields_spans_duplicates_and_nonfinite_json(self):
        with real_runtime() as runtime:
            event, private = A.insert_sources(runtime, self.fixture)
            ref = copy.deepcopy(private[0]['source_ref'])
            quote = {'source_ref': ref, 'text': runtime.store.read_source(ref)}
            bad = []
            extra = copy.deepcopy(quote)
            extra['answer'] = 'A'
            bad.append({'quotes': [extra]})
            for field, value in [('char_start', True), ('char_end', ref['char_end'] - 1),
                                 ('modality', 'audio'), ('sha256', 'f' * 64)]:
                changed = copy.deepcopy(quote)
                changed['source_ref'][field] = value
                bad.append({'quotes': [changed]})
            bad += [{'quotes': [quote, quote]}, {'quotes': [quote] * 5}, {'quotes': [], 'summary': 'forbidden'}]
            for obj in bad:
                with self.subTest(obj=obj), self.assertRaises(ValueError):
                    A.validate_model_quotes(runtime, A.dumps(obj), private, 'B1_DETAIL')
            for raw in ('{"quotes":[],"quotes":[]}', '{"quotes":NaN}', '{"quotes":Infinity}'):
                with self.assertRaises(ValueError):
                    A.validate_model_quotes(runtime, raw, private, 'B1_DETAIL')

    def test_missing_and_conflicting_controls_keep_explicit_unknown_labels(self):
        controls = [f for f in self.doc['fixtures'] if f['kind'] in {'missing_rule', 'contradictory_rule'}]
        for fixture in controls:
            row, seam = self.run_fake('paired_model_quotes', fixture=fixture)
            self.assertEqual(row['kind'], fixture['kind'])
            self.assertEqual(row['status'], 'RECORDED')
            self.assertTrue(row['score']['exact'])
            self.assertEqual(json.loads(row['raw_answer'])['action'], 'UNKNOWN')
            self.assertEqual(len(row['delivered_quotes']), 2)

    def test_source_refs_survive_real_store_close_restart(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            A.initialize(home)
            A.save_config(home, A.CONFIG)
            A.disable_background_sleep(home)
            runtime = A.Runtime(home)
            event, private = A.insert_sources(runtime, self.fixture)
            before = A.producer_messages(runtime, event, private, 'B1_DETAIL')
            runtime.close()
            runtime = A.Runtime(home)
            try:
                self.assertEqual(A.producer_messages(runtime, event, private, 'B1_DETAIL'), before)
                self.assertFalse(runtime.store.integrity(True))
            finally:
                runtime.close()

    def test_registration_is_coverage_bound_and_rejects_relabeling_or_modified_geometry(self):
        with patch.object(A, 'installed_bindings', return_value={'synthetic': 'NOT_NATIVE'}):
            registration = A.registration(Path('/unused'), self.doc, [self.fixture['id']],
                                          ['paired_model_quotes', 'exact_source_control'])
            self.assertEqual(registration['max_rows'], 2)
            self.assertEqual(registration['max_native_calls'], 4)
            self.assertEqual(registration['max_total_row_seconds'], 180)
            self.assertFalse(registration['gate_promotion'])
            self.assertEqual(registration['numeric_utility_gate'], 'NOT_DEFINED_FOR_THIS_NEW_ADAPTER')
            self.assertIn('prompt_only_retention_ablation', registration['unimplemented_controls'])
            for ids, variants in [([], None), ([self.fixture['id']] * 2, None), (['missing'], None),
                                  (None, []), (None, ['both_control']), (None, ['same_policy_dual'] * 2)]:
                with self.assertRaises(ValueError):
                    A.registration(Path('/unused'), self.doc, ids, variants)
            changed = copy.deepcopy(self.doc)
            changed['fixtures'][0]['oracle']['action'] = 'FORGED'
            with self.assertRaisesRegex(ValueError, 'fixed private fixture'):
                A.registration(Path('/unused'), changed)
            with tempfile.TemporaryDirectory() as d:
                changed_registration = copy.deepcopy(registration)
                changed_registration['source_bindings']['v13/runtime.py'] = 'FORGED'
                with patch.object(A, 'prepare_home', side_effect=AssertionError('Must not reach inference')):
                    with self.assertRaisesRegex(ValueError, 'binding changed'):
                        A.run_registered(Path('/unused'), self.doc, changed_registration, Path(d) / 'out')

    def test_progress_snapshots_capture_exact_prompts_before_runner_generation(self):
        snapshots = []
        seam = RunnerSeam(A.dumps(self.fixture['oracle']))
        with real_runtime() as runtime:
            def record(row):
                snapshots.append(copy.deepcopy(row))
            with patch.object(runtime.pool, 'get', side_effect=seam.get):
                row = A.run_row(runtime, self.fixture, 'paired_model_quotes', record=record)
        self.assertEqual(row['status'], 'RECORDED')
        self.assertTrue(snapshots)
        first = snapshots[0]['calls'][0]
        self.assertEqual(first['raw'], '')
        self.assertEqual(first['status'], 'RUNNING')
        self.assertEqual(first['messages'], seam.calls[0]['messages'])
        self.assertEqual(snapshots[-1], row)

    def test_registered_cohort_uses_fresh_real_stores_and_keeps_structural_failures(self):
        # Still fake only at runner seam. No fake child processes are declared
        # reaped, so the outer native harness must keep NOT_CONFIRMED despite
        # scripted exact decisions and complete row coverage.
        seam = RunnerSeam(A.dumps(self.fixture['oracle']))
        def get(pool, role):
            return seam.get(role)
        with tempfile.TemporaryDirectory() as d:
            installed, out = Path(d) / 'installed', Path(d) / 'cohort'
            A.initialize(installed)
            (installed / 'config/models.json').write_text('{}')
            with patch.object(A, 'installed_bindings', return_value={'synthetic': 'NOT_NATIVE'}):
                prereg = A.registration(installed, self.doc, [self.fixture['id']],
                                        ['b1_model_quotes', 'same_policy_dual'])
                with patch('v13.runners.RunnerPool.get', new=get):
                    report = A.run_registered(installed, self.doc, prereg, out)
            self.assertEqual(report['status'], 'NOT_CONFIRMED')
            self.assertTrue(report['coverage_complete'])
            self.assertEqual(len(report['rows']), 2)
            self.assertEqual({r['status'] for r in report['rows']}, {'STRUCTURAL_FAIL'})
            sources = []
            for row in report['rows']:
                name = row['fixture'] + '__' + row['variant']
                self.assertTrue((out / (name + '.partial.json')).is_file())
                self.assertEqual(A.strict_json((out / (name + '.json')).read_text()), row)
                sources.append(row['event']['source_ref']['source_id'])
                self.assertEqual(report['row_sha256'][row['fixture'] + ':' + row['variant']], A.digest(A.dumps(row)))
            self.assertEqual(len(set(sources)), 2)
            self.assertEqual(A.strict_json((out / 'report.json').read_text()), report)


if __name__ == '__main__':
    unittest.main()

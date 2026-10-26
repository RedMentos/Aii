"""Run575 actual-live Runtime.submit/_turn pilot contract tests, entirely no-model."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run575_true_live_pilot as live


class FakeStore:
    def __init__(self, statuses=None):
        self.statuses = statuses or {}
    def one(self, sql, args):
        eid = args[0]
        value = self.statuses.get(eid)
        if value is None:
            return None
        return {'event_id': eid, 'status': value[0], 'text': value[1],
                'metadata': value[2] if len(value) > 2 else '{}'}


class FakeRuntime:
    def __init__(self, home):
        self.home = home
        self.sent = []
        self.closed = False
        self.cancelled = False
        self.store = FakeStore()
    def submit(self, text):
        self.sent.append(text)
        eid = len(self.sent)
        self.store.statuses[eid] = ('FINAL', '{"project":"x"}')
        return eid
    def cancel(self):
        self.cancelled = True
    def close(self):
        self.closed = True


class TrueLivePilotTests(unittest.TestCase):
    def test_plan_exact_six_dialogues_twenty_four_turns_and_no_oracle_in_input(self):
        p = live.registration()
        self.assertEqual(p['status'], 'TRUE_LIVE_SOURCE_ONLY_NOT_EXECUTED')
        self.assertEqual(p['planned_live_turns'], 24)
        self.assertEqual(p['fixture_ids'], ['Helios', 'Kepler', 'Mistral'])
        self.assertEqual(p['arms'], ['CURRENT', 'LEGACY'])
        self.assertEqual(len(set(p['dialogue_keys'])), 6)
        self.assertEqual(p['dialogue_keys_sha256'], live.sha(p['dialogue_keys']))
        self.assertEqual(len(p['source_fixtures']), 3)
        self.assertTrue(all(set(f)=={'id','type','history','current'}
                            for f in p['source_fixtures']))
        self.assertEqual(set(p['scoring_oracles_not_for_runtime']),
                         set(p['fixture_ids']))
        self.assertIs(p['native_executed'], False)
        self.assertIs(p['canonical_gate_pass'], False)
        self.assertEqual(p['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(p['jepa_weight'], 0)
        self.assertIs(p['redmi_measured'], False)
        self.assertEqual(live.registration(), p)

    def test_plan_exclusive_and_tamper_preflight_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            p = live.prepare_plan(work)
            self.assertEqual(live.exact_plan(work), p)
            with self.assertRaisesRegex(ValueError, 'FRESH_WORK_REQUIRED'):
                live.prepare_plan(work)
            path = work / live.PLAN
            altered = copy.deepcopy(p)
            altered['instruction'] = 'Guess.'
            path.write_text(json.dumps(altered))
            with patch.object(live.pinned, 'verify_installed') as verify:
                with self.assertRaisesRegex(ValueError, 'PLAN_CHANGED'):
                    live.execute(work, work/'installed')
                verify.assert_not_called()

    def test_exact_event_id_ownership_and_terminal(self):
        fake = FakeRuntime('home')
        fake.store.statuses[17] = ('FINAL', 'done')
        self.assertEqual(live.wait_terminal(fake, 17, timeout=1),
                         {'event_id': 17, 'status': 'FINAL', 'text': 'done'})
        class WrongStore:
            def one(self, sql, args):
                return {'event_id': 999, 'status': 'FINAL', 'text': 'other'}
        fake.store = WrongStore()
        with self.assertRaisesRegex(ValueError, 'ASSISTANT_EVENT_OWNERSHIP_CHANGED'):
            live.wait_terminal(fake, 17, timeout=1)

    def test_timeout_cancels_and_refuses_invalid_event(self):
        fake = FakeRuntime('home')
        ticks = iter((0., .01, .03, .06, .11))
        with self.assertRaisesRegex(TimeoutError, 'LIVE_TURN_TIMEOUT_CANCEL_REQUESTED'):
            live.wait_terminal(fake, 7, timeout=.05, clock=lambda: next(ticks),
                               sleep=lambda _: None)
        self.assertTrue(fake.cancelled)
        with self.assertRaisesRegex(ValueError, 'EVENT_ID_INVALID'):
            live.wait_terminal(fake, 0)

    def test_actual_submit_sequential_history_current_and_close(self):
        f = live.registration()['source_fixtures'][0]
        cfg = live.registration()['config_snapshots']['CURRENT']
        created = []
        def make_runtime(home):
            r = FakeRuntime(home)
            created.append(r)
            return r
        with tempfile.TemporaryDirectory() as tmp:
            row = live.run_dialogue(Path(tmp)/'installed', Path(tmp), 'CURRENT', f, cfg,
                                    runtime_factory=make_runtime,
                                    home_factory=lambda installed, home, cfg: home)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].sent[:3], f['history'])
        self.assertEqual(created[0].sent[3], f['current']+'\n'+live.INSTRUCTION)
        self.assertEqual(len(row['turns']), 4)
        self.assertTrue(created[0].closed)
        self.assertEqual([t['event_id'] for t in row['turns']], [1,2,3,4])
        self.assertIs(row['native_final_observed'], False)
        self.assertIs(row['native_executed'], False)

    def test_live_nonfinal_turn_closes_runtime_and_refuses(self):
        f = live.registration()['source_fixtures'][0]
        cfg = live.registration()['config_snapshots']['CURRENT']
        created = []
        def make_runtime(home):
            r = FakeRuntime(home)
            created.append(r)
            return r
        def not_final(runtime, event):
            return {'event_id': event, 'status': 'DEADLINE', 'text': ''}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'LIVE_TURN_NOT_FINAL'):
                live.run_dialogue(Path(tmp)/'installed', Path(tmp), 'CURRENT', f, cfg,
                                  runtime_factory=make_runtime,
                                  home_factory=lambda installed, home, cfg: home,
                                  wait=not_final)
        self.assertTrue(created[0].closed)
        self.assertEqual(len(created[0].sent), 1)

    def test_evaluation_wrong_committed_and_unknown_distinguished(self):
        oracle = live.registration()['scoring_oracles_not_for_runtime']['Helios']
        good = {'arm': 'CURRENT', 'fixture': 'Helios', 'native_executed': False, 'native_final_observed': False,
                'turns': [{'index': x} for x in range(4)],
                'final_answer': json.dumps(oracle)}
        self.assertFalse(live.evaluate(good, oracle)['wrong_committed'])
        wrong = copy.deepcopy(good)
        wrong_action = 'A' if oracle['action'] != 'A' else 'B'
        wrong['final_answer'] = json.dumps(dict(oracle, action=wrong_action))
        self.assertTrue(live.evaluate(wrong, oracle)['wrong_committed'])
        unknown = copy.deepcopy(good)
        unknown['final_answer'] = '{"project":"x","action":"UNKNOWN","options":[]}'
        self.assertTrue(live.evaluate(unknown, oracle)['unknown'])

    def test_native_final_observation_refuses_unproven_final(self):
        fake = FakeRuntime('home')
        fake.store.statuses[17] = ('FINAL', 'answer')
        self.assertFalse(live.native_final_observed(fake, 17))
        self.assertFalse(live.native_final_observed(fake, 0))
        self.assertFalse(live.native_final_observed(fake, 999))

    def test_native_final_observation_requires_exact_metadata(self):
        fake = FakeRuntime('home')
        good = {'model_generated': True, 'model_revision': 'pinned-revision',
                'runner': {'role': 'C3_LANGUAGE', 'actual_model': 'pinned-model',
                           'generated_tokens': 2, 'prompt_tokens': 10,
                           'duration_s': 1.0, 'ttft_s': .5}}
        fake.store.statuses[17] = ('FINAL', 'answer', json.dumps(good))
        self.assertTrue(live.native_final_observed(fake, 17))
        for changed in (
            {'model_generated': False},
            {'model_revision': ''},
            {'runner': dict(good['runner'], role='B1_DETAIL')},
            {'runner': dict(good['runner'], generated_tokens=0)},
            {'runner': dict(good['runner'], generated_tokens=True)},
            {'runner': dict(good['runner'], prompt_tokens=0)},
            {'runner': dict(good['runner'], duration_s=float('nan'))},
            {'runner': dict(good['runner'], ttft_s=float('inf'))},
            {'runner': dict(good['runner'], actual_model='')},
        ):
            with self.subTest(changed=changed):
                meta = dict(good, **changed)
                fake.store.statuses[17] = ('FINAL', 'answer', json.dumps(meta))
                self.assertFalse(live.native_final_observed(fake, 17))
        fake.store.statuses[17] = ('FINAL', 'answer', 'not-json')
        self.assertFalse(live.native_final_observed(fake, 17))
        fake.store.statuses[17] = ('CANCELLED', 'answer', json.dumps(good))
        self.assertFalse(live.native_final_observed(fake, 17))
        fake.store.statuses[17] = ('FINAL', '', json.dumps(good))
        self.assertFalse(live.native_final_observed(fake, 17))

    def test_synthetic_metadata_does_not_become_native_executed(self):
        fake = FakeRuntime('home')
        fake.store.statuses[17] = ('FINAL', 'answer', json.dumps({
            'model_generated': True, 'model_revision': 'pinned-revision',
            'runner': {'role': 'C3_LANGUAGE', 'actual_model': 'pinned-model',
                       'generated_tokens': 2, 'prompt_tokens': 10,
                       'duration_s': 1.0, 'ttft_s': .5}}))
        self.assertTrue(live.native_final_observed(fake, 17))
        # Metadata is not an independent process/model/raw proof.
        with self.assertRaisesRegex(ValueError, 'SOURCE_ONLY_NATIVE_CLAIM_FORBIDDEN'):
            live.evaluate({'arm': 'CURRENT', 'fixture': 'Helios',
                           'native_executed': True, 'turns': [{}] * 4,
                           'final_answer': '{}'},
                          live.registration()['scoring_oracles_not_for_runtime']['Helios'])

    def test_failed_preflight_exclusive_claim_no_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            live.prepare_plan(work)
            with patch.object(live.pinned, 'verify_installed',
                              side_effect=ValueError('NO_PINNED_MODELS')):
                with self.assertRaisesRegex(ValueError, 'NO_PINNED_MODELS'):
                    live.execute(work, work/'installed')
            self.assertTrue((work / live.ATTEMPT).is_file())
            self.assertFalse((work / live.PROGRESS).exists())
            self.assertFalse((work / live.RESULT).exists())
            with self.assertRaisesRegex(ValueError, 'REFUSE_REUSE_OR_PARTIAL_LIVE_ATTEMPT'):
                live.execute(work, work/'installed')

    def test_synthetic_six_dialogue_full_path_and_wrong_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            p = live.prepare_plan(work)
            preflight = {'model_sha256': p['model_sha256_expected_not_retrieved'],
                         'runner_sha256': p['runner_sha256_expected_not_retrieved'],
                         'runtime_library_sha256': {'lib': 'f'*64},
                         'native_executed': False}
            def fake_dialogue(installed, work, arm, fixture, cfg, *args):
                oracle = p['scoring_oracles_not_for_runtime'][fixture['id']]
                return {'arm': arm, 'fixture': fixture['id'],
                        'turns': [{'index': i} for i in range(4)],
                        'final_answer': json.dumps(oracle),
                    'native_final_observed': False, 'native_executed': False}
            with patch.object(live.pinned, 'verify_installed', return_value=preflight), \
                 patch.object(live, 'run_dialogue', side_effect=fake_dialogue) as fake:
                out = live.execute(work, work/'installed')
                self.assertEqual(fake.call_count, 6)
            self.assertEqual(out['live_turns'], 24)
            self.assertEqual(len(out['evaluations']), 6)
            self.assertIs(out['native_executed'], False)
            self.assertEqual(out['native_final_observed_count'], 0)
            self.assertFalse(out['canonical_gate_pass'])
            self.assertEqual(len((work / live.PROGRESS).read_text().splitlines()), 12)
            self.assertEqual(len((work / live.RAW).read_text().splitlines()), 6)
            self.assertTrue((work / live.RESULT).is_file())


if __name__ == '__main__':
    unittest.main()

"""Run558 source-only strict frozen FUTURE_003..024 batch tests, no native."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run500_step2_stage_map as stages
import run504_remaining980_schedule as schedule
import run558_future_batch as batch


def workdir(tmp):
    work = Path(tmp)
    stages.write_new(work / 'RUN500_STAGE_MAP.json', stages.registration())
    schedule.write_exclusive(work / 'RUN504_SCHEDULE.json', schedule.registration())
    return work


def mock_child(command, log_path, timeout_s=3600):
    stage_id = command[command.index('--stage-id') + 1]
    work = Path(command[command.index('--work') + 1])
    folder = work / ('stage_' + stage_id)
    folder.mkdir()
    (folder / 'RUN500_STAGE_RESULT.json').write_text(json.dumps({
        'status': 'STAGE_14_ROWS_STRUCTURALLY_VERIFIED_ONLY',
        'stage_id': stage_id, 'rows_verified': 14,
        'native_execution_performed': True, 'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'redmi_measured': False,
    }))
    Path(log_path).write_text('MOCK_ONLY_NO_NATIVE\n')
    return 0


class FutureBatchSourceOnly(unittest.TestCase):
    def test_all_remaining_batches_exact_disjoint_and_last_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            frozen = stages.registration()
            future = schedule.registration()
            seen = set()
            for index, bid in enumerate(batch.ALLOWED, 2):
                p = batch.plan(work, bid)
                expected = future['batches'][index]
                self.assertEqual(p['stage_ids'], expected['stage_ids'])
                self.assertEqual(p['row_keys_sha256'], expected['row_keys_sha256'])
                self.assertEqual(p['expected_rows'], 14 if bid == 'FUTURE_024' else 42)
                self.assertFalse(p['native_executed'])
                self.assertFalse(p['canonical_gate_pass'])
                self.assertEqual(p['step2_exit'], 'UTILITY_FAIL')
                keys = {tuple(key) for sid in p['stage_ids']
                        for key in stages.choose(frozen, sid)['row_keys']}
                self.assertFalse(keys & seen)
                seen.update(keys)
            self.assertEqual(len(seen), 980 - 84)
            p = batch.plan(work, 'FUTURE_003')
            self.assertEqual(p['stage_ids'], ['A_s32_p01','A_s32_p02','A_s32_p03'])
            self.assertEqual(p['arm_seed_pairs'], [['A',32]] * 3)

    def test_reserved_or_invalid_batch_never_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            for bad in ('FUTURE_001','FUTURE_002','FUTURE_025','FUTURE_000','future_003',''):
                with self.subTest(bad=bad), self.assertRaisesRegex(ValueError,'FUTURE_003_TO_024_ONLY'):
                    batch.plan(work, bad)

    def test_tampered_source_and_plan_refused_before_native_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            original = batch.plan(work, 'FUTURE_003')
            stages.write_new(work / 'RUN558_BATCH_PLAN.json', original)
            installed = work / 'installed'; installed.mkdir()
            changed = copy.deepcopy(original); changed['expected_rows'] = 41
            (work / 'RUN558_BATCH_PLAN.json').write_text(json.dumps(changed))
            with patch('run496_heldout10_native_pilot.verify_installed',side_effect=AssertionError('NATIVE CALLED')):
                with self.assertRaisesRegex(ValueError,'RUN558_BATCH_PLAN_NOT_FROZEN'):
                    batch.execute(work, installed, 'FUTURE_003')
            (work / 'RUN558_BATCH_PLAN.json').write_text(json.dumps(original))
            future = schedule.registration(); future['batches'][2]['stage_ids'][0] = 'C_s31_p00'
            (work / 'RUN504_SCHEDULE.json').write_text(json.dumps(future))
            with self.assertRaisesRegex(ValueError,'FROZEN_FUTURE_SCHEDULE_REQUIRED'):
                batch.plan(work, 'FUTURE_003')

    def test_mocked_three_stage_success_then_no_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stages.write_new(work / 'RUN558_BATCH_PLAN.json',batch.plan(work,'FUTURE_003'))
            installed = work / 'installed'; installed.mkdir()
            with patch('run496_heldout10_native_pilot.verify_installed',return_value={'MOCK':True}), \
                 patch.object(batch,'run_child',side_effect=mock_child) as child:
                result = batch.execute(work,installed,'FUTURE_003')
            self.assertEqual(child.call_count,3)
            self.assertEqual(result['rows_verified'],42)
            self.assertFalse(result['canonical_gate_pass'])
            with self.assertRaisesRegex(ValueError,'REFUSE_BATCH_RERUN_OR_PARTIAL'):
                batch.execute(work,installed,'FUTURE_003')

    def test_second_stage_red_preserves_progress_and_stops_third(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stages.write_new(work / 'RUN558_BATCH_PLAN.json',batch.plan(work,'FUTURE_003'))
            installed = work / 'installed'; installed.mkdir()
            calls = []
            def fail_second(command,log_path,timeout_s=3600):
                sid = command[command.index('--stage-id')+1]
                calls.append(sid)
                if len(calls)==2:
                    Path(log_path).write_text('MOCK_RED_NO_NATIVE\n')
                    return 17
                return mock_child(command,log_path,timeout_s)
            with patch('run496_heldout10_native_pilot.verify_installed',return_value={'MOCK':True}), \
                 patch.object(batch,'run_child',side_effect=fail_second):
                with self.assertRaisesRegex(RuntimeError,'RUN558_STOPPED_AT_A_s32_p02_RC_17'):
                    batch.execute(work,installed,'FUTURE_003')
            self.assertEqual(calls,['A_s32_p01','A_s32_p02'])
            self.assertFalse((work/'stage_A_s32_p03').exists())
            progress = [json.loads(x) for x in (work/'RUN558_BATCH_PROGRESS.jsonl').read_text().splitlines()]
            self.assertEqual(progress[-1]['rc'],17)
            with self.assertRaisesRegex(ValueError,'REFUSE_BATCH_RERUN_OR_PARTIAL'):
                batch.execute(work,installed,'FUTURE_003')

    def test_malformed_receipt_cannot_promote_jepa(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            stages.write_new(work / 'RUN558_BATCH_PLAN.json',batch.plan(work,'FUTURE_024'))
            installed = work / 'installed'; installed.mkdir()
            def bad_receipt(command,log_path,timeout_s=3600):
                rc = mock_child(command,log_path,timeout_s)
                sid = command[command.index('--stage-id')+1]
                receipt = work / ('stage_'+sid) / 'RUN500_STAGE_RESULT.json'
                d = json.loads(receipt.read_text()); d['jepa_weight'] = 1
                receipt.write_text(json.dumps(d))
                return rc
            with patch('run496_heldout10_native_pilot.verify_installed',return_value={'MOCK':True}), \
                 patch.object(batch,'run_child',side_effect=bad_receipt) as child:
                with self.assertRaisesRegex(RuntimeError,'RC_98'):
                    batch.execute(work,installed,'FUTURE_024')
            self.assertEqual(child.call_count,1)

    def test_existing_stage_refused_before_model_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = workdir(tmp)
            p = batch.plan(work,'FUTURE_003')
            stages.write_new(work/'RUN558_BATCH_PLAN.json',p)
            (work/('stage_'+p['stage_ids'][0])).mkdir()
            installed = work/'installed'; installed.mkdir()
            with patch('run496_heldout10_native_pilot.verify_installed',side_effect=AssertionError('NATIVE CALLED')):
                with self.assertRaisesRegex(ValueError,'REFUSE_EXISTING_STAGE_DIR'):
                    batch.execute(work,installed,'FUTURE_003')


if __name__=='__main__':
    unittest.main()
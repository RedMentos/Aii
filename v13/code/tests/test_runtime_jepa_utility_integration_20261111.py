"""Run real source-bound JEPA update/holdout/restart in disposable integrated copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]

def test_integrated_runtime_jepa_holdout_restart(tmp_path):
    builder_path = CODE / 'scripts/stage_integrated_candidate.py'
    spec = importlib.util.spec_from_file_location('world_integration', builder_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stage = tmp_path / 'candidate'
    manifest = module.stage(CODE, stage)
    assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
    (stage / 'tests').mkdir(exist_ok=True)
    for name in ('integrated_jepa_disposable_cases.py','integrated_online_world_disposable_cases.py'):
        shutil.copy(CODE / 'tests' / name, stage / 'tests' / name)
    shutil.copy(CODE / 'tests/runtime_jepa_utility_disposable_cases_20261111.py',
                stage / 'tests/runtime_jepa_utility_disposable_cases_20261111.py')
    env = dict(os.environ, PYTHONPATH=str(stage) + os.pathsep + str(stage / 'tests'))
    command = [sys.executable, '-m', 'pytest', '-q', '-s',
               'tests/runtime_jepa_utility_disposable_cases_20261111.py']
    result = subprocess.run(command, cwd=stage, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'JEPA_HOLDOUT' in result.stdout
    print(result.stdout)


from test_v14_world_jepa_postcommit_runtime import (
    test_sleep_runtime_postcommit_requires_observed_outcome_and_keeps_gates_default_off as _postcommit_default_off,
    test_sleep_tick_schedules_one_authorized_idle_batch_and_coalesces_turn_bursts as _postcommit_idle_schedule,
    test_sleep_jepa_job_runs_real_postcommit_consumer_and_persists_completion as _postcommit_job,
    test_sleep_jepa_job_requeues_one_bounded_continuation_when_more_t8_rows_exist as _postcommit_continuation,
    test_sleep_runtime_postcommit_updates_world_jepa_ema_replay_and_planner_with_restart_rollback as _postcommit_numeric_learning,
    test_planner_refuses_censored_action_outcomes_even_when_they_are_terminal as _postcommit_censored_negative,
    test_runtime_idle_tick_enqueues_world_jepa_into_normal_sleep_queue as _postcommit_runtime_queue,
    test_learning_gate_reenable_retries_shadowed_t8_event as _postcommit_gate_reenable,
    test_cancelled_store_backed_world_jepa_fit_is_atomic_and_retryable as _postcommit_cancel,
)

def test_sleepruntime_postcommit_default_off_and_source_gate(tmp_path):
    _postcommit_default_off(tmp_path)

def test_sleepruntime_postcommit_idle_scheduler_and_coalescing(tmp_path):
    _postcommit_idle_schedule(tmp_path)

def test_sleepruntime_postcommit_job_consumes_persisted_t8(tmp_path):
    _postcommit_job(tmp_path)

def test_sleepruntime_postcommit_bounded_continuation(tmp_path):
    _postcommit_continuation(tmp_path)

def test_sleepruntime_postcommit_numeric_learning_replay_restart_rollback(tmp_path):
    _postcommit_numeric_learning(tmp_path)

def test_sleepruntime_postcommit_censored_negative_control(tmp_path):
    _postcommit_censored_negative(tmp_path)

def test_sleepruntime_postcommit_runtime_queue_delivery(tmp_path):
    _postcommit_runtime_queue(tmp_path)

def test_sleepruntime_postcommit_gate_reenable_after_shadow(tmp_path):
    _postcommit_gate_reenable(tmp_path)

def test_sleepruntime_postcommit_cancelled_fit_is_atomic(tmp_path):
    _postcommit_cancel(tmp_path)

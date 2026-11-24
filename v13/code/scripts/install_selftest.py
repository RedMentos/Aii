#!/usr/bin/env python3
"""Bounded model-free first-install smoke; NOT the full developer selftest.

This runs a fixed list of existing real V13 tests in a separate process.
It proves software invariants only: no GGUF/Needle execution, learning utility,
Redmi performance, STEP2/B3/JEPA or age-gate promotion.
"""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest

APP = Path(__file__).resolve().parents[1]
TESTS = APP / "tests"
MAX_SECONDS = 120

# Exact methods, not file patterns: adding a new expensive test cannot silently
# make a first install execute the 4907-test developer suite.
SMOKE_CASES = (
    "test_age.AgeChecks.test_default_build_stays_age0_but_records_proposal",
    "test_age.AgeChecks.test_user_cap_is_binding_and_not_self_overridable",
    "test_age.AgeChecks.test_rights_are_masked_by_rules_permissions_resources_and_structural_lock",
    "test_age.AgeChecks.test_user_freeze_and_lower",
    "test_age.AgeChecks.test_restart_persists_state",
    "test_age_rights.AgeStageChangesAllowedPaths.test_age_stage_changes_allowed_paths",
    "test_runtime_queue.DurableRuntimeQueue.test_paused_restart_preserves_pending_fifo_and_no_duplicate_outputs",
    "test_runtime_queue.DurableRuntimeQueue.test_restart_queue_expiry_is_visible_and_never_generates_late_answer",
    "test_runtime_queue.DurableRuntimeQueue.test_failed_turn_is_terminal_and_following_real_source_copy_runs",
    "test_standstill.EngageTests.test_all_parts_stop_and_idle_runtime_is_confirmed_still",
    "test_standstill.RestartTests.test_restart_stays_still",
    "test_standstill.ReleaseTests.test_user_notaus_before_standstill_survives_release",
    "test_source_handoff_candidate.SourceHandoffCandidate.test_relevant_prior_quote_delivered_without_unselected_prior_text",
    "test_source_handoff_candidate.SourceHandoffCandidate.test_rejected_and_own_state_quotes_never_gain_verified_delivery",
    "test_source_handoff_candidate.SourceHandoffCandidate.test_deleted_and_corrupted_prior_source_fail_closed",
    "test_source_handoff_candidate.SourceHandoffCandidate.test_mutable_offer_and_wrong_turn_cannot_change_consumer_evidence",
    "test_source_handoff_candidate.SourceHandoffCandidate.test_exact_integrated_candidate_is_accepted_but_mixed_or_tampered_sources_reject",
    "test_admission.AdmissionTest.test_labels_come_only_from_human_signals",
)

# New exact cohort for current Run102 Runtime; legacy_run97 remains immutable.
SMOKE_CASES_RUN102_C3 = (
    "test_age.AgeChecks.test_default_build_stays_age0_but_records_proposal",
    "test_age.AgeChecks.test_user_cap_is_binding_and_not_self_overridable",
    "test_age.AgeChecks.test_rights_are_masked_by_rules_permissions_resources_and_structural_lock",
    "test_age.AgeChecks.test_user_freeze_and_lower",
    "test_age.AgeChecks.test_restart_persists_state",
    "test_age_rights.AgeStageChangesAllowedPaths.test_age_stage_changes_allowed_paths",
    "test_runtime_queue.DurableRuntimeQueue.test_paused_restart_preserves_pending_fifo_and_no_duplicate_outputs",
    "test_runtime_queue.DurableRuntimeQueue.test_restart_queue_expiry_is_visible_and_never_generates_late_answer",
    "test_runtime_queue.DurableRuntimeQueue.test_failed_turn_is_terminal_and_following_real_source_copy_runs",
    "test_standstill.EngageTests.test_all_parts_stop_and_idle_runtime_is_confirmed_still",
    "test_standstill.RestartTests.test_restart_stays_still",
    "test_standstill.ReleaseTests.test_user_notaus_before_standstill_survives_release",
    "test_b2_c3_context_plan_20261031.C3ContextOSB2Evidence.test_wide_exact_prior_rules_survive_c3_legacy_and_planned_view",
    "test_b2_c3_context_plan_20261031.C3ContextOSB2Evidence.test_narrow_c3_view_contains_only_selected_prior_sentence",
    "test_b2_c3_context_plan_20261031.C3ContextOSB2Evidence.test_deleted_prior_ref_cannot_enter_context_plan",
    "test_context_os.PlanTests.test_append_only_does_not_replay_revoked_volatile_memory",
    "test_context_os.PlanTests.test_append_only_does_not_replay_rewritten_source_history",
    "test_admission.AdmissionTest.test_labels_come_only_from_human_signals",
)
# New optional 21-case integration cohort. The two registered 18-case cohorts,
# including their exact order and default, remain byte-identical.
SMOKE_CASES_RUN104_C3_C5_EXIT = SMOKE_CASES_RUN102_C3 + (
    "test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_six_source_bound_local_drafts_survive_restart",
    "test_jef_c3_c5_c6_operator_cli.JefC3C5C6OperatorCliTests.test_native_missing_pinned_model_refuses_before_human_records",
    "test_step2_exit_gate_split_20261031.Step2ExitGate.test_exit_is_explicitly_red_and_all_graph_deps_remain_known",
)
COHORTS = {"legacy_run97": SMOKE_CASES, "run102_c3": SMOKE_CASES_RUN102_C3,
           "run104_c3_c5_exit": SMOKE_CASES_RUN104_C3_C5_EXIT}


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def load_exact_suite(names=SMOKE_CASES):
    """Fail closed if a test is missing, renamed, duplicated or imported elsewhere."""
    names = tuple(names)
    if not names or len(set(names)) != len(names):
        raise ValueError("empty or duplicate install-smoke allowlist")
    for folder in (APP, TESTS):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(names)
    actual = list(_flatten(suite))
    if len(actual) != len(names):
        raise ValueError("install-smoke count changed")
    for expected, test in zip(names, actual):
        if (not isinstance(test, unittest.TestCase)
                or type(test).__name__ == "_FailedTest"
                or test.id() != expected):
            raise ValueError("install-smoke missing or substituted test: " + expected)
        module = importlib.import_module(type(test).__module__)
        if Path(module.__file__).resolve().parent != TESTS.resolve():
            raise ValueError("install-smoke test outside pinned tests directory")
    return suite


def worker(cohort='legacy_run97'):
    os.environ["NO_MODEL_DOWNLOADS"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    try:
        names = COHORTS[cohort]
        suite = load_exact_suite(names)
    except (ValueError, ImportError, AttributeError) as exc:
        print("INSTALL_SELFTEST_REFUSED: " + str(exc), file=sys.stderr, flush=True)
        return 2
    print("INSTALL_SELFTEST_SCOPE=MODEL_FREE_SOFTWARE_ONLY; full developer suite remains 'v13 selftest'",
          flush=True)
    print('INSTALL_SELFTEST_COHORT=' + cohort, flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("INSTALL_SELFTEST_RESULT tests={} expected={} failures={} errors={} skipped={}".format(
        result.testsRun, len(names), len(result.failures),
        len(result.errors), len(result.skipped)), flush=True)
    return 0 if result.wasSuccessful() and result.testsRun == len(names) else 1


def run_bounded(seconds=MAX_SECONDS, cohort='legacy_run97'):
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError("install-smoke timeout must be between 1 and 120 seconds")
    if cohort not in COHORTS:
        raise ValueError('unknown install-smoke cohort')
    env = os.environ.copy()
    env.update(NO_MODEL_DOWNLOADS="1", DO_NOT_TRACK="1", V13_INSTALL_SMOKE="1", V13_INSTALL_SMOKE_COHORT=cohort)
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", "--cohort", cohort]
    process = subprocess.Popen(cmd, cwd=str(APP), env=env, start_new_session=True)
    try:
        code = process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            process.kill()
        process.wait()
        print("INSTALL_SELFTEST_TIMEOUT: worker terminated after {}s".format(seconds),
              file=sys.stderr, flush=True)
        return 124
    if code == 0:
        print("INSTALL_SELFTEST_PASS: {} exact model-free cases; NOT a native/Redmi gate".format(
            len(COHORTS[cohort])), flush=True)
    else:
        print("INSTALL_SELFTEST_FAIL: worker exit {}".format(code), file=sys.stderr, flush=True)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=MAX_SECONDS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument('--cohort', choices=sorted(COHORTS), default='legacy_run97')
    args = parser.parse_args(argv)
    if args.worker:
        return worker(args.cohort)
    try:
        return run_bounded(args.timeout_seconds, args.cohort)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())

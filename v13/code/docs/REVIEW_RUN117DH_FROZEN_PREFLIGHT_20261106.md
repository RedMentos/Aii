# Run117DH: historical Run34/Run37 preflight tests (2026-11-06)

Base: `7bf3557bf5a94c6860285be7137c7da714c77995` on
`assistant/v13-run117dh-independent-native-replay-20261101-hourly11`.
This is a local, test-only review candidate. It does not replace any original
result or indicate a full-suite, native, Redmi, or scientific-gate pass.

## Observation and source

Before the change, the two focused modules ran 11 tests with two errors:
the Run34 and Run37 `test_pinned_source_model_runner_and_negative_gates`
both raised `native_source_or_catalog_changed`. The historical Run34
preflight expects utility Git blob `f4a92dab9c4a40761d64394cdca1c052e9a76bfd`;
the current utility is `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53`.
The catalog, Run33 source, and runner match their existing pins. Refusal of
the current utility by the historical preflight is correct; no pin has been
updated. This matches the Run117CT Actions log for run `41260851541`, which
reported 5,445 tests, two errors, and 28 skips. The original run remains RED;
its artifact was not independently verified in this local review.

The test correction is adapted from [PR #1459](https://github.com/RedMentos/Aii/pull/1459),
whose Run94 branch is independent of this one. It asserts genuine rejection
of the current utility, then simulates only the old utility *hash* to check
historical preflight metadata. That mock is not historical execution or native
readiness. The prior separate historical-worktree comparison described in
[PR #1137](https://github.com/RedMentos/Aii/pull/1137) reported 11/11 passing
against the original utility blob; it was not rerun here.

As an additional counterexample, the new focused test copies the registered
catalog, Run33, runner, and current utility to a temporary directory. With
only the utility hash simulated as historical, it first checks the metadata,
then actually modifies each of the three other copied files in turn. Both
Run34 and Run37 `_run_unlocked` calls must refuse each edit before constructing
a runner or creating evidence. No project runtime file is edited. Because the
tests deliberately assert the current utility blob, a later legitimate utility
change requires review of this expectation; it must not silently repin the
historical native cohort.

## Local verification

Commands were run from `v13/code`, without model downloads or native inference:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:scripts \
V13_NO_AUTOSTART=1 NO_MODEL_DOWNLOADS=1 python -m unittest -v \
  tests.test_run34_c3_native_quote_intervention_pilot \
  tests.test_run37_c3_rule_use_native_pilot
```

Before: 11 tests, 2 errors. After: **12 tests, OK**.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:scripts \
V13_NO_AUTOSTART=1 NO_MODEL_DOWNLOADS=1 python -m unittest -v \
  tests.test_run83_native_driver_fake_c3 tests.test_run52_b1b2_cross_turn \
  tests.test_run34_c3_native_quote_intervention_pilot \
  tests.test_run37_c3_rule_use_native_pilot
```

Result: **18 tests, OK**. An earlier attempt also named
`tests.test_run90_exact_route_lineage`, as used by PR #1459; that file does
not exist on this branch, so the attempt had 18 passing tests and one module
import error. It was not a full-suite result.

Original native scripts, runtime sources, hashes, model/seed/cohort pins,
and raw evidence remain unchanged. STEP2 remains `UTILITY_FAIL`, B3 has no
promotion, Body-JEPA remains unavailable, `jepa_weight=0`, Redmi is unmeasured,
and the whole system is incomplete. Full unfiltered Run117DH testing is still
needed with its registered original artifact prerequisites.

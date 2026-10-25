# Run391 / AG2 preaction restart reconciliation (2026-10-26)

Independent opt-in AG2 lifecycle package stacked on verified Run390/PR385 checkpoint `b60a5af368eec7d989da1a2c902e80c0bdb1b61d` (not main). File ownership: `v13/code/v13/agi/tools.py`, `v13/code/v13/agi/grounding_preaction.py`, new `tests/test_ag2_preaction_recovery_run391.py`, isolated workflow, this proof directory. Do not edit Run389 or Run390 files, registered cohorts, source/model/seed hashes, or default Growth wiring.

**Problem.** Run388 records an AG2 prediction before a tool effect, but the expectation does not contain the durable ActionTransaction ID. A process crash after the SQLite action copy or after the terminal action commit but before the post-action hook leaves an orphan `G2_GROUNDING.open` record. Blindly inferring an outcome from a running/UNKNOWN/CANCELLED action would fabricate causal training evidence; dropping every completed outcome wastes verifiable feedback.

**Preregistered RED checks (before production edits).**
1. Before the actual effect, the opt-in AG2 expectation must carry the exact durable `action_tx` ID, with transaction already COPY_COMMITTED/EXECUTING and matching tool+args.
2. Explicit `PreActionGrounding.reconcile()` (not automatically wired into active Runtime) may close a pre-existing open expectation from the matching durable SUCCEEDED/FAILED transaction only when it is an operator action or its assistant turn is FINAL. Outcome labels map SUCCEEDED→EXECUTED and FAILED→FAILED with the durable result; no invented effect.
3. UNKNOWN/CANCELLED are discarded with **zero** frequency/closed/error updates. PREPARED/COPY_COMMITTED/EXECUTING are deferred, never assumed completed; the existing `Transactions.recover()` owns crash transition. A missing or mismatched durable ID/source, or non-FINAL terminal turn, must not create learning evidence.
4. Recovery must be bounded to the existing AG2 open history, idempotent on repeated calls, and must not rerun any tool or change user permissions/age. Legacy ToolRegistry without preaction hooks must remain unchanged.
5. Test direct Runtime/SQLite with simulated post-commit lost callback, crash UNKNOWN and turn finality. Run inherited Run388 AG2/G10 tests, compileall/privacy.

**Workflow:** pinned Ubuntu 24.04, isolated numpy/prompt-toolkit, no models/cloud, exact-head checkout, raw test/identity/privacy logs and SHA256 manifest, Actions artifact. Enforce RED and retain raw before code edit, then GREEN. Evidence source-only synthetic crash simulation; no real SIGKILL or Redmi native claim.

**Negative gates:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Run389 full suite RED (3160 tests: 1 fail, 70 errors), Age0/approval unchanged, no active Growth opt-in, no native/Redmi, whole V13 incomplete. Independent review required before integration. Next after GREEN: optional opt-in end-to-end FINAL/CANCELLED settlement proof; do not enable by default.

# AG6 source revocation between training and human approval — prereg (2026-10-29)

Review-only child of PR #1125 exact parent `c2347b437c07faae7273577742219eaefdbea107`; owner only this child branch, `v13/code/v13/agi/weights.py`, `v13/code/tests/test_ag6_approval_source_revocation_20261029.py`, scoped CI and this prereg. Do not mutate parent, frozen cohorts or historical gates.

## Independent defect hypothesis

PR #1125 rechecks direct staged SourceRefs **before trainer.fit**, but `WeightConsolidation._approve_locked` later checks drift, request and artifact only. A human can revoke the underlying source after training and before the separate explicit approval; the old code still publishes the adapter and marks the batch APPROVED. Manual approval of a *candidate* does not override a previously revoked source. The Store uses a reentrant mutex around `_approve_locked` and SQLite writes; rechecking direct refs inside the initial approval transaction can prevent a concurrent local revocation from interleaving.

## Predeclared real-Store tests

1. Build a real STAGED → TRAINED → PENDING_USER batch from a user memory with authored FakeLora (no model weights), then mark its exact source `deleted=1`. `approve` must refuse; batch stays PENDING_USER, request stays PENDING, no consolidated memory or active adapter/mirror. Original expected RED.
2. Same valid batch without revocation must still approve, with exactly the existing manual approval and rollback behavior.
3. Malformed staged source ref after PENDING_USER must not activate; original expected RED.
4. Run inherited approval atomicity tests and the stage-to-fit source recheck tests; no change to Age0 learning mode or request/activation semantics.

## Narrow candidate and proof

In `_approve_locked` while Store.mutex and initial SQLite transaction are held, validate every persisted batch item direct `source_ref` via `Store.read_source`. Fail closed with ValueError **before** creating ACTIVATING intent; do not mutate request or adapter registry on refusal. Keep existing approval atomics, manual permission and rollback. This is not a proof of answer-dependency revocation after staging or a general anti-tamper guarantee for mutable rating metadata. Preserve first original RED, candidate focused/full logs, raw hashes and failed attempts.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, AG6 unapproved, V13 incomplete.

# Run14S — AG6 gate-time live-source and holdout re-admission (preregistered)

2026-10-30 UTC. Owner GPT-6 scheduled continuation. Review-only child of Run14R PR #1334 exact `7379befc9c475988f25a44771652449cbda3418f`. Own `v13/code/v13/agi/weights.py`, `v13/code/tests/test_ag6_gate_readmission_run14s.py`, Run14S docs/workflow. Do not touch parent PR, shared review files or active model/native cohorts.

## Concrete request-time gap

Run14R rechecks AG12 holdouts at stage, immediately pre-fit, and both human-approval transactions. But `WeightConsolidation.gate` currently inserts a `WEIGHT_CONSOLIDATION` human approval request in the same transaction without rechecking source/holdout admissibility. A source may be revoked, or an AG12 EN/DE unseen suite may be registered, after fit and before gate. The eventual `approve` rejects, but the user is still asked to approve an inadmissible candidate. Correct behavior is to avoid the request and mark the immutable batch invalid at gate-time.

## Frozen tests

1. Stage a source-bound human fact, fit via FakeLora test seam to `TRAINED`, then register a fresh EN seed17 unseen prompt matching that fact. `gate` must return `SOURCE_INVALID` with no request and no consolidation. Original code expected RED (creates PENDING_USER).
2. Same after registering a fresh German seed17 unseen prompt. No English/German curve or seed mutation by AG6.
3. Revoke the staged source after fit but before gate; `gate` must not create a request and must persist `SOURCE_INVALID`.
4. Corrupt the registered historical holdout union after fit; gate fails closed with no request.
5. A valid source, unchanged holdout registry and valid synthetic measured gate still produces `PENDING_USER` (not auto-approval). Existing AG6 request atomicity, source revocation, Run14P/Q/R and AG9 tests remain green.

Implementation: inside the **same SQLite write transaction** that would create the request, revalidate current batch source refs and the read-only AG12 registered EN/DE union; on invalid state move to existing `SOURCE_INVALID` with a bounded reason, do not write a request and do not emit positive neuromodulator signal. No model training, no age promotion. Preserve original negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, V13 incomplete. Historical unfiltered suite RED unwaived.

Parent pins: Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; AG6 `2ea853c8517674f22bc551b361a8d96b9c89c9f5`; AG12 `84ca3580c37a00701286d0d9b00d535ee8c3153f`.

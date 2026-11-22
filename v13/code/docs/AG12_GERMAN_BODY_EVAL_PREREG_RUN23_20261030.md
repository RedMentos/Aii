# Run23 preregistration — explicit German AG12 real-body evaluation (2026-10-30)

Owner: GPT-6 scheduled continuation. Exact review parent Run22 PR #1349 head `018c3fc875de36690545ec31731b0968a0e22466`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Functional gap
AG12 already has German deterministic suites and a read-only EN/DE comparison, but `:growth eval run c3|b1|b2|v13` and scheduler/BodySolver always use `growth.eval` (English). Thus an operator cannot collect a German **real-body** evaluation through the normal bounded route. Existing AG9 code even anticipates `ag12:<solver>:de`, but cannot receive German results from that route.

## Scope and predeclared behavior
Add explicit `:growth eval run de <c3|b1|b2|v13>` scheduling, without changing the legacy English payload or default. The scheduled USER event carries `lang=de`, and the native BodySolver uses the existing pinned German AG12 suite (seed inherited from the active English eval) with the same JSON-answer grammar, no memory/tools and bounded resident body sequence. A German run writes only the German G12 state and `generality-last-de.json` export; AG9 calibration uses `ag12:<solver>:de` with in-memory exact-row validation. English runs remain byte-compatible in schedule payload and use the original suite/AG9 component. Reject unknown languages, prevent SYSTEM-origin German runs without a USER event, and do not initialize the German suite if no model is installed.

Test first with a fake native RunnerPool (no native model claim) against real Runtime/SQLite: 88/88 German model-answer calls, explicit scheduler payload, AG9 German calibration, restart/EN isolation, no holdout prompt persisted as chat/event, negative cancel/NO_SOLVER/invalid-origin, and EN+DE comparison via Run22. Existing `tests.test_agi_solver` and `tests.test_growth` must stay green.

## Claim limits
Fake runners prove software wiring only. No actual German quality, transfer learning, Body-JEPA, STEP2 utility, B3, jepa_weight, Redmi or production promotion. All Age0 RECORD_ONLY and approvals remain. Actual pinned Linux-native/Redmi German runs require real installed models and separate evidence.

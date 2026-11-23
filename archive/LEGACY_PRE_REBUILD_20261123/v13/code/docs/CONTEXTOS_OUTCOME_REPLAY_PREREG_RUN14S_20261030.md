# Run14S — Context OS outcome replay integrity preregistration (2026-10-30)

Parent: Run14R PR #1334, exact head `7379befc9c475988f25a44771652449cbda3418f`. Owner: GPT-6 scheduled continuation. Scope: `v13/code/v13/context_os.py`, `v13/code/tests/test_context_os.py`, new `v13/code/tests/test_context_os_outcome_replay_run14s.py`; no runtime/registered cohort/model/Canon edits.

## Observed gap and test-first claim

`ContextOS.outcome(event_id, utility)` currently applies every repeated call for the same event to the learned context-policy prior and sends another neuromodulator signal. A single operator rating can therefore be replayed to manufacture the minimum 3 observations needed to enable learned ACTIVE, including after restart. This is a causal evidence integrity bug, not measured model utility.

Hypothesis: an atomic persisted bounded event receipt inside the existing ContextOS state makes an exact event replay a no-op (including after restart), while distinct events remain independent and recently observed out-of-order ratings are accepted. Once the bounded receipt window evicts old event IDs, a monotonically advanced SQLite event-rowid floor must reject stale unrecognized events instead of permitting replay. No change to human ACTIVE approval, SHADOW default, policy update math, native inference, age or model weights.

## Frozen tests before implementation

1. One event with a compression decision and three identical outcome calls increments policy `n` once, not three times; no extra signal.
2. Restarted ContextOS reading the same SQLite state cannot credit the same event again.
3. Three *distinct* context plans and ratings yield `n=3` and preserve learned SHADOW gating; ACTIVE remains explicit human only.
4. Out-of-order recent event ratings are accepted once each; once a bounded window evicts a very old event, replay fails closed.
5. Existing ContextOS, operator, cache observation, source-exact, and AG12/AG6 tests must not regress. Original prepatch RED and candidate GREEN are recorded separately, without waiver.

Evidence level: real SQLite/software only. Never promote STEP2, B3, Body-JEPA, jepa_weight or V13 completion from this package. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured. Historical full-suite RED unwaived. No private content in public repository.

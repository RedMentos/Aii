# Core handoff — C3 recovery reserve contract in same-turn B1/B2 scheduling

Date: 2026-11-22
Role: Core & Harness
Branch: `core/v14-c3-recovery-reserve-contract-20261122`
Base: Boss integration PR #2370 exact head `ebe1bec4df6033e619cf145eb9899572dcb5849b`
Comparison at checkpoint: 1 commit ahead / 0 behind.

## Problem found

The staged Runtime acceptance had contradictory expectations for the same 30-second turn after two observed C3 zero-token prefill deadlines:
- `native_turn_budget.plan` defines a 26-second C3 recovery reserve; the unit contract in `test_same_turn_body_delivery_qa.py` already expects 26 seconds.
- `observer_fair_budget_disposable_cases_20261116.py` incorrectly expected the ordinary 16.5-second reserve and 6.75/13.5-second observer endpoints even while asserting that recovery was active.
- With recovery active, only 4 seconds remain for pre-answer B1/B2. The sequential observer must cap the first body at 2 seconds and the second at the remaining 2 seconds (or less if the first body consumes its slice early); C3 retains the 26-second reserve.
- A prior exact run on head `bae7d031`, workflow `45077837118`, also exposed an obsolete monkeypatch path to `v13.native_turn_budget.time`; the current unit test already patches the actual clock owner `v13.cognition.time.monotonic`.

## Change

Only the Core-owned staged Runtime acceptance file is changed:
- Recovery unit examples now pass the turn-start clock and assert a 26-second C3 reserve, a 4-second total pre-answer cap, and a 2.75-second capped first slot.
- The end-to-end Runtime/SQLite test now expects 26 seconds reserved for C3 and verifies the sequential body deadlines at +2s and +4s. It still requires both source-bound OfferPackets to reach C4/C3 in the same turn, with their exact source quotes in the C3 prompt.
- No runtime code, native models, Age policy, learning rights, B3 authority or model selection is changed.

## Local evidence

- LOCAL_LINUX CPython 3.13.5: the exact `native_turn_budget.plan` policy was reproduced with two C3 prefill failure rows. PASS: reserve=26.0s, pre-answer end=+4.0s, first-slot cap=+2.75s.
- The changed assertion block compiles. This is a local synthetic policy check, not a full Runtime test.
- Full Aii checkout/pytest: BLOCKED / NOT_RUN; no checkout is mounted and GitHub DNS resolution fails.
- Parent Boss head `ebe1bec4df6033e619cf145eb9899572dcb5849b`: current exact-head CI has 1 completed success (A5 UI lease), several completed successes, and Core same-turn/staged integration workflows queued; no current-head pass is claimed for the affected test.
- TERMUX/REDMI: REDMI_UNVERIFIED. No device probe, model change, permission change or update was performed.

## Next action

Run exact PR-head Core same-turn and staged/integrated workflows. If the corrected acceptance still fails, inspect the real Runtime clock/valid-until wiring before changing the reserve policy. Keep this PR stacked on #2370; do not merge or claim a Redmi speed improvement from synthetic scheduling tests.

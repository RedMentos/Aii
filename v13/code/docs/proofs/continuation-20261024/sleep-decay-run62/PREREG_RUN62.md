# Run62 prereg — Sleep C elapsed-time trace decay, production-bound bug fix

Date 2026-10-24. Immutable base 7849f756fbf5da3f3bc7e279fd01c163c3f1a505 (Run61 prereg; PR94 Run60).
Owner: `v13/code/v13/sleep_trace_decay.py`, a minimal integration diff in `v13/code/v13/sleep.py`, `v13/code/tests/test_sleep_trace_decay.py`, and `v13/code/docs/proofs/continuation-20261024/sleep-decay-run62/*`. Do not edit Run61-owned history files, frozen model/STEP2 fixtures or any native job.

Observed code defect before tests: `SleepCycle.sleep_c` repeatedly multiplies priority by `trace_decay_per_day ** ((now - (last or created))/DAY)`, using the original timestamp at every tick. Multiple Sleep C runs at the same wall time therefore decay the same trace repeatedly, not once per elapsed day. This can distort §94.4 homeostatic replay and §67 priority; fix without changing user authority or replay selection contracts.

Proposed isolated production-importable pure function: validate finite inputs, compute decay from max(last-or-created, last-decay watermark), return a staged priority and watermark; no side effects, no fact writes, no weight writes. Existing schedules without a watermark use the old source anchor exactly once; previously compounded history cannot be reconstructed. Sleep C should stage/validate the entire batch before mutating it. Clock rollback must not decay or rewind the watermark. An existing replay last timestamp may supersede the decay watermark. Priority must never increase due to floor.

Predeclared software tests: same-time idempotence, 24 hourly vs 1 daily decay, replay timestamp supersedes, backwards clock, floor, malformed/nonfinite refusal, legacy schedule compatibility, batch validation no partial mutation, and one actual SleepCycle callsite integration in a full checkout. Preserve before/after reproduction and Python -O. No native/model/Redmi or canonical gate promotion.

STEP2=UTILITY_FAIL; B3 L1=FAIL; Body-JEPA=UNAVAILABLE; jepa_weight=0; full V13=INCOMPLETE. This patch is not an answer-quality or learning utility claim.

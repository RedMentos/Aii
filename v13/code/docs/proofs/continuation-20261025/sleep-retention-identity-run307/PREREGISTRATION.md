# Run307 — Sleep A retention probes must credit the exact human correction (2026-10-25)

Owner GPT-6 automation; base verified Run306 checkpoint `a7c4193f9e53b742adaec13dcf9f42c4a807544a`. Owned `v13/code/v13/sleep.py`, new `tests/test_sleep_retention_identity_run307.py`, dedicated CPU CI, this scoped proof. Independent of Run303 Budget, Run297 native Context OS, Runtime/Store/Model owners.

## Observed actual Runtime/Store defect

`SleepCycle._probe` currently marks a particular active memory as successfully recalled if **either its memory ID appears or any other recalled memory has the same value** (`m['id'] in ids or m['value'] in values`). With two distinct source-bound human corrections from one event sharing the same answer value and `memory_top_k=1`, only one correction is actually retrieved; the other incorrectly receives a PASS. Reproduced using extracted Run305 exact source and actual SQLite. Sleep A can then increment retention PASS/reps despite a missed correction, masking a retrieval regression. This is not a model accuracy or native proof.

## RED-first acceptance tests

1. Two active, valid, independently source-bound F5 corrections for the same original user event, different cue keys but identical value. With actual `Memory.recall` and `memory_top_k=1`, one ID is absent. `_probe` must mark **that ID** `RECALL_MISS:<id>`, return FAIL, and include one failed check. Original code is expected to fail.
2. The same real replay item through `SleepCycle.sleep_a` must produce `failed=1, passed=0`, `reps=0, failures=1`, never false retention credit; no native/weight authority.
3. With `memory_top_k=2`, both distinct IDs are actually retrieved and probe passes. With a single correction, the original PASS path stays unchanged. Existing Sleep, source-lineage, replay, forget, retention tests remain green.
4. Original F5 provenance and source revocation checks remain in place; no value-only cross-correction substitution. No change to replay queue, sampling, sleep policy, memory indices, model/seed/Canon or approval gates.

Minimal expected fix after RED: require **exact memory ID membership** for each recallable correction in `SleepCycle._probe`; keep source/value equality check as an independent provenance test, not as retrieval evidence. Scope software SQLite only, no native/Redmi or STEP2/B3/Body-JEPA/jepa_weight/full-system promotion.

Exact next command: commit RED tests and dedicated CI, observe failures, apply one-line fix in `sleep.py`, run existing Sleep/Memory regressions and privacy, retain closed raw and durable checkpoint, then continue a different Canon package.

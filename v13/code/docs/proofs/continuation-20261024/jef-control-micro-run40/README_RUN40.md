# V13 Run40 — JEF/C2 synthetic multi-head control objective: **FAIL_SYNTHETIC**

Parent PR #75 `195876c930eb93e1d509c4a577f330e55a6ebc71`. Preregistration committed first at `70d210eb0472ba66b80b15718ef0fa06380546ee`. Exact Canon §3.4.6–3.4.9, §13H, §14.2. File ownership only `v13/code/docs/proofs/continuation-20261024/jef-control-micro-run40/`.

## Implemented

CPU PyTorch synthetic JEF/C2 ObjectiveAdapter with four separately trainable heads: route (direct/detail/gist/both), wake, halt and report. Shared 6→32 feature network, deterministic frozen synthetic outcome labels, eligibility-weighted CE/BCE loss, 512 train/128 heldout, 200 steps, seed 20261024, same minibatch order for candidate and shuffled-label control. SHADOW proposals only; hard report gate blocks missing source, conflict and resource pressure regardless of learned probability. No Age action authority, no production model, no C3/Body update.

## Preregistered results — failure retained

8/9 tests PASS; **one preregistered acceptance test FAIL**. Candidate route accuracy 1.000, report Brier 0.000002545, four heads updated, deterministic replay and hard report gates PASS. **Wrong-label control accuracy 0.625 > preregistered maximum 0.500**. The heldout route class is imbalanced: 80/128 = 0.625 are `direct`, exactly matching wrong-target control accuracy. This is not evidence of a learned route in the negative control; the threshold was improperly absolute rather than majority-baseline-adjusted. Per preregistration the original Run40 result remains **FAIL_SYNTHETIC**, not retroactively passed. Raw failed test, metrics and class distribution retained.

## Next

Independently preregister a class-balanced or majority-adjusted negative control in a **new** cohort; do not alter Run40 criterion. Extend JEF learning to grounded real outcomes only with provenance/permission gates. This is no native JEF, no actual generated-answer utility, no Redmi, no full suite/privacy scan. All original gates remain STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Z6a FAIL; Z8 FAIL; full V13 INCOMPLETE.

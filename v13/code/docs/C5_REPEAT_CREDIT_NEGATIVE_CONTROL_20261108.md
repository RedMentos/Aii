# C5 repeated-event credit — isolated negative-control checkpoint (2026-11-08)

Base: PR #1602 head `e5d9e925e7f61c90ee3d64a43badba28c5966a8a`. Own branch `codex/c5-repeat-credit-negative-control-20261108`. No frozen runtime, schema, age, model, cohort or gate changed.

## Source-grounded finding
In `v13/code/v13/actionlearn.py`, `C5Learning.learn(ctx, action_id, event_id, **mods)` increments `q['n']` on every call, without an event identity check. `MIN_N=3` is a sample-count threshold for nonzero learned shifts. Three deliveries of the same positive rating can therefore satisfy the threshold. A corrected rating of the same event also retains the earlier positive running mean while adding a negative one. This is not evidence from three independent outcomes.

The added executable test `tests/test_c5_repeat_credit_negative_control_20261108.py` asserts the *existing unsafe behavior* as a regression/negative control. A PASS means the bug is reproduced, **not** fixed. It uses a versioned in-memory state stub and the real `C5Learning` implementation; it does not modify or activate the frozen runtime. No native model is involved.

## Verification status
GitHub source inspected: `v13/code/v13/actionlearn.py` blob `98d2378cf213be32ee0ad0fb6891c244279f6f0b`, from `codex/resume-20261106`. PR #1602's review notes independently identify the same problem. The new test was committed and remote readback is required. **Repository test execution has not been performed in this checkpoint**; do not call it passing.

Command from `v13/code` on this branch:
```
PYTHONPATH=. python -m unittest -v tests.test_c5_repeat_credit_negative_control_20261108
```
If the test package layout does not support module import, use:
```
PYTHONPATH=. python -m unittest discover -s tests -p 'test_c5_repeat_credit_negative_control_20261108.py' -v
```

## Required fix before C5 activation
A source-bound candidate must bind credit to a stable (event_id, action, feedback identity/revision, provenance) ledger. Duplicate delivery must be idempotent, a corrected rating must replace or compensate its predecessor, and multiple genuinely independent signals from one event must remain distinguishable. The ledger must survive restart and concurrency, and existing aggregate-only state must be quarantined or migrated without inventing historical provenance. Add tests for restart, duplicate retry, correction, different events, concurrent writers, mixed typed/legacy packets, dream-source rejection and Age-0 SHADOW. Compare frozen-original and candidate behavior, independently review and run privacy scan before integration. Existing Neuromod delta/event binding is a separate prerequisite.

No STEP2, B3, Body-JEPA, jepa_weight, C5 ACTIVE or whole-system promotion. The complete Canon remains required.

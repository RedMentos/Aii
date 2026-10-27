# WP-HX1/HX3/HX4 Claude cross-review integration — prereg (2026-10-27)

Review-only child of verified C1+World+B3 seed integration `1ab88aa30947e2f3da9905b1d3055f04b98a8bed`, not main. Source: Claude branch `claude/project-thread-4iqpro`, exact commit `d0d1e2e909cfcacd66c39938853af869978023b2` (2026-10-22), parent `da1217c9b845658fa8cbb831f77ba8d1e72e2038`. Owner GPT cross-review; source/test file ownership restricted to `v13/code/v13/agi/{__init__,self_improve,harness,experience,blind_select}.py`, `v13/code/tests/test_harness_hx.py`, CI and coordination. Do not overwrite newer ROADMAP/HANDOFF or other owners' branches.

## Problem and provenance

HX1 harness proposals (fixed allow-list, explicit human approval and rollback), HX3 evidence-bound experience library and HX4 blind selector were built and tested on Claude's branch but absent from this current C1+World+B3 integration tree. The two overlapping AG8 files `agi/__init__.py` and `agi/self_improve.py` are **byte-identical** in this tree and Claude's parent (blobs `d6a7c7d22aeee6800dd97d556d508f2035409c72` and `04e266e3030b598ced5eb8d1174e8f767559f218`). Therefore copy exactly Claude's six code/test blobs without transplanting stale global docs.

## Falsifiable acceptance

1. Test-only RED: exact `test_harness_hx.py` from Claude fails on this tree because the HX modules are missing; prereg committed first.
2. GREEN: exact source/test blobs from Claude commit, including AG8 kind wiring and SHADOW-only Hub attachment, make HX1/HX3/HX4 tests pass. All protected prompts/operator rules/age/approval controls remain immutable and live harness consumers remain zero. No automatic apply or live prompt replacement.
3. Full software regression, compileall, privacy scan, diff check and raw ZIP all exits0; independent review of changes and source hashes. No model/native/Redmi run.
4. No change to existing STEP2/B3/LP1/LP2/BJ1 negatives, `jepa_weight=0`, Age0, no self-modification authority or whole-system completion. HX2 remains unmeasured and must gate any live consumer. No auto-merge.

After verification, integrate this independent HX review with the current all-gates chain in a separate review candidate. Keep private raw backup and exact next command.

# Run176 — optional developer fixture permission portability (2026-10-25)

Owner: `v13/code/tests/test_toolforecast.py` **only for the optional fixture probe**, plus new Run176 workflow/proof. Base Run175 `3ec7eab3066b0f824268e35b1d00949d63fb7347`. Frozen production runtime, toolforecast implementation, Canon, registered models, original cohorts and all gates unchanged.

Run173 full-suite `40166625520` finished **FAIL**: 2408 tests, 1 FAIL, 1 ERROR, 13 skipped. Raw log artifact ID `12588498353`, ZIP SHA-256 `c06651dd13605ace2687ca2dd2b93b5e64abb8a51a60eebd395e8bc2bb10e5de`. The three Run164 CLI rc1 failures disappeared after staging exact LP3 audit siblings. Remaining original FAIL is live orphan descendant. New unrelated ERROR is in `test_toolforecast.CheckpointTests.test_competence_check_scores_states_not_calls`: an **optional local-only** `/root/native/restore/round8-note-tool-raw` existence check raises `PermissionError` on GitHub Ubuntu.

Run176 changes only the optional availability check: catch `OSError` from `Path.exists()` and treat inaccessible optional local fixture as unavailable, exactly like missing. **All competence scoring assertions and every original safety test remain unchanged.** Adds a focused regression that patches `Path.exists` to raise `PermissionError` and to return True. Local isolated logic 2/2 PASS; full exact source Git blob `28b551a3be56eaaf557e0a2f877fbf432137990a`.

Run176 CI repeats the Run173 full suite, same pinned dependencies and exact reconstructed Run21 helper with two audit siblings, true nonzero exit on any failure, raw log upload and official privacy scan. This is a test portability fix, not a forecast learning or native containment proof. CI result pending until independently verified. Expected remaining orphan descendant FAIL must not be suppressed.

Gates: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. Run171 real B1 predictor failed ablation. Run174 native larger cohort pending. Run175 subreaper/pidfd synthetic candidate is not cgroup proof.

Exact next step: run Run176 full suite after any active serialized native job; inspect raw failures, then independently review Run175 as optional defense-in-depth while retaining original cgroup/clone3 kernel containment gate. Do not retry rejected Drive destination.

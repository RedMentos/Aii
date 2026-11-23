# Phone C3 Context OS + STEP2 canonical exit gate integration — prereg 2026-10-31

Owner: automation11/GPT-6; review-only child of phone/C3 PR #1473 exact parent `621d4df389ea010ede9f53679a435eb8dd85b07e`. Independent STEP2 gate donor PR #1472 head `5d05b9baab44bbc4ea3df127bc67f3ced63d1739`; Run103 native C3 and other active owners untouched. This preregistration precedes code and workflow changes.

## Problem and permitted changes

The current phone-source packager includes only v13/scripts/tests/specs and a limited docs/proofs set; it **excludes** `v13/code/bench-results/`. Thus copying donor's new `STEP2_EXIT` graph without its exact original Z2b/Z2c native-negative JSONs would make the extracted Termux source lose the evidence needed to report `EVIDENCE_NOT_PASSING`. This is a source-distribution/acceptance integrity gap, not a new native result.

Copy exact Git blobs of `v13/gates.py`, `specs/gate-graph.json` and `tests/test_step2_exit_gate_split_20261031.py` from donor PR #1472; these paths are disjoint from phone/C3 PR #1473. Update `scripts/package_source.py` **only** to require and include the three existing original negative Z2 evidence files in phone ZIP: `bench-results/step2-z2b-seeds-20261021/z2b_result.json`, `bench-results/step2-z2c-b2-rule-20261021/z2c_result.json`, `bench-results/step2-z2-timescale-20261021/z2_result.json`. Never edit those evidence bytes, model/source/seed hashes, original gate results, or unrelated code.

## Fixed acceptance

1. On Linux Actions isolated Python, run donor's 7-case STEP2 exit tests and original `test_register_gates.py`; verify `STEP2_EXIT=EVIDENCE_NOT_PASSING`, original Z2b/Z2c `canonical_gate_pass` are **Boolean false**, STEP2 harness remains distinct, and no dependent Callosum/focal/timescale gate becomes GREEN.
2. Package **actual** current phone/C3 source with `scripts/package_source.py --phone-install`, extract, validate ZIP CRC + all manifest SHA256 entries, assert original three negative result bytes match source and donor's tests pass from **extracted ZIP**, not just checkout.
3. Run existing bounded phone smoke cohort `run102_c3` from extracted ZIP, and actual C3 Context OS B2 prior source tests. No model download, no native inference, no Redmi claim.
4. Preserve stdout/stderr, exact tested HEAD, exit codes, source ZIP, manifest, SHA256SUMS, privacy scan and diff in immutable GitHub Actions artifact (including failures). Review branch + PR, no merge/force-push. Negative age/STEP2/B3/JEPA/whole-system gates unchanged.

If incompatible, preserve original RED and repair only this child; do not silently weaken donor test, prune evidence, or promote a gate. Native/Redmi validation remains separately required.

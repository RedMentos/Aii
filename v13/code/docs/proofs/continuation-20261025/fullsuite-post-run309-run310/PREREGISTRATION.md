# Run310 — entire current-chain test suite after Run304–309 (2026-10-25)

Owner GPT-6 automation; base verified Run309 checkpoint `280ca41c406069303b71dff50a9213fc364176b8`. Independent review branch owns only a new full-suite workflow and this proof folder. No Runtime, model, source/seed/cohort, frozen Canon or acceptance-gate modifications. Serialize with `v13-native-c3-run131-serialized` concurrency group; respect Run297 native/Run303 Budget owners.

## Reason for rerun, baseline and acceptance

Meaningful new code changed backup SQLite closure, WorldModel source-disjoint holdout, Sleep A exact correction retention, Attention exactly-once outcome receipts; focused RED/GREEN tests passed and exact source-only ZIP Run309 passed 25 extracted tests. The prior **full-suite** on Run298 `40202886433` reported 2833 tests, 2 failures, 36 errors, 14 skipped (primarily frozen native candidate source mismatch and resident cancellation cleanup). These failures are preserved, not waived.

Run entire `python -m unittest discover -s tests -p 'test_*.py' -v` on exact PR head with isolated pinned numpy 2.3.5, prompt-toolkit 3.0.52, torch 2.9.1+cpu. Reconstruct exact frozen LP3 Run21 helper from immutable Run20 tar and patch in temporary directory, verify every source/helper SHA before execution. Fetch exact Run147 native fixture by artifact ID/hash, stage read-only, no model downloads or live native inference. Use existing `run-current-fullsuite-postfix-20261025.yml` as provenance template, without changing any frozen SHA. Preserve **all** test failures, not just success summary. Record exact head, original Canon SHA256, test count, failures/errors/skips, raw logs, exit codes, SHA256SUMS, official privacy scan. Upload closed raw artifact even on nonzero exit.

A full-suite FAIL is evidence, not a reason to falsely promote STEP2/B3/Body-JEPA or stop other independent Canon work. If failures match known frozen mismatch/cancel path, report exact overlap and continue an unrelated package; if new failures involve Run304–308 owned files, diagnose and fix without overwriting another owner. Never rewrite fixtures/hashes to make suite green. No Redmi claim.

Next command after workflow: inspect actual job logs and raw, compare to baseline by test name, persist BUILD_STATE and exact next package; continue productive work while budget remains.

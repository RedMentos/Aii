# Run423 — HX2 preregistration baseline integrity and RED-first repair

Date 2026-10-26; owner GPT; review-only branch `codex/run423-hx2-prereg-baseline-integrity-20261026` based on Run422/PR420 head `39b76971880944cc88ab514b597c25425ac4cce2`. Do not alter frozen STEP2 native source, model/seed cohorts, user rules, age gates or live harness consumers.

## Observed RED
Exact-head GitHub Actions Run422 job 40261529183 (job 121374757029) failed: 18/19 tests passed, test_same_task_same_seed_blind_preference_signal_not_approval expected PREFERENCE_SIGNAL_ONLY but received NOT_SUPPORTED. Cause: production code correctly requires nonempty disjoint exclusion registry and pinned solver/judge revisions, while positive test registered UNPINNED/empty. Keep the conservative production gate; fix test setup, not the gate. Preserve raw failing Actions artifact 12624384662 (ZIP SHA256 f1e38f0b46af4b690b4c5e42424640f0bf1a3b7b3baa277f14dfa5abb0dd7f20).

## Additional preregistration integrity counterexample
HX2 preregister hashes tasks/diff/seed and revisions, but does not bind the reference harness baseline. A caller can preregister on one baseline and later supply a different valid baseline, causing a different comparison under the same input_sha256. Bind complete validated baseline content at preregistration and compare. Preserve both arm outputs' hashes if the judge raises or the second solver fails; do not discard partial evidence.

## Proof
Add source-only tests for pinned positive signal, unpinned negative, explicit baseline tamper mismatch and partial-output hashes. Run inherited HX1/HX3/HX4 and HX2 tests in GitHub Actions, privacy scan, exact-head evidence closure. No native/model/Redmi execution claimed. No AG8 approval, age promotion, STEP2/B3/Body-JEPA/jepa_weight promotion. After verified checkpoint, proceed to another independent canonical package.

# Run596 preregistration — exact-current full unfiltered source-suite diagnostic (2026-10-26)

Owner: GPT automation11; stacked review-only on verified Run595 PR590 checkpoint `669d5a8b4debf2fd99d0d42de8af18b620400d32`. Exclusive files: new `.github/workflows/run596-fullsuite-current-diagnostic.yml` and `v13/code/docs/proofs/continuation-20261026/run596-fullsuite-current-diagnostic/`. No runtime/model/seed/cohort edits.

**Question:** Do the Run593 Callosum, Run594 complete chat export and Run595 Context OS selector changes preserve the original entire V13 Python source suite? Prior Run573 full unfiltered suite was RED (4 FAIL, 65 ERROR) despite many focused GREEN packages; the exact current integration chain must not be called whole-system passing on focused results.

**Prospective test:** Reuse Run573's *unchanged SHA-pinned* historical Run531 and Run147 artifact prerequisites and LP3 helper reconstruction, isolated pinned NumPy/prompt-toolkit/Torch CPU dependencies, `unittest discover -s tests -p 'test_*.py' -v` with no test exclusion, source/Canon/prereg hash logs, exact branch checkout, privacy scan and SHA-closed raw even if RED. Serialize under the existing `v13-native-c3-run131-serialized` GitHub Actions concurrency group; do not cancel an owner. Avoid fetching models or running native inference. Treat prereq download/expiry, suite timeout, or runner failure as a separate diagnostic outcome, not test success or gate promotion. The exact source SHA is captured rather than asserting older Run573 source hashes after intervening code changes.

**Decision:** If suite RED, preserve all failure/error names and categorize without modifying tests/cohorts; implement next independent root-cause package. If suite GREEN, report only source-only GREEN; native/Redmi and full V13 remain blocked.

**Claims:** no STEP2/B3/Body-JEPA/jepa_weight gate promotion. No new model run, Redmi run or private data publication.
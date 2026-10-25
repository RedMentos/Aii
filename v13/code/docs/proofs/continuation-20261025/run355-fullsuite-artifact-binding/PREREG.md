# Run355 prereg — restore pinned Run147 raw artifact prerequisite to complete source suite

Parent: Run354 exact-head source-suite review branch `202dc21c59342e342e54ddc186a96e6adabcddc3`, itself on Run353/PR349; not main. Run354 full-suite CI `40227346223` is still running at preregistration, so its outcome must not be invented or overwritten. This is an independent prerequisite-only package; owner: new workflow `.github/workflows/run355-fullsuite-artifact-binding.yml` and this proof folder, no production source or original tests.

## Prior observed blocker and immutable artifact
Run338 full-suite source CI `40220291845` had a Run148 `setUpClass` error because `tests.test_age0d_run147_independent_audit_run148` reads `RUN147_ARTIFACT` default `/mnt/data/RUN147_native.zip`, absent from a fresh GitHub Actions worker. The original dedicated Run148 workflow already downloads the **same registered native evidence**, so lack of a scratch file is a missing prerequisite, not a new native model failure.

- GitHub Actions Run147 `40158320858`, artifact ID `12585363362`, head `af8b88b35fd1cf32f0c6895d27ff956e28e9ab5e`, 2026-10-25, not expired.
- Artifact ZIP SHA256 `ddd60c897e1bdc634a40179b67e434097bb1e1999a6a2141372f6272682b9676`, verified against GitHub's artifact digest and independent downloaded bytes; CRC PASS; contains exactly `RUN147_C3_VARIED_NATIVE_REPORT.json` and `RUN147_VARIED_NATIVE_RAW.log`. Private Library retention copy: `/V13/checkpoints/2026-10-25/V13_Run147_NATIVE_ORIGINAL_shaDDD60C89.zip`.
- Original `v13-run148-age0d-native-audit.yml` demonstrates read-only download with `actions: read` and explicit SHA256 verification; reuse that exact approach without altering registered cohort, model, seed or hashes.

## Frozen acceptance
1. In new Run355 full-suite workflow, before tests, download **only** artifact ID 12585363362 with the existing GitHub token and `actions: read`; require exact SHA256, ZIP CRC and two required members, then export `RUN147_ARTIFACT` for original Run148 tests. Fail closed on any missing/tampered artifact; never regenerate or fabricate native output.
2. Execute the full source-only suite on exact PR head with the same serialized CPU-only dependency/concurrency budget and unchanged test list. Preserve all remaining failures, raw stdout/stderr and manifest; no blanket skip or gate promotion.
3. Run privacy scan, verify raw bytes, persist checkpoint. If Run148 still fails, record exact reason; do not retune 96-row original native cohort.
4. Distinguish this as **replay/audit of old Linux-native evidence**, not a new native run or Redmi proof. STEP2, B3, Body-JEPA, AG6 and jepa_weight negative gates unchanged.

Next command: GitHub Actions Run355 workflow on its own PR, serialized after Run354; `RUN355_FULL_SUITE_RAW.log` and `RUN355_SHA256SUMS.txt`.
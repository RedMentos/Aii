# Prospective evidence-closure amendment — 2026-10-27

Initial structural Linux file-world Actions `40448629698` passed (27/27 software tests, actual Z12c seed211 smoke and seed212 lifecycle exits 0), but independent artifact inspection found a real evidence gap: `cohort_sha256` was recorded without retaining the actual 600 transition rows, so the digest could not be recomputed from the persisted artifact. The independent-world process schedule and log also remained in a temporary directory that was deleted after export. This is **not** a training-utility claim and must not be concealed by a passing process exit.

Before changing source/tests, extend acceptance:
1. Persist the exact canonical, privacy-safe synthetic-content transition rows as `cohort.json` in the isolated output; its raw SHA256 must equal the manifest `cohort_sha256`, allowing independent recomputation and held-out split audit.
2. Preserve the independent world subprocess's original schedule and event log byte-for-byte alongside the model, with SHA256 entries in the manifest; no rewriting, synthetic replacement, or silent loss. If a required original log is missing, fail rather than claim a complete raw collection.
3. Unit tests prove raw cohort hash/row count and preserve existing checkpoint/restart, negative controls, output collision. CI raw ZIP includes cohort and world log, verifies hashes and reports the exact Z12c FAIL/low confidence without promotion.
4. Preserve first GREEN original artifact as historically structurally passing but **raw-cohort incomplete**; do not rewrite it. No registered seeds, model weights, calibration threshold, authority or age changes.

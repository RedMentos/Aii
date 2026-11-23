# Run13N — unfiltered current review-chain full-suite diagnostic (2026-10-30)

Owner GPT-6; review-only child of Run13M #1304 at `f5805204f68a063003e04eed9f45280e732628a8`. No code, model, cohort, scorer or Canon changes. **Purpose:** prevent isolated Run13J–M green focused tests from being mistaken for full cross-organ integration.

- Run the repository's original `python -m unittest discover -s tests -p 'test_*.py'` from `v13/code` against the exact branch snapshot. No skipping, excluding, xfail, monkeypatch, rewrite, test discovery filter or alternative scoring. Allow existing tests' own documented skip decisions. No model downloads, no native inference, no Redmi claim.
- Isolated venv and dependencies consistent with previous G15/Run13M software workflows; `V13_NO_AUTOSTART=1`, telemetry off. Hard wall timeout 15m, keep nonzero exit and original stdout/stderr. Stage outputs: PINS, VENV, DEPS, TEST, COMPILE, PRIVACY, DIFF; each exit code separately. Original raw, HEAD, pinned source blobs, SHA256SUMS and all failure text retained even if tests fail.
- Predeclared outcome: `FULLSUITE_GREEN` **only** if full unfiltered test exit0 and every other stage exit0. Otherwise `FULLSUITE_RED` with exact failure counts and original raw, no waiver. Historical G14/G15 full-suite RED is binding and may recur; the new run cannot retroactively change it.
- This is Linux CI software evidence, not end-to-end native B1/B2/C2/C3 utility, STEP2, B3, Body-JEPA, JEPA, Redmi, or whole-system acceptance. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, full blueprint incomplete.

After raw verification, triage only concrete new failures and choose next cross-organ canonical package; do not keep retesting unchanged failing suites without a new reason.

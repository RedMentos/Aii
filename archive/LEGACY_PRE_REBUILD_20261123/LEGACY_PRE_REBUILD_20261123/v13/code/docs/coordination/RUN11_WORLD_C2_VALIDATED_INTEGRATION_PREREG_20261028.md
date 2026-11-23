# Run11 cross-organ World F4 + C2 validated native route scoring — prereg (2026-10-28)

**Owner:** GPT-6 independent integration-only review branch `assistant/v13-run11-world-c2-validated-integration-20261028`, exact base `3de35568ff5905fa892a73358713a85bda626e1f` (PR #865 World receipt reconciliation source candidate, its full CI pending at prereg). Do not overwrite sibling owners or merge main.

## Inputs / exact source boundaries

- Parent #865 World F4 atomic/source-bound candidate blob `3799f84fdf52a82efe70e0e5e73bcfe4a95f0ac7`, preserving #861 invalid timing, #863 multi-action, #864 session-local state. Historical RED 4 failures+6 errors at 40645810035, original raw preserved. Parent green is a **prerequisite**, not assumed.
- Sibling PR #859 (GREEN source-pinned Linux software 40642735294) is a disjoint C2 benchmark scoring repair: `scripts/c2_benchmark.py` blob `12fe792cacd2dc92c2b3c5c33e01424e20a148e4`, `tests/test_c2_benchmark.py` blob `48554fd86c985fab520888af8bd7910236589683`. It scores only the first **validated** `select_processing` proposal; unrelated tool calls cannot masquerade as C2 routes. Do not reinterpret frozen native raw, which lacks full tool traces. Original model/catalog/seed/cohort unchanged.
- Sibling PR #860 modifies runtime and has source-frozen full-suite RED (4 failures, 62 errors). **Exclude** it from this integration; no hash rewriting or promotion.

## Plan

Import exactly the two #859 Git blobs into separate branch while preserving all other parent files. Verify exact remote blobs, run focused World atomic/corrupt/forged/timing/session and C2 benchmark suites, then full Linux software regression, compile/privacy/diff and archive closed raw stage exits/hashes. No model downloads, native execution, registered cohorts, tool authority or Age changes. If combined suite RED, preserve original raw and classify; do not claim green.

**Acceptance:** combined software regressions GREEN at exact source head and independent review; no production/main merge, no native route re-evaluation, no STEP2/B3/Body-JEPA/LP3/jepa_weight/whole-system promotion. Negative gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY, Redmi unmeasured. Platform budget UNKNOWN.

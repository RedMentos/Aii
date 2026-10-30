# Full unfiltered Run34/Run37 RED — exact pinned source mismatch audit (2026-10-30)

**Read-only evidence:** GitHub Actions `40991785171` on JEF source-explain full-suite branch (original raw artifact `12949379368`, ZIP SHA256 `c4fb54cbbd7bf28a65764c4f2e31bf3ae3010d3f91a11da9a0b14f480d03abb2`, CRC clean). **3425 tests run, 2 errors, 11 skipped**, `FULL_EXIT=1`; dependency/compile/privacy/diff stages passed. Private Library copy `/V13-Checkpoints/2026-10-30/Run11-JEFFinalAudit/FULLSUITE_INHERITED_RED_40991785171.zip` downloaded again and byte-compared identical. No rerun or waiver.

**Root cause verified against actual Git blobs** for `scripts/run34_c3_native_quote_intervention_pilot.py::prereg()`:

| Required file | Original registered blob | Current branch blob | Result |
| --- | --- | --- | --- |
| `specs/models.json` | `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` | same | MATCH |
| `scripts/run33_b2_c3_counterfactual_envelopes.py` | `b1d58d7e0c3937787cf15dd801e278de25845879` | same | MATCH |
| `v13/runners.py` | `efda7aa1aa5729e974d0d641870d4da05d21c961` | same | MATCH |
| `v13/utility.py` | `f4a92dab9c4a40761d64394cdca1c052e9a76bfd` | `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53` | **MISMATCH** |

The current utility file contains a later `_row_utility` guard rejecting invalid explicit utility scores (bool, NaN, infinity, out of range), and invalid duplicate/empty cohorts. The original frozen utility source does not contain this guard. This is a substantive source identity change; reverting the guard just to satisfy the frozen test would weaken current validation. The registered original hash is not to be updated or waived. Run34 intentionally raises `ValueError("native_source_or_catalog_changed")` when the current utility bytes differ. Run37 calls Run34 `prereg()` and therefore fails for the **same underlying cause**, not an independent model failure.

**Conservative resolution path:** preserve the original registered source hash and historical evidence; for a historical reproduction, use an isolated checkout/worktree at the exact registered utility blob, never silently substitute current utility. If current utility behavior is needed, separately preregister a new cohort/source identity and compare it without changing old scores. A future full-suite design may distinguish historical pinned-source reproduction from current-head functionality, but must retain an explicit failing pin check for the historical current-head mismatch; do not skip the test, change the expected hash, relabel RED, or promote any gate.

No source, model, seed, score, or acceptance gate changed by this audit. STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, Age0 RECORD_ONLY, jepa_weight=0, Redmi unmeasured, whole-system incomplete.

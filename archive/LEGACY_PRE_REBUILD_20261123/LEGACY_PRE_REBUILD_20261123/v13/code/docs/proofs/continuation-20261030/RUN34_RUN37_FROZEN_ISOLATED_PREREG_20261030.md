# Run34/Run37 isolated frozen-source preflight — preregistration 2026-10-30

Parent review PR #1179 exact head `ef29bc777910067da28fa2b41445ebf7e3cccb0a`. Own only this prereg, new CI workflow and non-promoting result delta; no runtime source changes, no cohort changes. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Observed blocker
Unfiltered full suite `40975677615`: 3372 tests, exactly 2 historical Run34/Run37 `native_source_or_catalog_changed` errors. Read-only source audit proved `specs/models.json`, `run33_b2_c3_counterfactual_envelopes.py`, `v13/runners.py` match registered blobs, but active `v13/utility.py` is `ff16ab6012b2865e0f3abde2a289aaf00e9aaa53`, while frozen Run34 requires `f4a92dab9c4a40761d64394cdca1c052e9a76bfd`. Current utility adds needed numeric/fixture validation; it must NOT be reverted.

## Registered controls
1. Checkout current exact parent in read-only active tree. Verify active utility blob `ff16...` and registered old blob object exists. Preserve current-source Run34/Run37 RED preflight raw; do not waive.
2. Create a **disposable isolated worktree** at the same head, replace **only** its utility file with exact Git blob `f4a92...` via `git cat-file blob`. Verify all four frozen source blob hashes in isolated tree and unchanged current active checkout.
3. Run unmodified original Run34 and Run37 preflight/refusal tests in isolated tree with no model/native execution, and require GREEN. Keep all negative gate assertions (native_executed=False, canonical_gate_pass=False, phone_measured=False, jepa_weight=0).
4. Capture exact-head raw logs, before/after blobs, pip freeze, exits, SHA256SUMS, CRC, privacy/diff. A historical isolated GREEN does **not** turn current-source unfiltered RED into GREEN and is not a native pilot.

No registered cohort/model/seed/source hash changed; no force-push or production merge. Next work after evidence: actual native Body-/Train-Port/ObjectiveAdapter and semantic STEP2 utility, not more historical helper loops.

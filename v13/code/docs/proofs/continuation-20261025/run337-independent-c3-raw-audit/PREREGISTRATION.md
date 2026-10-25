# Run337 preregistration — independent downloaded Run336 raw ZIP closure and non-promotion audit

UTC 2026-10-25. Source parent: Run336 PR #332 exact head `dfbe3c50a5e0f1b31e42d3ccb05fffa98c446195`. Separate source-only audit package. Do not change Run334/Run336 native workflow, model/cohort/seed/weights, optimizer, threshold, native tensor-byte auditor, original Canon or any runtime/approval/age gate.

## Question and frozen contract

Run334 original RED (Actions 40218827356, ZIP SHA256 `9900d10ca527a5181eca39047a38002d1f1539f4f79a92a2735630a672cba0d1`, 35/35 independent raw manifest PASS) demonstrates why a green source-only test is not native proof: only A ran two epochs; B/C absent after `ModuleNotFoundError: gguf`. Run336 replays the original three-arm cohort using only the pinned b10964 `gguf-py` import-path correction, with no new weights published. Its CI is currently in progress. This audit must never turn a partial or RED result into a PASS.

Implement `scripts/verify_run336_artifact.py` (stdlib only) for an operator-downloaded raw GitHub Actions ZIP. Require unique safe archive paths; no GGUF/weight files; exact complete SHA256 manifest closure; exact Run336 source head; pinned b10964 Python reader import proof; successful pinned source/build/model/native/audit/privacy receipts; original Run334 report status/evidence class and all A/B/C arm modes, two epoch receipts and selected-only tensor audit; independent Run334 raw-score audit; original negative gates and no activation/publication. Report only stored-artifact integrity, never native reexecution. This independent check is additive; original source-only auditor and native tensor-byte auditor remain unchanged.

## Verification before claims

1. Local synthetic adversarial ZIP tests: a synthetic complete-shape positive, and tampered manifest, wrong head, missing arm, false native execution, failed native stage, unpinned reader, failed independent audit, gate promotion, published weights, traversal, and nonselected-weight drift all fail closed. No synthetic positive becomes native evidence.
2. Run on original Run334 RED ZIP: must return FAIL_CLOSED.
3. Once Run336 native CI is terminal, download its artifact, verify actual SHA256/manifest and run the independent checker. Record all arm metrics and original failures. Do not claim PASS if the native run is incomplete.
4. Source-only CI and privacy check on the isolated branch; persist raw evidence privately and verify remote source bytes.

No Redmi access in this environment; STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. No model activation, AG6 or production merge.

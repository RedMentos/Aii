# Cross-organ review merge preregistration — P2X CAL36 + WP-T6 skilllive (2026-10-29)

## Exact parents, ownership and scope
- Source parent A: draft PR #1099, `codex/v13-p2x-cal36-transport-20261029` exact head `cc0417b3c0c879f35a60842adc79b4dabf08a415`, based on PR #1093. Software full suite 3163 OK (11 skipped), native CAL36 all NONE and no utility gain.
- Source parent B: draft PR #1100, `codex/v13-skilllive-crossskill-conflict-20261029` exact head `fcf9f20a438ac4607595bccfd4e0cdbc95dea97c`, based on PR #1097. RED-first 2 expected real Runtime failures, GREEN 22/22 focused; full suite `40885625890` must be checked before integration.
- Common active ancestor `1aa13abec66eccd2df24942479e1194e826caa5e` (PR #1090). GitHub compare showed **zero overlapping changed file paths** between the two review branches. The merge must preserve all nine changed WP-T6 paths byte-identically and all thirteen changed P2X paths byte-identically. No production main merge, no force-push, no owner-branch update.
- Integration owner: new independent `codex/v13-cal36-skilllive-integration-20261029` review branch. Prereg branch is a separate durable checkpoint. Only add this prereg and CI/handoff; do not change organ code or source/model/cohort/seed pins during merge.

## Acceptance and falsification
- Construct a genuine two-parent merge commit from the two exact source heads, with a tree equal to parent A plus the nine disjoint files from parent B (and this prereg). Verify each source blob after merge against its parent.
- Focused regression: P2X CAL36 6 tests, P2X corrected LoRA CLI tests, WP-T6 existing tests, within-skill and cross-skill Runtime tests; full source-only unittest suite with isolated dependencies, privacy scan and diff check. Preserve exact-head raw ZIP, stage exits, SHA256SUMS, failed tests and full logs. A failure is RED and must not be hidden by adjusting frozen historical pins.
- If parent B full suite is RED, defer merge until root cause is resolved on a separate owner review branch; never silently integrate a failing parent.
- A software integration PASS is not a model-utility or native C2 proof. CAL36 remains 0/24 positive, 0/24 source-sensitive, 72/72 NONE. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; Age0 RECORD_ONLY; jepa_weight=0; AG6 unapproved; Redmi unmeasured; V13 incomplete.

## Next exact action
Check `40885625890` original artifact and hashes. If GREEN, construct the two-parent merge commit without modifying either owner branch, create a new review PR based on #1099, run focused and full source-only CI, privately back up raw and record the next independent canonical package.

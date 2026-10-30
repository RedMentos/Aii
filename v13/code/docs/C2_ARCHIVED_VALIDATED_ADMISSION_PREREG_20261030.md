# C2 archived Needle3/scaffold hybrid: validated flag admission prereg (2026-10-30)

Review-only child of verified #1186 at `c7b23b863817f6ab8ad011f04c08c30387dde6b7`. Owner: this automation. Scope: archived post-hoc evaluator `v13/code/scripts/c2_route96_hybrid_archived_20261030.py`, new focused tests/workflow and evidence; **no live route change**.

Original pinned native 96-row artifact `12792493532` ZIP SHA256 `c4dd65ba18b446447271d4780b0741a4dc6994ab489496592ab3447123747076`, independently re-downloaded/CRC checked 2026-10-30: 95 native rows `validated=True`, one `validated=False` with `pred=None`, `confidence=None` and truncated tool call. Existing original result `NO_C2_HYBRID_GAIN` (hybrid 46/96, native 15/96) is **not** to be recomputed with changed cohorts or reclassified as a gain.

## Expected original RED
`predict()` currently selects a native route when `pred` is in ROUTES and confidence passes, without checking the row's `validated` flag. `validate()` does not require `validated` to be a strict boolean. An unvalidated but high-confidence route could be counted as native success in a future exploratory synthetic replay. This is evidence-integrity, not a live routing bug.

## Acceptance
- RED-first synthetic test: `validated=False`, plausible native route and high confidence must **fall back to scaffold**; a missing/string `validated` field must be rejected as malformed typed evidence; `validated=True` with `pred=None` must be rejected. Preserve original RED logs.
- Source fix: strict boolean validated in `validate`, and native selection only when `validated is True`. No new thresholds, labels, source/model/seed changes.
- Re-run exact pinned original 96-row ZIP through source-hash-verifying CI; assert original hybrid/scaffold/native scores and negative gate unchanged, 4 folds, no model calls. Focused tests + compile, privacy/diff, complete raw artifact, private backup when available.
- No C2 quality, Redmi, STEP2, B3, Body-JEPA, Age or whole-system promotion. Post-hoc archive remains exploratory only.

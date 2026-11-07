# BP6 bounded resampling input guard — 2026-11-07

Owner: isolated Codex review child of PR #1589, **not** the production or resume integration branch.

## Scope
The BP6 `meta_i` candidate previously divided by zero for `bins=0`, and `report` accepted `perm=0` (meaningless null estimate) while `boot=0` indexed an empty sample. Nonintegral counts could fail with unrelated Python exceptions. This child rejects invalid bin and resampling counts before analysis and adds a focused regression. The ordinary defaults (5/500/300) and stored historical DS3b measurements are unchanged. No original model/source/seed pins were edited.

## Evidence
- Parent: `assistant/v13-meta-i-tie-review-20261106` PR #1589, head at branch creation `2766598914cbe1e42894071242c0b2ec0d901759`.
- Source new Git blob `5d72a3e69ea9458588f8d59f46e4bf63bfd15655`; test new Git blob `57caea897780cb9221dae8d1c81a9969c9c798c0`.
- Source and test changes were committed through GitHub connector; **no local test executed** because direct git fetch fails DNS. Focused test command when checkout is available:
  `cd v13/code && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest test_metaeff_tie_invariance test_agi_metaeff`.
- Additional consumer tests before integration: `test_growth test_agi_live test_agi_solver test_bp6_metaeff_tie_reanalysis`. Run complete software suite separately before claiming integration.
- This branch does not contain or integrate PR #1587/#1590; PR #1588 already ancestor of resume. The resume branch currently lacks `v13/code/v13/agi/metaeff.py`, so this BP6 patch must not be transplanted alone. Establish exact dependency on #1586 and all later owners before merging.

## Unchanged negative gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; no Redmi or whole-system completion.

## Next
Verify branch file bytes, run focused software tests in an isolated checkout with full `specs/` fixtures, then integrate BP6 dependency chain into a new branch only after reviewing ancestry and conflict risk. No native jobs until ownership confirmed.
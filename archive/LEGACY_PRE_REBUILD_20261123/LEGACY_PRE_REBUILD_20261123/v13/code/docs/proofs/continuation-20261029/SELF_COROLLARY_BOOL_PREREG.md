# Self/World corollary boolean-vs-number attribution guard — prospective prereg (2026-10-29)

Owner: GPT-6 isolated WP-N9 Self/World attribution package. Parent exact source `6854e17317e8a7a13bd968ba7a15ea5612c29799` (PR #1084 Context OS child); do not modify the prior Context OS/JEF work or any frozen model/cohort.

## Reproducible source-level counterexample

`v13/selfmodel.py::_match` treats observed booleans as numbers: `isinstance(True, (int,float))` is true, so a numeric prediction `value=1.0, tolerance=0.0` is considered exactly matched by observed `True`. The inverse `value=False` versus observed integer `0` is also incorrectly equal in the fallback branch. This can attribute a type-conflicting observation as `SELF` and suppress an error signal in the digital Self/World corollary path (§7.5/§85.7). This is a deterministic software flaw, not a demonstrated native/model behavior.

## Exact narrow fix

Preserve wildcard `'*'` behavior and existing numeric residual/tolerance logic for real numeric observations. Require strict boolean-to-boolean type matching when either side is boolean; a boolean/numeric mismatch must be a nonmatch with structured expected/actual residual, never a numeric zero-error SELF outcome. Do not alter far-outside, mixed, delayed, ambiguous or external attribution thresholds. Keep no-model test harness and all Age0/learning gates unchanged.

## Tests and acceptance

Red-first pure `_match` and `attribute` counterexamples: numeric 1.0 vs True; boolean False vs integer 0; True vs numeric 1; boolean True vs True; numeric 1 vs numeric 1.0; wildcard with boolean; type-mismatch should not be SELF and must not yield numeric zero residual. Also check existing G-SELF-WORLD-005 six cases, Runtime corollary integration and full software suite. Run source-hash pinned GitHub Actions, raw and privacy evidence. No native inference, learning or device claim.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. A verified checkpoint is not an end-of-run condition.

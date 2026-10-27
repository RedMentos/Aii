# AGE0d exact-representability guard — preregistration (2026-10-27)

## Frozen lineage and ownership
- Exact parent: `6c1e0e985c7fa5ba5e477d95743cf1e21b718831` (review-only PR #759; NOT `main`).
- Source blob before change: `b1a58497ccf508784ded8fb478935cd664859f7a`, `v13/code/scripts/age0d_answer_audit.py`.
- Scope: deterministic local-only arithmetic diagnostic; no live delivery, runtime hook, new Age permission, model, training, or native/Redmi claim.
- Owned files: `scripts/age0d_answer_audit.py`, `tests/test_age0d_exact_representability.py`, new dedicated workflow and this proof note. Do not change frozen tests, source cohorts, SSOT, or another agent's branch.

## Hypothesis / expected RED
Current anchored parser accepts at most 12 integer digits and 12 decimal digits per number. Exact multiplication/division can produce a value outside that grammar; e.g. `0.000000000001 * 0.000000000001` = `1E-24`. Even a reasonable shortened answer cannot express the exact value; the audit currently labels such answers `MISMATCH` instead of conservative `ABSTAIN`. Likewise `999999999999 + 1` has 13 integer digits. A deterministic correction alarm in an unrepresentable exact-answer case is not calibrated evidence.

## Locked tests
- Out-of-format exact result must ABSTAIN: tiny product with answer 0, tiny terminating division with answer 0, 13-digit integer sum with answer 999999999999.
- Exact representable controls must remain CORRECT: `0.000000000001 * 2 = 0.000000000002`, `2 / 4 = 0.5`, `999999999999 - 1 = 999999999998`.
- Frozen existing `test_age0d_answer_audit`, `test_age0d_cli`, `test_age0d_locale_ambiguity_review` must remain green; 32-case frozen fixture and original locale ambiguity gate unchanged.
- RED: new focused tests fail on parent source. GREEN: minimal source fix passes; run full source-wide software suite if CI resources allow. Raw exits, exact head and privacy scan must be recorded; failed attempts preserved.

## Proposed constrained behavior
Use a high-precision local Decimal context (64 digits, above max 48-digit product) for binary arithmetic; before comparing with a parsed answer, require the *exact* result to be representable with <=12 integer and <=12 fractional digits after removing trailing decimal zeros. Return ABSTAIN when not representable. No approximate rounding or silent numerical correction. Do not change division recurrence rule or source model/seed hashes.

## Evidence boundaries
Software/synthetic only. All LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight=0, Age authority=0, Redmi unmeasured, and V13 incomplete remain. Independent review before integration; no auto-merge.

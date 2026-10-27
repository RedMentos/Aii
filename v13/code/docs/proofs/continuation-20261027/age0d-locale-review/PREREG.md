# AGE0d locale-ambiguous 3-digit separator review prereg (2026-10-27)

Exact parent `51e23fab7716dc90f3269a505002b002424ef94e` (PR #757 local CLI, child of #755); review-only candidate branch `assistant/v13-age0d-locale-ambiguity-review-20261027`, not main. This prereg precedes RED tests and GREEN source. Owner: `v13/code/scripts/age0d_answer_audit.py` candidate, `v13/code/tests/test_age0d_locale_ambiguity_review.py`, isolated CI and this proof directory. Frozen runtime unchanged.

Defect hypothesis: the answer-aware parser treats both comma and dot as decimal separators in every language. A numeral like `1,234` (often grouping 1234) or `1.234` (often grouping 1234 in German) is silently interpreted as 1.234. A correct answer 1235 to a `1,234 + 1` question can be marked MISMATCH; an answer `4,000` can be interpreted as 4.000 even though it could mean four thousand. Such ambiguity violates the intended fail-closed false-alarm property.

RED: add fixed counterexamples `What is 1,234 + 1?` answer `1235`, `Berechne 1.234 + 1` answer `1235`, and `What is 2+2?` answer `4,000` and `4.000`, all required ABSTAIN, plus unambiguous decimal `0.125` and `3,5` correct controls. Original code should fail 4 counterexamples; retain raw evidence.

GREEN: a minimal `_number` guard rejects any signed nonzero 1–3-digit integer part followed by a single dot/comma and **exactly three digits**. This deliberately abstains even when the notation could be a legitimate three-decimal fraction. Leading zero (e.g. `0.125`) and unambiguous one/two decimal places remain accepted. Do not change grammar, existing frozen 32-case evaluation, authority, CLI transport or model weights. Focused tests plus original 32-case suite, compile/privacy/diff, raw exits. Full suite separately if needed.

No broad locale understanding claim; no live delivery. AGE0c STAY_SHADOW, LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight0, Age authority0, Redmi unmeasured, V13 incomplete.

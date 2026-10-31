# Run52 lexical metric specificity audit — verified software checkpoint 2026-10-31 UTC

Owner GPT-6, independent review-only child of Run52 preflight head `2211863105802d3192bd6247546dab3ce7deb761`. Precommitted audit question `RUN52_LEXICAL_METRIC_AUDIT_PREREG_20261031.md` at commit `67432084f17cae64ce3c947f9248942f3b0b8d95` before candidate/test implementation. Run52 owner branch, seed479 fixture SHA256 `5cc8783dedbb201a0a8b86763c99dc23130e1d126a603cf0afcac33d8b985f3b`, registered original scorer and independent replay scorer, original native evidence and all model pins remain untouched.

## Concrete finding

Both registered Run52 runner `b1_signal` and independent replay `lexical_b1` return positive on six synthetic counterexamples that do not establish the intended lexical meaning:
- Expected A/30 but text explicitly says **Option B** and includes ordinary article **a** before remaining 30: the case-insensitive `\\bA\\b` matches article `a`.
- Expected A/30 or B/15 but text says `30.5`, `-30`, `15.5` or `-15`; original integer regex matches the embedded digit sequence.
- Expected NONE but text says `None of the options? Option A qualifies.`; original NONE keyword alone matches.

The original metric is **narrow lexical signal**, not a semantic truth gate. This is a diagnostic of possible false positives, **not** a retroactive score correction, native error claim or modification to preregistered acceptance. Added isolated `run52_lexical_metric_future_candidate.py` with conservative explicit Option/Choice markers, positive whole integer boundary and nearby remainder word, and a 5-test adversarial suite. The candidate is not authorized to rescore seed479; a fresh disjoint preregistered native cohort is required before replacing a metric.

## Verified raw

GitHub Actions `41160833960`, exact executed head `f33498f297bea56feb6c54f7981030e1764739d8`, terminal SUCCESS: **59/59** real software tests (5 new audit, 5 existing Run52, 49 earlier Run51/50/49/48/46B); all 8/8 stage exit receipts zero, privacy CLEAN. Original ZIP artifact `13027135894` SHA256 `b141b81d45979c0cdd08ee52098f15ca6b0b1bef9dd75198f2464c45e3b064a6`; CRC PASS and **18/18** SHA256SUMS inner hashes verified independently. Private Library backup `/V13-Checkpoints/2026-10-31/Run52-Lexical-Metric-Audit/Preflight_GREEN_41160833960_SHA_b141b81d.zip` independently materialized and byte-compared identical.

## Next and limits

Do not retune or rescore the current seed479 Run52 native protocol. First await its original native terminal result and preserve every raw row; compare original prereg score unchanged, and attach this audit as an explicit limitation. If metric specificity matters to next-stage interpretation, preregister a **new disjoint** test with explicit positive-choice and whole-number controls before model inference. Independently progress other canonical organs meanwhile. Exact focused command: `cd v13/code && PYTHONPATH=.:tests:scripts python3 -m unittest -v tests.test_run52_lexical_metric_audit tests.test_run52_b1b2_cross_turn tests.test_run51_f1f5_second_attempt tests.test_run50_native_c3_c5_c6_draft tests.test_run49_c5_c6_draft_shadow tests.test_run48_jef_c3_final_agreement_shadow tests.test_run46b_jef_source_eligibility_shadow`.

No native inference in this audit, no Redmi measurements, no Runtime or output authority, no whole-system claim. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW. Original Run44 native RED remains. No production merge or auto-merge. Platform remaining budget UNKNOWN.

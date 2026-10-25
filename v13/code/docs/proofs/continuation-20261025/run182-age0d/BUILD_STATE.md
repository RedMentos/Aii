# Run182 — AGE0d answer-aware exact-source contradiction SHADOW candidate

Base: Run181 preregistered review branch `4f781889c6634959f06466ef0a97b84ecb2bac99` (PR210). File owner: **new** `scripts/run182_answer_aware_shadow.py`, `tests/test_run182_answer_aware_shadow.py`, this proof and focused CI only. Run181's heavy native B2 utility job is a separate active owner; no changes to its files or process. Frozen Runtime, `selfmodel.py`, `age.py`, user rights, model pins, source corpora and V13 Canon untouched.

## Why this candidate

WP-AGE0c showed the earlier post-answer heuristic had **100% false alarms** for correct JSON answers and 0% useful alarms on its real replay; `:self correction deliver` must not be recommended. WP-AGE0d asks for a checker that actually sees the **delivered answer and exact source** before suggesting a correction. Run182 is deliberately narrower: only an explicit single approved budget in euros or a single revised deadline (`moved from X to Y`) in a source, plus a single explicit corresponding value in the answer. It compares normalized Decimal budgets or normalized month/day dates, and emits `SHADOW_MISMATCH` only when values differ. All ambiguous/missing/unsupported inputs abstain. The returned `source_ref` offsets bind the exact source quote; there is no inferred fact or model call. This does **not** claim general contradiction detection.

Authority always `shadow_only=True`, `delivery_authorized=False`, `learning_authorized=False`, `age_reopen_authorized=False`. No import into SelfSystem, no user-visible correction, no automatic approval, no edits to original answer. No learned weights or latent authority. Existing Age-0 default SHADOW remains untouched. The code uses Python standard-library `decimal.Decimal` for exact decimal comparison; no network, model, torch or native device.

Local synthetic tests: **11/11 PASS**, `compileall` PASS; cases include wrong/correct budget, wrong/correct revised deadline, comma decimal equivalence, ambiguous source/answer, missing value, unsupported question, invalid input, and authority never granted. SHA-256 source `cd3e0b1f10c085e0662c61d2d9bebcc6e226507891309af8583e03fb3204b11c`, test `5023fc8a17b0e3f780b934d6cf87a1dd3f5fb56c5cffa44513b129ff53f33e71`, raw test log `0f993ced309d6c1d314776b96770cd1627b05130e31e656756fe84d2ce079755`.

## Limitations and next acceptance

This is **synthetic software-only**. It has not been measured on real C3 answers, German wording, varied dates, quoted claims, source conflicts, precision/units, or ambiguous multi-project context. No false-positive/recall estimate may be inferred from the hand-written tests. Before any recommendation to deliver: separately preregister a held-out replay with actual final answers and exact source, include correct and incorrect answers, compute false-positive rate and source-supported true positives, and preserve negative cases. Never weaken Age0c failure or grant Age rights from this candidate.

Gates unchanged: `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`. Original Run173 full-suite orphan failure and generic frozen Phone-source CI failure remain. Next: independent review and real-answer shadow calibration; do not integrate into live `deliver`. Rejected anyone-writable Drive destination remains forbidden.

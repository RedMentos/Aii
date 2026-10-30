# Run12N original source cohort × existing JEF budget SHADOW (2026-10-30)

Review-only child of Run12N full-task posthoc PR #1275. This package binds the **existing** `v13/agi/budget_en_source_shadow.py` (Run11Y; frozen source grammar and zero-authority behavior) to the exact four Run12N native source prompts, without changing either implementation, source/model/seed hashes or original negative results.

New `tests/test_run12n_jef_source_baseline.py` uses actual Runtime Store source references and `jef.propose` for the four Run12N `frozen.prompt` strings. It requires 4/4 exact budget remainder and faster-option candidates, unchanged Store source count, zero model calls/weight updates/authority, and negative gate flags. Three tampered/foreign source controls must abstain. This is a **deterministic task-specific baseline**; the shadow's closed grammar cannot handle arbitrary language and it cannot authorize output replacement or tool execution.

Original Linux-native Run12N at Actions `41061289187`: structural 16/16 GREEN but registered C2-auto numeric utility 1/8 RED; posthoc strict full answer 0/4 all arms. The JEF candidate, if verified, demonstrates a *read-only exact-source check* available in the architecture, not an integrated live repair or learning proof. This package does not re-score the frozen native output.

Exact source-only GitHub Actions `41062848655` launched at HEAD `1c5a0a8f5e05675c53f9b64c384087a933aa7f5b`, with frozen Run11Y and Run12N source pins; result PENDING at this checkpoint. On terminal inspect original raw artifact, preserve RED, independently verify SHA256/CRC/inner hashes and private byte-exact backup.

Next independent package: preregister disjoint whole-task cohort with numeric+faster source-bound metric and compare read-only JEF exact-source proposals against C3/B1/B2/C2 native controls, **without** using JEF to repair model outputs or enabling tools. Any live intervention would require separate explicit age/approval and safety gates. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole system incomplete.

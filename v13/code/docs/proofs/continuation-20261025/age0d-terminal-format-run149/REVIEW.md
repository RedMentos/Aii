# Run149 — isolated AGE0d terminal-format SHADOW candidate

**Scope:** A pure, opt-in evaluator `v13/agi/answer_arithmetic_shadow_v3.py`; no runtime consumer, no live delivery, no model update, no user age or approval changes. Only new source/test/workflow/proof files owned. Original Run134/146/147 code, hashes and cohorts untouched.

**Change:** Recognize source-matched arithmetic outputs with terminal blank lines or a single bold integer (`**-4**`), preserving the exact original answer-span offsets. Explicitly refuse multiline narrative, conflicting text, scratch `<<...>>` chains, unrelated source echoes, noninteger division, control characters and unsupported operations. All results have `authority=SHADOW_ONLY`, `may_deliver=false`, `may_update=false`.

**Software tests:** 10/10 local PASS in repository-shaped directory layout. Deterministic 120-task synthetic suite, seed 14926, 0 exact question overlap with Run147, SHA-256 `f708e90ef2312d7eb8c453508778ba3f07eb52631e54bcc86f60e80e5701f10f`; for each task tests correct, deliberately wrong, and contaminated narrative output.

**Posthoc closed Run147 readout (not a new native test):** v2 supported 83/96 (79 correct / 4 wrong / 13 abstain); v3 supported 90/96 (86 correct / 4 wrong / 6 abstain). Seven additional classifications are from terminal formatting only; no additional wrong examples. They were originally unlabelled and are **not independently human adjudicated**. Original Run147 K2 remains INSUFFICIENT; no gate promotion.

**Next:** Exact-head privacy and CI tests; independent review; fresh prospective native holdout if justified. Separate Linux software, Linux-native original evidence, and Redmi (NOT RUN). Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, DS2 H2 FAIL, V13 INCOMPLETE.

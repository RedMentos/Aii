# P0X independent paired source-use analysis — prospective read-only plan (2026-10-29)

Owner: GPT-6 independent reviewer. Parent: P0X 600-arm prereg PR #1062 exact `a86405e9ee897db09cb046f269ca59529ccbd604`. At registration, the 600 native calls were not yet observed; do not alter the original prereg, seed, cohort, models, source strings, native runner, or acceptance thresholds.

## Fixed analysis before 600-arm result

- 150 matched P0X heldout task IDs from fixture SHA256 `ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e`, C3-only baseline original 150-call Linux-native raw SHA256 `79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1` (50 exact, 100 wrong commitments, all 150 predicted NONE).
- Analyze four source arms: `b1_only`, `b2_only`, `both_exact`, `shuffled`, each 150 matched rows. Pair by original ID SHA256, never by mutable output order. Reject missing/duplicate IDs, mismatched oracle labels, malformed parse categories, wrong row counts, mismatched source/score SHA pins, or changed negative gates.
- Primary descriptive contrast: `both_exact` vs `c3_only` on per-row correctness. Secondary contrasts: `both_exact` vs `b1_only`, `b2_only`, and `shuffled`. For each: matched wins, losses, ties, exact-count delta, paired difference, exact two-sided McNemar/binomial p on discordant pairs, and deterministic 5,000-replicate paired bootstrap percentile CI using seed `2026102919`. Apply Holm correction across four comparisons; report adjusted and unadjusted p. Do not change preregistered success criteria or interpret exploratory p as a Canon gate.
- Independently report `wrong_committed` per arm, foreign/shuffled false commitments, and label collapse. Never count UNKNOWN as correct for A/B/NONE oracle; only exact labels count.
- Software mocks and native Linux results are distinct; source-only scores cannot claim model utility. The analysis is read-only and not a training or inference run. Original 600-arm native raw and independent verifier must be audited before any statistical conclusion.
- Negative gates stay Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight 0, Redmi unmeasured, V13 INCOMPLETE.

Next: implement a deterministic stdlib-only paired analyzer and tamper tests, run source-only CI; later evaluate only independently closed original 600-arm evidence without rerunning native models. No production merge.

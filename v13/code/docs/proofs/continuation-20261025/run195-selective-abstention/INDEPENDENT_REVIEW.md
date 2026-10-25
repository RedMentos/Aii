# Run195 independent cross-review — per-kind safety (2026-10-25)

This review is independent of the Python Run195 selector: it rereads the immutable GitHub `capture-seed11.json` blob `c8176df6c2a0ce79d3ba4016541878de48940e93`, applies the **already sealed** threshold `0.5803461074829102` to `-digit_min_logprob` and counts per fixture prefix. No native model is run; no answer is regenerated. Original capture SHA-256 `96efd0d65bdb13005336661e0cb09fc7d1f41a1e62ec77c0b512ebf74078b5a1` unchanged.

| Kind | Original correct / 15 | Answered | Correct answered | Wrong answered | Wrong / answered |
| --- | ---: | ---: | ---: | ---: | ---: |
| summary | 9 | 8 | 7 | 1 | 12.5% |
| long | 15 | 15 | 15 | 0 | 0% |
| notes | 13 | 13 | 12 | 1 | 7.7% |
| compare | 5 | 10 | 3 | **7** | **70%** |
| **Total** | **42/60** | **46** | **37** | **9** | **19.6%** |

The frozen global preregistered criterion is satisfied retrospectively (46/60 coverage, 9/46 wrong vs 18/60 raw wrong), but the **compare stratum is unsafe**: seven of ten answered compare questions are wrong. The global gain largely reflects selective abstention on some harder tasks while all 15 easy long tasks are answered correctly. The original comparison task error rate is 10/15 (66.7%), so the selector does not establish lower compare risk.

Approximate separate 95% Wilson intervals (descriptive, not a paired significance test): selected error 9/46 = 19.6% [10.7%, 33.2%]; raw C3 error 18/60 = 30.0% [19.9%, 42.5%]. They overlap. Selection sacrifices five originally correct answers (37 correct delivered instead of 42). The criterion does **not** demonstrate higher total task utility, and seed11 was not truly blind: its aggregate results had been published on 2026-10-12.

**Independent deployment verdict: NOT_SUPPORTED.** Do not wire this threshold to live C3 abstention or JEF routing. Any next evaluation needs genuinely fresh unseen native tasks, source/revision pinning, stratified preregistered risk ceilings and a cost for withholding correct answers. Existing R4 wake-policy NOT_SUPPORTED, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 and full V13 INCOMPLETE remain unchanged.

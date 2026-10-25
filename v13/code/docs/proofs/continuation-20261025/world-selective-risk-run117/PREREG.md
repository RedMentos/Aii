# Run117 — fresh-seed World Model selective-risk diagnostic (preregistered)

Date 2026-10-25 UTC. Base verified Run114 PR #145 `6fce98c2111429b1951e6e527608cb9c543c21b3`. Owner: new `v13/code/scripts/ablation_world_selective_risk_run117.py`, new tests, Run117 CI/evidence only. No edits to World Model runtime, original Run114 ablation, active Run106 episodes.py, Run116 LateWatch, canonical blueprint, model artifacts or age/approval gates.

## Motivation and evidence
Run114's unchanged original five seeds 13–17 × 400 queries: 1161/2000 counterfactuals correctly abstained as `IMPOSSIBLE_PREDICTED_OUTCOME`; original confidence Spearman prereg is `INCOMPLETE_ABSTENTION`, not positive evidence. We need a separately preregistered question: **among physically valid simulated predictions**, does the confidence rank lower-error predictions better than simple controls?

## Locked fresh cohort and metric
- Fresh seeds `200..219` inclusive (20 seeds), exactly 300 synthetic own transitions and 400 held-out queries per seed, unchanged `ablation_world_model_confidence.world(seed)` generator, `world_model.fit` and `counterfactual` runtime functions. No native/Redmi data.
- For each query, draw a random-control score from a separate seeded RNG before checking validity. A query with no finite complete prediction is an **abstention** with reason; it contributes to denominator and cannot be assigned a made-up error or score.
- Among valid queries only, select top `floor(0.25*valid_n)` (minimum one) by descending score with stable original-query-index tie breaking. Metric = mean absolute error against synthetic noise-free truth for selected queries (lower is better).
- Four arms: actual confidence, samples-only coverage `1-exp(-samples/COVER_N)`, spread-only `1/(1+spread/SPREAD_REF)`, random. All arms share the exact same valid query set and same top-k.
- A seed is evaluable only if `valid_n >= 40`; otherwise entire result is `INCOMPLETE`, no positive verdict. Report valid/abstained counts and reason counts per seed.
- `SUPPORTED_SYNTHETIC_SELECTIVE` only if confidence has strictly lower top-quartile risk than **each** of three controls in at least 16/20 seeds **and** lower mean risk across all 20 seeds for each control. Otherwise `NOT_SUPPORTED_SYNTHETIC_SELECTIVE`. No post-hoc threshold tuning.
- Negative, tie, or incomplete outcomes are preserved. No STEP2/B3/Body-JEPA/DS2/whole-system gate promotion; no production confidence authority. This diagnostic cannot prove the value of abstention itself or causal utility.

## Verification
Test-first RED: deterministic synthetic world, equal denominators and k across arms, explicit no-prediction abstention, no positive verdict for incomplete cohort, fixed seeds. GREEN: focused tests, full 20-seed synthetic Linux job with raw JSON artifact/log and official privacy scan. Preserve raw failed attempts and source hashes. Heavy native/model jobs not run.

# WP-T14 persisted row integrity — preregistration (2026-10-27)

## Lineage and isolation
- Parent PR #761 review-only exact head `5458dce977ad22f82fb1749811c512bb543782fc` (not main, not production-integrated).
- Frozen source `v13/code/v13/control_budget.py` blob `aa29c4eb39b5fdc87c58ac3838acd3dd2818281c`; original finite stage-mark guard remains unchanged.
- Owner of this child only: `control_budget.py`, new `test_control_budget_row_integrity_review.py`, dedicated workflow and this proof. Do not modify original #761 branch or thresholds.

## Counterexample and expected RED
`latency()` does `json.loads(metadata)` then unconditionally `meta.get`. Valid JSON containers `null`, `[]`, strings and numbers raise AttributeError, crashing the operator budget report instead of excluding invalid evidence. It also trusts `messages.created`; invalid type/nonfinite/negative timestamps can crash `max(times)-min(times)` or pollute the denominator and hourly rate.

## Locked tests
- Invalid metadata JSON shapes (`null`, `[]`, `"bad"`, `0`, `true`) plus one valid row: invalid rows excluded, valid latency and denominator preserved.
- Invalid timestamps (`null`, `"bad"`, bool, NaN, +/-Infinity, negative) plus one valid row: invalid rows excluded, no NaN/Infinity in report.
- Existing finite marks and original control budget tests remain green; valid stage marks unchanged.
- RED test-only commit must fail on parent. GREEN source fix minimal; run focused, privacy, compile, diff, and full software suite. Preserve raw failure logs and exact commit/blob hashes.

## Proposed behavior
After JSON decoding, accept metadata only if `type(meta) is dict`; accept created only if exact int/float, finite and nonnegative; otherwise skip the entire invalid row. Keep all budget limits, stage timing math, no-limits default and recorded evidence levels unchanged.

## Claim limits
Software/synthetic only; no native/Redmi, energy/thermal or whole-fabric calibration. LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight=0, Age authority=0, full V13 incomplete. Independent review required, no auto-merge.

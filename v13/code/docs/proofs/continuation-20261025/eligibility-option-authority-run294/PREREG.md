# Run294 preregistration — eligibility option authority

Date: 2026-10-25 UTC. Owner: `v13/code/v13/agi/eligibility.py`, new `tests/test_run294_eligibility_option_authority.py`, dedicated CPU-only CI, scoped proof. Parent: PR293 `df5f29c1f4a1ac4f9e58d83cecd9bccc3ba6fe7a` (branch-scoped, not main). No changes to Runtime PR284, output-adapter PR293, native model/seed/cohort, thresholds, Canon, or learning/age gates.

## Defect hypothesis (before code)

`decide` validates option A/B fields against *any* source, but unlike budget/deadline/local-only rules it does not require current-message option fields to override earlier quotes. A stale earlier Option A cost can be accepted even when the current message explicitly changes it. Repeated contradictory current Option A clauses can also be silently resolved to the first clause. The fixed reader may already handle some of these, but direct `eligibility` tool and model-reader fallback remain exposed.

## Frozen adversarial checks

1. Earlier exact option A cost 40, current exact option A cost 90, extracted A cost 40: must return UNKNOWN with `A:conflicts_current` even when old text verifies the stale cost.
2. Extracted current A cost 90 and unchanged B: accepted with original deterministic cheapest-eligible recipe.
3. Two contradictory current A clauses: UNKNOWN, never pick first.
4. Repeated identical current A clauses: no false refusal.
5. A/B mentions without field statements must not suppress valid earlier option evidence.
6. Option A and B in one sentence must not bleed values between clauses.
7. Current conflicting budget values: UNKNOWN, not silently choose one.
8. Wrong-typed option `local` must not be cast with `bool("false")`.
9. Original eligibility tool, fixed-reader and live regressions remain passing.

## Claim/evidence limits

Software/SQLite only. No new native model inference, no registered cohort redefinition, no new user consent, no approval promotion. Preserve `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE. Record actual RED/GREEN or failure, source hashes and exact next action. Do not weaken an original test.

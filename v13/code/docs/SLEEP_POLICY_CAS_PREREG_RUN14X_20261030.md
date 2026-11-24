# Run14X — Sleep policy fail-closed boolean and CAS concurrency (2026-10-30)

Parent: Run14W cross-organ integration branch exact `ef8f6d0bda3d6b19e2280c4bafeed4658639de55`; parent full-suite Actions 41125663275 still running at preregistration. Owner GPT-6, independent F9 Sleep control-plane package. Scope `v13/code/v13/sleep.py`, new `v13/code/tests/test_sleep_policy_cas_run14x.py`, workflows/checkpoint only. No Canon/model/registered cohort/learning-age gate change.

## Observed source bug

`SleepCycle.set_policy('enabled', value)` silently maps every unrecognized string (including `yes`, `maybe`, `None`) to `False`, unintentionally disabling Sleep. Policy mutation also writes without `expected` state version; two concurrent operator updates can overwrite one another. This is operational control integrity, not native model quality.

## Frozen tests before implementation

1. Explicit true aliases `on/true/1/ja/yes` and false aliases `off/false/0/nein/no` persist and reload; malformed or empty value rejects with ValueError without changing durable policy.
2. Deterministic injected interleaving between state read and write causes CAS retry, preserving both independent changes; no lost update. Bounded retry fails closed if state changes continuously.
3. Invalid mix, locked gain and numeric policy gates unchanged; existing Sleep scheduler, validation, source lineage and AG12 holdout tests pass.
4. No new learning authority, no dream fact writes, no weight activation, no auto-enabled Sleep. Original RED and candidate raw closed, hash-verified and privately backed up. Historical full-suite RED remains unwaived.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi unmeasured, whole system incomplete.

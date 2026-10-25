# Run261 — terminal failure training lineage (RED-first, 2026-10-25)

Base: PR259 verified head `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`. Exclusive ownership: new test file, unique CI workflow, this proof directory. No edits to PR259 owner's `world_model.py`, `test_world_model.py`, Runtime, Store, native cohorts, Canon, gates or historical raw logs. This is actual production Store with synthetic action outcomes; not native inference or Redmi.

## Predeclared problem

Canonical §7.2.1 requires an observed **outcome** objective; current WorldModel target explicitly includes success=FINAL vs failure=0. `transitions()` includes valid terminal `ERROR` actions, but PR259 `_action_binding()` returns None unless `status=='FINAL'`. Thus one valid failed action among 24 can force `fit()` to `SOURCE_UNVERIFIED` and prevent training the failure target. Restrict to observed terminal statuses with nonnull finite outcomes, not DISPATCHED or invented targets; source, selected route and action outcome must remain hash-bound and revocation-aware.

## RED-first contract

1. Actual Store, 24 valid source-backed actions, 20 FINAL + 4 ERROR: `transitions()` retains all 24, four with success=0.
2. `fit()` produces source-bound FITTED state and `load()` accepts it; failure examples remain in training.
3. Mutating a trained ERROR action's outcome invalidates the fitted state just as mutating FINAL does.
4. Run existing WorldModel tests alongside, preserve exact failures and raw artifact. Do not modify production WorldModel under PR259 owner; send counterexample for independent review. No STEP2/B3/Body-JEPA/jepa_weight/full-system promotion.

Next: inspect RED CI and notify PR259 owner with precise failing lines. Only after ownership release, fix `_action_binding` terminal-status contract and add nonterminal negative control; rerun full suite on integrated head.

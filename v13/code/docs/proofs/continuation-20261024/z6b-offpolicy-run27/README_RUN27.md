# V13 Run27 — off-policy C3-first wake diagnostic (WP-Z6b)

Base PR62 `1f87ed6aa17b137419e903e42f271635883b07bb`. Independent isolated package, no runtime/Canon/AGENTS/learning rights modified. Only new files under Run27; production OFF.

## What changed

`z6b_offpolicy_wake.py` is a runnable, source-Git-blob-bound analyzer of the already-registered 2026-10-22 Z6a dataset. It selects a previously recorded adaptive-arm answer **only when the disabled-arm C3 generated answer contains a deterministic arithmetic contradiction**. It uses no gold label to select. It computes descriptive paired pass counts, wake rate, estimated latency, A3 overthinking fraction and exact sign-test p. It atomically writes a closed, non-overwriting report. It never calls models or wakes a body; it is an *off-policy diagnostic*.

## Evidence and limitations

10/10 new tests PASS, compileall PASS. Tests cover source hash binding, duplicate JSON keys/rows, missing arm, wrong seed, no label leakage, no adaptive-output leakage, atomic non-overwrite and paired sign-test.

Retrospective on the original Z6a 60 generated tasks (read-only GitHub data, JS mirror, sample Python cross-check): disabled 42/60, always-adaptive 39/60, off-policy mixture 44/60 with 9/60 wakes, 1/42 baseline passes woken; estimated time 2.79 s vs disabled 2.38 s. Three prior failures would be replaced by correct adaptive answers, one prior pass replaced by a wrong adaptive answer; exact paired sign-test p=0.625. **No significant or causal benefit**. In a true C3-first runtime the adaptive path is different, and timing cannot be obtained by substitution. This is not a registered prospective experiment and does not promote the failed Z6a gate.

## Next

Implement an isolated live C3-draft capture and a preregistered fresh-seed experiment with a *real* second-stage wake, independent verification, equal budgets and no source/answer label leakage. First confirm current native models, memory and job ownership; no overlapping heavy runs. Preserve original A1–A3 thresholds. Continue other required V13 organs/learning/Context OS, not only effort.

Unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. No Redmi or new native model run. Full checkout/privacy scanner blocked by GitHub DNS in container.

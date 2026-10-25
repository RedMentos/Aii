# Run298 — WorldModel terminal-outcome learning (preregistered before code)

Owner: GPT-6 automation; files owned: `v13/code/v13/world_model.py`, `v13/code/tests/test_world_terminal_outcomes_run298.py`, `.github/workflows/run298-world-terminal-outcomes.yml`, this proof directory. Base: Run296 / PR296 head `2bcb475abcd26e2eef1083f4bf3bde3833dc5196`. Run297 native Context OS owner remains independent; no shared file edits.

## Problem / falsifiable claim
`transitions()` includes observed non-FINAL actions as binary success=0, but `_action_binding()` rejects every non-FINAL status. Consequently a real source-bound Store with otherwise valid, terminal failed actions returns `SOURCE_UNVERIFIED` from `fit()` and cannot learn its success target. This is an implementation bug, not a new gate or model selection.

## Authorized narrow intervention
Use an explicit closed terminal status allowlist `FINAL, ERROR, DEADLINE, CANCELLED` consistently in extraction and source-binding. Keep exact event/source/route/outcome SHA binding, source revocation, numerical constraints, persisted revision, Canon, seed/model hashes, authority and all acceptance gates unchanged. Never admit `DISPATCHED` or unknown status, even if an outcome JSON is present.

## RED / GREEN tests, fixed before code
1. Actual production Runtime/Store SQLite: 24 source-grounded actions, 16 FINAL + 8 terminal ERROR/DEADLINE/CANCELLED with real nonnegative duration and integer output counts. `fit()` must be FITTED, have `n=24`, and load after closing and reopening the Store; failure target contains both 0 and 1.
2. After fitting, changing an ERROR row status or outcome invalidates `load()`; revoking its source invalidates `load()`. Negative: a forged DISPATCHED row with nonnull outcome, and a made-up terminal status, must be excluded from `transitions()`.
3. Existing WorldModel source/chronology/observation/counterfactual tests and focused full regression workflow must remain green; public-repo privacy scan CLEAN.

Evidence scope: **software / actual SQLite Store with synthetic action values**. No model inference, native execution, Redmi, real causal utility or STEP/B3 promotion. Preserve failing RED CI run and final GREEN run; never rewrite history.

Next after GREEN: independent review for status tamper and cross-source controls; then pursue another separate canonical package. No live external actions or paid resources.

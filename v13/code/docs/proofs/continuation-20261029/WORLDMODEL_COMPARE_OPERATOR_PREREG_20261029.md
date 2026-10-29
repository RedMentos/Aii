# World-Model operator four-route counterfactual view — preregistration (2026-10-29)

Parent review checkpoint: `e321d06cac47bcba42030ab87625b2ed192bc96c`
(after #1157 and #1158). Binding Canon unchanged.

## Functional gap
The read-only `:worldmodel event <id> <route>` command requires four
separate manual queries to compare hypotheses for the same observed event.
Expose `:worldmodel compare <Event-ID>` in the existing operator lane. It
must return all four canonical routes as **separate simulations**, without
ranking, selecting, dispatching, approving, learning, or creating an action.
Do not change World-Model fit, revision, confidence thresholds or weights.

## Predeclared checks
- Real isolated Store: 48 observed C5 route actions, fit World-Model once,
  then compare event. Output contains exactly simple/detail/gist/both;
  each action retains `authority=HYPOTHESIS`, `cause=SELF_CAUSED`,
  and its existing support/confidence result. No winner/selection field.
- Existing fitted World state, packet count, action count, learning_mode,
  native pool PIDs are identical before and after.
- Unfitted current-session event yields four honest NO_WORLD_MODEL
  uncertainty entries, not a fabricated prediction.
- Foreign-session and missing event IDs are rejected before any
  World-Model query. Existing per-route and invalid-command tests unchanged.
- Execute focused software CI for operator + World-Model tests, Canon hash,
  privacy scan, compile, diff. Preserve failed attempts/raw logs and SHA256SUMS.
- No native or Redmi claim, no authority promotion, no registered cohort edit.
  STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, LP3 FAIL,
  World-JEPA utility unproven, jepa_weight 0 and full V13 incomplete.

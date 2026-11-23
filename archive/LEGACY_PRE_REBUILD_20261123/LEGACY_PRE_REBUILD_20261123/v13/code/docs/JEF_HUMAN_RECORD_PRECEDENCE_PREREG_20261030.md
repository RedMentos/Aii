# WP-U1 / JEF human RECORD precedence over self-outcome labels — preregistration 2026-10-30

Review-only child of #1184, exact parent `e1e9228318b2152875bd6e5b402f5cf2c50213df`. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Owner: this automation, `v13/code/v13/learning.py`, new dedicated regression tests and workflow only. Independent Body-JEPA typed batch preflight is already under a separate owner's active work; no overlapping edits.

## Expected original RED
`Learner.shadow_readout()` builds `unique` from the newest valid human feedback for every context, but passes only **human LEARN** keys to `jefoutcome.training_rows()`. A later human `record` (or any human `record`) is a veto on learning that context, yet `OUTCOME_SELF_LABEL` reintroduces the same context into the training set when outcome mode is `learn`. This violates the declared lower priority of self-labels and the comment that a newer RECORD revokes prior learning.

## Acceptance
- Real SQLite/Runtime feedback with a JEF `ExecutiveDecision`, recorded self-outcome and explicit human `record` must result in the context being excluded from self-label training. Assert via the **actual** `shadow_readout` call boundary (no optimizer needed; expected insufficient-class refusal), and via `training_rows` on the exact human context key.
- Self-label for a different context with no human feedback remains eligible in outcome `learn` mode; explicit human `learn` takes precedence.
- Original RED must be preserved; source fix must be the smallest bounded change to context suppression, not a broad refactor or new authority.
- Focused `unittest` + relevant existing `test_jefoutcome*`, compile, privacy scan, `git diff --check`, Canon/source hash and raw artifact on both RED/GREEN. Software-only Linux; no native model/Redmi claims.
- Keep `RECORD_ONLY` default, no age promotion, STEP2/B3/Body-JEPA/whole-system gates unchanged. A passing test is not proof of learned utility.

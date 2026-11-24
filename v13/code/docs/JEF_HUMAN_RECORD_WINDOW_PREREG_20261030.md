# JEF WP-U1 human feedback precedence beyond 512-row window — prereg (2026-10-30)

Review-only child of verified #1185 at `5f341acaba4ff37289cde0753448c6b3829f27ec`; separate owner from Body-JEPA typed input work. Source scope: `v13/code/v13/jefoutcome.py` and a dedicated regression, CI and handoff only. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` and all registered model/source cohorts unchanged.

## Original expected RED
The corrected `Learner.shadow_readout` passes every **human feedback key it saw** to lower-priority `jefoutcome.training_rows`, but its feedback query has `LIMIT 512`. An earlier explicit human `record` for a self-labelled context can fall out of that window after 513 newer unrelated human decisions, letting `OUTCOME_SELF_LABEL` re-enter shadow training despite the user's persistent record-only veto.

## Verification and bound
- Real SQLite Runtime: create one FINAL JEF skill self-label and explicit human RECORD for context A, then 513 later legitimate human skill RECORD feedback entries for context B. In `outcomes learn` mode, actual `shadow_readout` must never receive A as self-labelled training input, even when A is outside its 512-row recent-human scan. Original RED retained before source fix.
- Fix at the **self-label admission** boundary: a candidate must be suppressed when any still-valid human `HumanDecision` linked to the exact `ExecutiveDecision` context SHA + revision and head exists, regardless of age in feedback history. Use bounded per-candidate checks (max `MAX=1024` retained self labels), not an unbounded materialization of all feedback. Preserve source revocation and no-human eligibility.
- Tests, compile, privacy, exact source/Canon hashes and closed raw Actions artifact. No native/model/Redmi execution. No Age or gate promotion, and no changes to active learning defaults.

Known limitation to investigate separately: source deletion and historical feedback erasure semantics; do not redesign those in this package.

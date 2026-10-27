# Run645 preregistration — AG4 skill outcome needs actual FINAL receipt (2026-10-27)

Base: Run644-AG5 PR643 head `a9423e26c58f1cd3d9237041a379955c58a6c9e1`. Files owned: `v13/code/v13/agi/live.py`, new `tests/test_run645_skill_credit_receipt.py`, isolated CI/evidence. Do not touch original native C3/Body cohorts, ages, human approval, World-JEPA gates, canonical blueprint or another owner's branch.

## Source counterexample
`agi.live.after_turn` currently calls `g.skills.record(st['skill'], status=='FINAL')` before verifying any persisted same-event assistant answer. This increments AG4 successes even when the caller supplies FINAL without an answer, or a refusal/abstention/reference-only teacher output. The record can influence skill lifecycle/retention, so this is not merely display text. This is a separate issue from Run644's AG5 curiosity signal.

## Acceptance, model-free SQLite
- caller FINAL but no persisted answer -> use 1, success 0;
- persisted leading explicit nonanswer -> use 1, success 0;
- persisted metacog abstention -> use 1, success 0;
- persisted teacher/reference-only FINAL -> use 1, success 0;
- real same-event, same-session nonempty non-abstaining FINAL -> use 1, success 1;
- caller ERROR despite stored FINAL -> use 1, success 0.
No semantic answer correctness claimed. Preserve existing `test_agi_live`, `test_run633_jef_noanswer_goal`, `test_run644_curiosity_receipt` regressions. Keep success credit conservative, no promotion or autonomous age change. Full-suite known baseline is RED due frozen chain fixture drift/import issues; do not hide, falsely promote, or rerun identical full suite without new reason.

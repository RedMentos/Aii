# Run386 / AG4 trusted skill promotion evidence — preregistration (2026-10-25)

Independent owner: GPT continuation. Branch `codex/ag4-skill-outcome-guard-run386-20261025` from verified Run385 checkpoint `9ccdb47750aaf8a6bafb92bc82572d98da964e9f` (stacked PR380→PR379, not main). File ownership: `v13/code/v13/agi/skills.py`, new `v13/code/tests/test_ag4_skill_outcome_guard_run386.py`, dedicated workflow and this proof directory. No changes to frozen cohorts/models/seeds/other owners.

## Defect and risk
AG4 `SkillLibrary.record` currently does `int(bool(success))` and `float(parity)` without validating measurement types or [0,1] bounds. Thus a string `"false"` counts as success and a parity score `2.0` exceeds the 0.95 promotion threshold. Eleven such untrusted reports can auto-promote a USER-origin skill to TRUSTED and influence the live fast route without a genuine full-route parity measurement. NaN/Inf/negative/string/bool parity can also poison persistent history or distort promotion.

## RED-first acceptance
Real Runtime/SQLite tests must show: (1) all non-bool success values (0/1, strings, None, dict/list) rejected as ValueError with zero state writes; (2) parity when supplied is exact int/float, finite, [0,1], bool and numeric strings rejected, and no state writes; (3) failed forged promotion sequence leaves the skill SHADOW with unchanged uses, successes, parity and history; (4) valid bool + parity 0/1 retains CANDIDATE→SHADOW→TRUSTED behavior for USER-origin skills; (5) SELF-origin Age0 skill still cannot auto-promote to TRUSTED; (6) existing `tests.test_growth.G4Skills`, `tests.test_skilllive`, and `tests.test_agi_live` remain green.

No change to promotion thresholds, Age rights, tool approvals, live route policy or learning algorithms. Fix only measurement boundary before `StateBox.mutate`; preserve all negative gates. Source-only Linux/SQLite CI, pinned checkout/actions/deps, exact-head logs and SHA, privacy scan, RED and GREEN raw artifacts privately mirrored after hash/CRC verification. Not native/Redmi, not STEP2/B3/Body-JEPA/jepa_weight or V13 acceptance.

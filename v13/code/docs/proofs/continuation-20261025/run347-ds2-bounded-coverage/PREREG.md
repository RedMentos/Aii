# Run347 prereg — DS2 bounded per-action coverage under hunger constraint (2026-10-25)

Base: Run346 negative lab checkpoint `8bed84c57ca53d1d9018dbc80d0ec4a0959a7331`. Owner: `v13/code/v13/sandbox.py`, new `tests/test_sandbox_ds2_coverage_run347.py`, `scripts/run347_ds2_coverage_bench.py`, Run347 workflow/proofs. Do not modify Run346's immutable seeds 401..420, source/model/cohort hashes, runtime/age/learning/approval/native owners.

## Hypothesis derived from preserved Run346 NOT_SUPPORTED
Existing `lp_goal_novelty` lowers hunger but is worse than `lp_goal` on new-kind KL and only wins 7/20 paired seeds. A global word novelty bonus does not ensure *per-action* coverage of a newly encountered object. Test a **new**, lab-only `lp_goal_coverage` policy: retain the exact LP + existing novelty + hunger pragmatic terms; add a temporary `COVERAGE_BONUS=0.75 * max(0,1 - visits(word,action)/8)` for undercovered action pairs **only when hunger < 0.60**. The bonus naturally expires after 8 real interactions per word/action; no model truth labels or object-name special cases. It may also sample noisy TV initially; the bounded quota limits this cost. Constants are frozen before evaluation.

## Frozen fresh evaluation and acceptance
- **New disjoint seeds 501..520** (20), 1200 steps, new kind at 500; policies `lp_goal_coverage`, `lp_goal`, `lp_goal_novelty`, `lp`; same world per seed. No tuning on Run346 seeds or these evaluation seeds.
- RED-first tests for new policy name, positive undercoverage bonus, no bonus when hunger >=0.60, bonus expires at 8 visits, determinism and finite telemetry. Existing DS1/Run346 tests must remain green.
- A supported lab candidate requires **all** preregistered paired means: new-kind final KL at least 0.02 lower than `lp_goal`, improvement in >=14/20 seeds, new-kind interactions >=5 more on average, mean hunger <= `lp_goal` +0.03, noise share <= `lp_goal` +0.05, final learnable KL <= `lp_goal` +0.03. Otherwise `NOT_SUPPORTED` with raw failure preserved.
- Report 80 per-seed episode rows, exact checks/thresholds, immutable source and bench hashes, exact-head CI, independent ZIP CRC/internal SHA verification and private backup. Synthetic lab only: no AG5/STEP8/learning/age/Redmi/whole-V13 authority.

Next: add RED-first tests/bench/workflow; preserve RED; smallest new policy code; run frozen cohort and checkpoint honestly.

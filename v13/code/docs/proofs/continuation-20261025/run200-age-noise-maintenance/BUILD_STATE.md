# Run200 — Age noise-aware maintenance cross-metric integrity

## Source, scope, ownership
- Base: Run199 PR227 exact head `7fbc99e84835bf6b0aad86b56f1d433bdc427762` (Run199 actual-source CI green). New draft PR228 / branch `codex/age-noise-maintenance-run200-20261025`.
- Owns `v13/code/v13/age.py`, new `tests/test_age_noise_maintenance_run200.py`, dedicated `run200-age-noise-maintenance.yml`, and this proof folder only. No concurrent edits to ContextOS Run198/199, R4 Run195–197, active native B2/C3 owner, Phone, model cohorts, JEF, Canon, learning authority or Redmi.
- Canon v10.16.1 full original blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` untouched. Age `BUILD_CEILING=0` remains untouched; tests use `build_ceiling=5` **only inside temporary SQLite fixtures**.
- This is **software/synthetic Linux GitHub Actions** evidence, not native model inference, learning utility, phone evidence, a new age entitlement, or completion.

## Independently executed RED before fix
- Commit `791c8ea0c9cefe6de178c592588529dafd207d4e`: new tests, **original production AgeControl.record unchanged**.
- Actual full-checkout GitHub Actions `40175438959` / job `121114968823`: **20 tests, 7 FAIL**. Retention and six other independent maintenance failures (stability, calibration, memory_health, safe_self_control, experience, regression_pass) were all incorrectly reported `FAIL_WITHIN_NOISE_BAND` when competence increased.
- Raw failed job log is retained by GitHub Actions at `https://github.com/RedMentos/Aii/actions/runs/40175438959/job/121114968823`. This is a genuine actual-source counterexample; do not rewrite it as passing.
- Intermediate commit `501a6daaf116e221612d2806515fd7d228b10489` introduced literal `\\n` while serializing the patch via connector. CI `40175481012` failed. Corrected in follow-up commit `b1db18c6674cd117ea91af0c75c8cd22b5e15acf`; the failed attempt remains in history.

## Narrow fix and GREEN
- Only change in `AgeControl.record`: competence noise suppression now additionally requires `gate_pass(dict(metrics,competence=1.), current_stage, BAND)`, so *every non-competence maintenance condition must pass*. Existing competence-only noise tolerance remains. No new authority, config, schema, metric, model, native process or background job.
- Corrected production file blob: `988f5d97a5c958d1091c61a1b90824f68f690dfb`; original `d4c38ae344746811fedecff706a9affe9cf8b375`.
- Actual GitHub Actions `40175502447` / job `121115161013`: **20/20 PASS**, including three new tests plus existing `tests.test_age` and `tests.test_age_rights`; Python compileall PASS; official public privacy scan **CLEAN** against exact Run199 base.
- Source-bound CI job log: `https://github.com/RedMentos/Aii/actions/runs/40175502447/job/121115161013`. Focused full source CI `40175502450` launched; outcome must be checked independently.
- Diff scope verified with GitHub compare: 3 files, original base ancestor, no force push. All new bytes must be fetched again after this documentation commit.

## Unchanged negative gates
- STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; DS2 H2 `FAIL`; V13 complete = **false**. No claim of AGI.
- Age-0 default and explicit human approval remain mandatory. Elevated stages in tests are synthetic test-only.

## Next exact step
1. Verify focused CI `40175502450` and remote blob hashes; record any failures rather than concealing them.
2. Independently audit malformed Age evidence (especially `experience=NaN/Infinity` bypassing `gate_pass`, boolean/overrange quality values) in a *separate sequential package*; preregister actual-source RED before modifying `age.py` again.
3. Keep active native owner serialized; after that continue another canonical functional package. No Redmi available here.

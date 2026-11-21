# QA handoff — Age rights and runtime-resource separation

**Updated:** 2026-11-21 18:16 CET  
**Owner:** QA & Android  
**PR:** [#2235](https://github.com/RedMentos/Aii/pull/2235)  
**Branch:** `qa/v14-age-rights-resource-separation-20261121`  
**Current exact head:** `8d3df9ba655597e60f0b542aa252af7ae4d8aca8`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `7a07d01d3f6c9c3a4fb96511ae7decd73c27ccf9`  
**Status:** targeted Age/Lab CI PASS; Python 3.14 staged bootstrap PASS; staged/integrated regression still running at last readback; strict safe-additive gate intentionally blocks automatic integration; DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.

## Canonical contract

V14 master §2.10 separates three dimensions: `official_age`, `lab_age`, and `runtime_resources`. Age controls rights, learning and development. Physical memory, compute, thermal, token and wall-time constraints are independent ResourceGuard/feature-policy decisions. Official Age may remain 0 while X10 exercises already-implemented experimental test rights. The PR does not promote official Age or change device/model/weight state.

## Reproduced defects

1. The staged `LaboratoryAgeControl` adapter already supplies X10 rights while leaving official `AgeControl` unchanged. The effort plan must read rights from that adapter but report official maturity via `system_stage()`.
2. `effort.age_limits()` read `autonomous_effort_max` and `focal_depth` from Age; `effort.decide()` then capped adaptive effort at Age 0. It also used the adapter's virtual `ceiling()` as the reported official stage.
3. `SleepCycle.run()` capped replay batch size using Age-derived `replay_items`, despite the separate Sleep policy and ResourceGuard replay scaling.
4. First exact-head staged CI exposed a composition bug: the Lab-Age overlay expected the old `control.ceiling('system')` anchor after the source had already changed to `control.system_stage()`. The staged build failed before runtime activation.

## Changes on this branch

- `effort.age_limits()` now reports `system_stage()` (official) and reads rights from the supplied controller; it no longer derives compute effort/focal depth from Age.
- Adaptive effort is no longer capped by Age. ResourceGuard, deadline, configuration and feature policy remain the physical constraints.
- `SleepCycle.run()` uses its validated Sleep-policy batch and ResourceGuard scaling; Age still gates whether learning phases are permitted, not replay volume.
- X10 test rights remain distinct from official Age. Tests exercise tool/learning rights, OFF/SHADOW, hard-rule/user-permission/structural/resource vetoes, scoped SHADOW_UPDATE, and unchanged official Age.
- The staged Lab-Age overlay now accepts exactly one of the original anchor or the already-applied expected value. It fails closed on missing, repeated or conflicting anchors; this makes the source composition idempotent without weakening the source blob pins.
- Rebound the exact candidate → recovery builder → integrated stager → runtime deploy SHA-256 chain. Independent readback confirms all four links and the `effort.py` Git blob pin.

## Exact verification

All results below are GitHub Actions CI, not local Linux execution or Redmi proof:

| Workflow / job | Exact result |
|---|---|
| Lab Age control state and WebView truth, run `44926791688` | PASS |
| Laboratory Age two-checkout updater migration, run `44926791674` | PASS; old and new checkout roots both report UPDATED |
| Private owner-read Termux bootstrap, run `44926791650` | PASS; Python 3.14 staged runtime startup and SQLite source-ref job PASS |
| Runtime deployment integrity, run `44926791666` | PASS |
| Staged context/integrated regression — staged-runtime, run `44926791694` | PASS: 251 passed, 10 skipped, 47 subtests |
| Staged context/integrated regression — integrated-regression, run `44926791694` | PASS: 424 passed, 3 skipped, 58 subtests; 6 warnings |
| Reviewed-PR integration queue, run `44926791778` | PASS |
| Strict safe-additive validator, run `44926791620` | **FAIL BY POLICY**: `not a strictly additive PR`; this PR changes existing runtime modules and pinned builders, outside the validator's inert-module/test/handoff scope. Do not bypass. Independent Boss/Core review is required. |

The staged regression initially failed on the already-applied source anchor. After the idempotency fix and complete hash-chain rebinding, the exact current head `dc87281...` passed both staged and integrated suites. No local full Aii checkout was available; `git ls-remote` failed because this runner cannot resolve github.com.

## User-visible effect and limits

If reviewed and later integrated, official Age 0 will no longer reduce the selected compute effort or focal-cycle budget; X10 can grant only its explicitly implemented test rights, while hard rules, user permissions, structural locks and ResourceGuard remain independent vetoes. Sleep replay quantity follows the bounded Sleep policy and ResourceGuard. These paths were exercised in synthetic/staged CI only.

This is not a V14 whole-system completion, not a phone release and not proof of improved native inference, learning utility, B1/B2 delivery or Redmi performance. The last integrated code-bearing release remains `f279286a4453248004c670fcaabecd85da6ab299`. Installed Redmi SHA and updater consent remain UNKNOWN; **REDMI_UNVERIFIED**. No model, weights, permissions, app, SQLite, chats or device data were changed.

## Coordination and next action

- Keep PR #2235 in DRAFT until Boss/Core independently reviews the existing runtime-path changes and resolves builder-file ownership with #2234 and #2231. Do not merge based on CI counts alone.
- #2234 and #2231 were notified of the shared recovery/stager/deployer pin-chain collision and their exact failing CI evidence; each branch must recompute its own full chain after composition.
- No user action, Termux command, UPDATE_REQUEST, model change or device permission change is needed.


## Repository-wide Age-budget consumer audit — 2026-11-21 18:16 CET

**Audit head:** `8d3df9ba655597e60f0b542aa252af7ae4d8aca8`

The Boss review blocker is now answered with an executable AST inventory over live `v13/` runtime modules and `scripts/` builder sources. It enumerates all `.budgets` attribute uses, legacy field reads (`autonomous_effort_max`, `focal_depth`, `dream_seconds`, `replay_items`, `context_edit_tokens`, `exploration_rate`, `own_loops`), and imports/calls of the old AGI budget helper.

### Exact remaining callsites

| Callsite | Classification | Runtime effect |
|---|---|---|
| `v13/age.py: AgeControl.view → self.budgets('system')` | Legacy status/report projection | Exposes the compatibility report; does not constrain compute, wall time, memory, focal cycles or replay |
| `v13/lab_age_runtime.py: LaboratoryAgeControl.budgets → real.budgets(...)` | Compatibility delegation to a fresh earned-Age controller | Deliberately prevents virtual Lab Age from changing the legacy report |
| `v13/agi/base.py: budget(...)` | Removed | No longer provides a path from runtime organs to numeric Age budgets |

No other live runtime or builder module reads the listed legacy numeric fields or calls `.budgets()`. The `age.py` producer still computes its legacy report fields internally; that provider is not a resource consumer. The executable test will fail if a new runtime callsite, field read, helper import or helper call is introduced.

### Residual developmental rights are now named rights

- `agi/curiosity.py`: self-directed practice is gated by `active_info_search`; `exploration_rate` no longer probabilistically throttles a turn or acts as a compute budget. USER-originated practice remains available.
- `agi/goals.py`: non-user goal nesting is gated by `choose_learning_goals`; numeric `focal_depth` no longer caps planning depth. USER goals keep the hard `MAX_DEPTH`; SYSTEM nesting without the right remains shallow; SELF goal creation still requires the right.
- `sleep.py`: replay volume remains Sleep-policy + ResourceGuard controlled; Age gates the learning phase only.
- `effort.py`: compute/focal effort remains independent of Age; ResourceGuard, deadline and feature policy remain the actual limits.

### Exact current CI readback

| Workflow / job | Run | Result |
|---|---:|---|
| Lab Age control state and WebView truth | `44930169527` | **PASS** — `test_lab_age.py`: 13 tests, including the two new behavioral tests and repository-wide AST inventory |
| Laboratory Age two-checkout updater migration | `44930169456` | **PASS** |
| Private owner-read bootstrap + Python 3.14 staged startup/SQLite refs | `44930169409` | **PASS** |
| Runtime deployment integrity | `44930169422` | **PASS** |
| Reviewed-PR integration queue | `44930169447` | **PASS** |
| Staged context + integrated regression | `44930169421` | **IN PROGRESS** at this readback |
| Strict safe-additive validator | `44930169466` | **FAIL BY POLICY** — existing runtime/builder modifications are outside the additive allowlist. No bypass or waiver. |

The full local Aii checkout remains unavailable: `git ls-remote https://github.com/RedMentos/Aii.git` failed with DNS resolution error. No LOCAL_LINUX full-suite result is claimed. The workflow evidence above is CI only.

### Integration and phone boundary

This resolves the requested callsite inventory, but does not authorize automatic merge. Keep #2235 DRAFT until Boss/Core manually review the existing runtime-path and branch-specific builder changes, and until exact staged/integrated CI completes. The current code-bearing release remains `f279286a4453248004c670fcaabecd85da6ab299`; this QA branch is **NOT_RELEASED**. No authenticated private owner-read response has established the installed phone SHA or updater consent; **REDMI_UNVERIFIED**. No UPDATE_REQUEST, Termux command, device action, model/weight change, permission change or user-data mutation was performed.

**User action:** none.


## QA run 11 follow-up — AST callback attribution repaired — 2026-11-21 20:53 CET

**Exact branch head:** `b22129a03bbd3395605b951d55d3f187f442bda6`

The previous exact-head failure was an AST scanner attribution error: `learning_limit()` was inside a nested transactional callback `f(st)` in `GoalStore.add`, but the inventory recorded the callback name `f`. The test now has a separate outer-owner resolver for `learning_limit` calls, while retaining nearest-function attribution for the budget-field inventory. Its negative control proves that `GoalStore.add → f` is attributed to `add`, while a distinct `unrelated → f` closure remains attributed to `unrelated`. No allowlist was widened and no runtime behavior was changed by this QA fix.

### Exact current-head CI

| Workflow / job | Run | Result |
|---|---:|---|
| Lab Age control state and WebView truth | `44943189875` | **PASS** — main suite 14 tests; workflow sub-suites also PASS |
| Private owner-read Termux bootstrap | `44943189926` | **PASS** — includes Lab-Age AST test, dashboard/native-role polling, and real SQLite Store Hi/Test source roundtrip |
| Python 3.14 staged startup and SQLite source refs | `44943189926` | **PASS** — staged startup and Store reference tests |
| Two-checkout updater migration | `44943189854` | **PASS** — 2 tests |
| Offline / offline-bridge-security | current head | **PASS** |
| Staged runtime | `44943189865` | **IN PROGRESS** at this handoff |
| Integrated regression | `44943189865` | **IN PROGRESS** at this handoff |
| Strict safe-additive | `44943189872` | **FAIL BY POLICY** — existing runtime/builder changes are outside the additive allowlist; no bypass |

A separate isolated Python 3.13.5 AST-helper probe passed locally; this is not a local full-repository test. Full Aii checkout execution remains unavailable in this environment. CI evidence above is not Android or native-model evidence.

### Integration status / ownership

Current shared release-development HEAD is `48ded1da27a52fcfba9d1f80fd5086d9ad36a8c4`. This QA branch compares as **42 commits ahead / 110 behind / diverged** from that HEAD. It modifies existing effort, Sleep, AGI and builder/recovery/deployer files. Boss has a separate current-base `learning_rights()` change in #2241, and Core's current-base audio/recovery/stage work is in #2251. Do not merge or blindly rebase this stale branch: compose the Age-rights changes with #2241 and the current Core builder chain, then recompute every nested pin and rerun the exact staged/integrated suite. Keep the branch DRAFT until that ownership/rebase review is complete.

### Device and user boundary

The private owner-read request #433 is still awaiting an authenticated phone receipt; installed SHA/updater state remain unknown. The expired no-reply request #428 was closed and was not replayed. No UPDATE_REQUEST, CHAT_SEND, shell, Termux installer, model/weight change, permission change or device mutation was sent. **REDMI_UNVERIFIED / NOT_RELEASED. User action: none.**

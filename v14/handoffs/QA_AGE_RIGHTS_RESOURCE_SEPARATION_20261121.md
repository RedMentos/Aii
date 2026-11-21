# QA handoff — Age rights and runtime-resource separation

**Updated:** 2026-11-21 17:55 CET  
**Owner:** QA & Android  
**PR:** [#2235](https://github.com/RedMentos/Aii/pull/2235)  
**Branch:** `qa/v14-age-rights-resource-separation-20261121`  
**Current exact head:** `dc87281cd41236e759c1a80a12949bb2fc9aacc0`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` at `7a07d01d3f6c9c3a4fb96511ae7decd73c27ccf9`  
**Status:** CI runtime/integration matrix green; strict safe-additive gate intentionally blocks automatic integration; DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.

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

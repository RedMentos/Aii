# QA handoff — Age rights and runtime-resource separation

**Date:** 2026-11-21 17:18 CET  
**Owner:** QA & Android  
**Branch:** `qa/v14-age-rights-resource-separation-20261121`  
**Initial base:** `a6b2aeaaa6cb92a0948c272c0b099e6265bca487`  
**Status:** implementation candidate; exact-head CI pending; NOT_RELEASED / REDMI_UNVERIFIED.

## Canonical contract

V14 master §2.10 and root `AGENTS.md` separate `official_age`, `lab_age`, and `runtime_resources`. Age is a rights/learning/development envelope; physical memory, compute, thermal, token and wall-time limits belong to ResourceGuard and feature policy. Official Age may remain 0 while X10 exercises already-implemented test rights.

## Reproduced defects

1. `lab_age.right_enabled()` existed but `AgeControl.allowed()` never called it. Consequently `AgeControl.may()` remained official-Age-only and `lab_age.rights_status().newly_testable` could not reflect the requested X10 test overlay.
2. `effort.age_limits()` read `autonomous_effort_max` and `focal_depth` from Age; `effort.decide()` then capped adaptive effort at Age 0.
3. `SleepCycle.run()` capped replay batch size using Age-derived `replay_items`, despite the separate Sleep policy and ResourceGuard replay scaling.

## Changes

- `AgeControl.allowed()` now applies the lab-right overlay only after NEVER, hard-rule, explicit user-permission, structural-lock and resource-mode vetoes. It does not mutate official Age or bypass those gates.
- Age's status profile now exposes developmental signals and explicitly identifies ResourceGuard as runtime budget authority. The legacy `budgets()` name remains a compatibility alias, but no longer supplies runtime resource limits.
- `effort.age_limits()` reads effective rights (including X10) while keeping compute ceilings independent. User effort mode and ResourceGuard remain authoritative.
- `SleepCycle.run()` uses its configured replay batch and ResourceGuard scaling; Age gates whether a learning phase is permitted, not how much compute/replay is allocated.
- Regression tests cover X10 rights, OFF/SHADOW, hard/user/structural/resource vetoes, scoped SHADOW_UPDATE only, unchanged compute effort across Age, and replay batch independence.

## Verification boundary

- Full local Aii checkout: BLOCKED (no checkout; GitHub DNS failure recorded on shared branch).
- Exact-head GitHub Actions: pending at push; no local or CI PASS claimed yet.
- Android/Termux/Redmi: REDMI_UNVERIFIED; no owner-authenticated device receipt, microphone test or runtime update.
- No model, weights, device permissions, installed app, SQLite or user data were changed.

## Next action

Run exact-head Python 3.13/3.14, staged and integrated regressions; repair any real failures without weakening gates. Boss/Core review the permission and resource-separation change before merge. No user action or Termux command is needed.

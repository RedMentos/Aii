# QA handoff — Age rights and runtime-resource separation

**Date:** 2026-11-21 17:35 CET  
**Owner:** QA & Android  
**Branch:** `qa/v14-age-rights-resource-separation-20261121`  
**Initial base:** `a6b2aeaaa6cb92a0948c272c0b099e6265bca487`  
**Status:** implementation candidate; exact-head CI pending; NOT_RELEASED / REDMI_UNVERIFIED.

## Canonical contract

V14 master §2.10 and root `AGENTS.md` separate `official_age`, `lab_age`, and `runtime_resources`. Age is a rights/learning/development envelope; physical memory, compute, thermal, token and wall-time limits belong to ResourceGuard and feature policy. Official Age may remain 0 while X10 exercises already-implemented test rights.

## Reproduced defects

1. The staged `LaboratoryAgeControl` adapter already supplies X10 rights while leaving official `AgeControl` unchanged. The effort plan must read effective rights from that adapter but report the official stage via `system_stage()`.
2. `effort.age_limits()` read `autonomous_effort_max` and `focal_depth` from Age; `effort.decide()` then capped adaptive effort at Age 0. It also used the adapter's virtual `ceiling()` as the reported official stage.
3. `SleepCycle.run()` capped replay batch size using Age-derived `replay_items`, despite the separate Sleep policy and ResourceGuard replay scaling.

## Changes

- The existing staged `LaboratoryAgeControl` remains the only X10 rights adapter; official `AgeControl` is unchanged. `effort.age_limits()` now reports `system_stage()` (official) while reading rights from the supplied controller.
- Legacy Age budget hints remain available for compatibility/status, but the runtime effort and replay paths no longer consume them. ResourceGuard and feature policy own actual compute/replay limits.
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

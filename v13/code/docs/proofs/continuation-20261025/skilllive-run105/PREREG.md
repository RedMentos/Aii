# Run105 — JEF trusted skill route consistency (preregistered)

Date 2026-10-25 UTC. Parent Run104 PR #136 `9f848f4f216d4b2cbca8b4c85e8e8c17a720a079`. Owner: `v13/code/v13/skilllive.py`, new test `tests/test_skilllive_route_consistency_run105.py`, isolated workflow and this evidence folder. No edits to other JEF, C2, Body, Memory, userrules, Callosum, World, LP3 or frozen model sources.

## Real JEF fast-path issue

`_route_only` currently accepts a trusted skill with multiple route steps whenever **the first** step names a valid route. It does not check later route steps for contradictory or invalid values. `SkillLibrary.propose` explicitly accepts multiple declarative steps and does not validate route vocabulary; a human can promote the skill to TRUSTED. `skilllive.automatic` then skips C2_CONTROL and chooses the first route, silently discarding contradictory procedure semantics.

## Expected test-first RED

- A real persisted trusted skill with `simple` followed by `detail` is not eligible for `matches(...,LIVE)` or `automatic`; original behavior selects `simple` and bypasses C2.
- A second invalid route step also prevents automatic bypass.
- Single valid route and multiple identical valid routes retain their existing fast-path behavior.
- Mixed route/tool procedures remain ineligible; SHADOW skill selection never gains authority.
- After restart, the conflicting trusted skill still cannot skip C2.

## Narrow correction

Only treat a procedure as route-only if every step is a route step, all routes are the same canonical route, and each value is a valid string. Do not change lifecycle, user promotion rights, explicit tool gates, or automatic/SHADOW defaults.

## Proof and claim limits

Real SQLite Runtime/SkillLibrary plus model-free JEF fast-path, no native inference or Redmi. Preserve RED logs before fix; GREEN in GitHub Actions full checkout plus existing `test_skilllive`, `test_agi_live`, official privacy scan. No claim of semantic route quality or trained procedural weight consolidation. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.

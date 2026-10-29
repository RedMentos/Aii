# SkillLive ↔ JEF WP-U1 agreeing route correction — preregistration 2026-10-30

Parent review PR #1176 exact verified head `7c940cd385fbb9cfc5c6eb5e961c0ad3209bea3d`. This is an independent cross-organ learning-quality package. Own `v13/code/v13/agi/live.py`, new `tests/test_skilllive_jef_route_correction_20261030.py`, CI and non-promoting evidence delta only. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` and all registered model/source/seed cohorts unchanged.

## Defect
`agi.live.on_feedback(kind='route')` calls `skilllive.on_route_correction` and then **unconditionally** `jefoutcome.on_route_correction`. SkillLive correctly ignores a human correction that agrees with the trusted skill's route; JEF nevertheless rewrites its positive `skill` self-label to `none`. This contaminates JEF's shadow outcome targets and human-agreement report without an actual skill reopening.

## Preregistered RED and positive controls
- Use one real isolated Runtime/Store/SkillLibrary; propose a USER route-only `gist` skill and mark TRUSTED, create a current-chat event and genuine `ExecutiveDecision(skill)`, persist a JEF self-outcome `skill` and delivered FINAL.
- Feed an agreeing human `route=gist` via `memory.feedback` (actual AGI hook). Assert SkillLive stays TRUSTED, JEF self-label stays `skill`, original source ID and state version unchanged.
- Feed disagreeing `route=detail`: SkillLive reopens to SHADOW, JEF flips once to `none`, source ID changes to the typed self-label source; repeated disagreement must not create additional flips.
- Verify same behavior after SQLite close/reopen and no native/model calls; no non-skill label contamination. Existing `test_skilllive` and `test_jefoutcome` remain GREEN.

## Proposed minimal repair
Gate the JEF invalidation on the actual non-null SkillLive `on_route_correction` result. Never flip on agreeing feedback or when SkillLive validation failed; retain direct JEF helper for existing tests. No change to training modes, approvals, route matching, or authority.

## Evidence
Commit this prereg before tests/source. Capture original RED and GREEN exact-head focused CI, complete raw artifact SHA256SUMS/CRC, Canon/source hashes, privacy and diff. Parent #1174 full unfiltered software remains RED on frozen Run34/Run37; no STEP2/B3/Body-JEPA/World-JEPA/native/Redmi/whole-system promotion.

# WP-T6 trusted multi-step route ambiguity — preregistration

**Date:** 2026-10-29. **Exact parent:** PR #1090 source `1aa13abec66eccd2df24942479e1194e826caa5e`. Independent file ownership: `v13/code/v13/skilllive.py`, new tests, this prereg, isolated CI only. No other branch, native model, registered cohort, age or approval gate changed.

## Source observation
`SkillLibrary.propose` permits a skill containing multiple `{'route': ...}` steps. `skilllive._route_only` currently checks that every step contains a route but returns only the **first** route. A TRUSTED skill with conflicting `detail` and `gist` steps can silently skip the C2 executive and select an arbitrary first route. This is not a valid single-route fast skill.

## RED-first behavioral contract
- A single valid route step is automatic-eligible.
- Multiple **identical valid** route steps remain eligible (same final route).
- Conflicting route steps, any invalid route, and any mixed tool/route procedure are **not** automatic-eligible. They must fall back to C_fast and may still be executed through the normal gated skill machinery.
- `matches` must not surface a TRUSTED conflicting-route skill as a live fast route. The existing single-step trusted-route, correction and habit tests remain unchanged.
- Run focused `tests.test_skilllive` + new tests, compile, privacy scan and diff check. This is software-only; no model/native calls. Preserve any unrelated frozen-source full-suite RED, do not modify original source hashes or promote any canonical gate.

## Claim limits
This fixes only ambiguous automatic skill dispatch. It does not prove learned skills, procedural-memory promotion, native C2 reliability, STEP2 utility, B3 L1 or whole-system completion.

# V13 Run28 — WP-T8 World-Model nonfinite/malformed evidence guard

Base: PR63 `4bc67c8a3dab569b4b28f2dab8f711f93b0483ff`, preserving Claude PR38 ancestry. Owner: Codex Run28 isolated candidate under `v13/code/docs/proofs/continuation-20261024/world-run28/`. Production `v13/code/v13/world_model.py` not changed. Canon, original cohort, learning rights, and acceptance gates untouched.

## Independent review and actual bug

The existing world-model transition reader accepted negative action durations/output characters, NaN input lengths, malformed JSON, nonfinite latent values, and nonfinite stored predictor weights. Some crash the fit path; some permit malformed predictions/confidence instead of an honest uncertain result. Original code tested in a local faithful extracted module: 7 adversarial tests RED (4 FAIL + 3 ERROR). A separate invalid `for_event` negative-input test also reproduced a predictor call with an invalid observed state. These are synthetic/software controls, not evidence that real user data is corrupt.

## Isolated candidate

`world_model.py` now validates finite, nonnegative observed input/duration/character counts and timestamps, rejects invalid packet JSON, excludes nonfinite latent state from alignment, and returns `SIMULATION_UNCERTAIN` with zero confidence for invalid counterfactual state/weights/nonfinite prediction. `for_event` rejects invalid stored state before simulation. No fabricated latents, no real-world causal authority, no model self-modification. Valid synthetic 80-transition fit and finite counterfactual still pass.

10/10 local synthetic/software tests PASS; `compileall` PASS. Original red logs and later event red log preserved in local Run28 checkpoint. The current runtime/full suite/privacy scan and actual model/Redmi runs are NOT RUN due connector-only checkout. Source candidate is hash-bound to exact current GitHub original blob and published separately for review; not production-integrated.

## Next

Review the exact remote-source patch, test against real SQLite store with corrupt/mixed rows and validate all existing world-model tests in full checkout; confirm malformed row counts are visible in telemetry (currently excluded without a count). Then preregister genuine observed Self/World outcomes and ablation for G-SELF-WORLD-005 / WP-Z12. The World-Model still represents own digital transitions only; not a proven causal world model.

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; full V13 INCOMPLETE. No rejected Drive destination used.

# Prereg: World-JEPA local SHADOW fit input integrity guard (2026-10-28)

Owner: independent ChatGPT review-only World-JEPA package, branch `assistant/v13-world-jepa-fit-input-guard-20261028` from integrated candidate `c6cc1bf4a4c6b72948494366dad9a3d7670b7ad4`. Frozen active model/seed cohorts, checkpoint formats, optimizer math, learning authority and runtime hooks must not change.

## Reproduced source defect before edit
`v13/code/v13/world_jepa.py` blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760` enters `fit(X,A,X2)` without validating sample count, shapes, finite data, steps or log interval. The covariance loss divides by `n-1`, so a single transition can produce nonfinite values; a zero `log_every` causes a modulo error; mismatched observations/actions may broadcast or fail after optimizer setup. Invalid data must never be treated as fitted SHADOW inference evidence.

## Locked implementation and tests
- At the start of `WorldJEPA.fit`, fail closed with `ValueError` for fewer than two transitions, non-2D or incompatible X/A/X2 shapes, nonnumeric/nonfinite arrays, empty feature/action dimensions, invalid negative/non-int steps or nonpositive/non-int log_every. Bound dimensions to the existing private checkpoint limits (features 1..4096, actions 1..64, transitions 2..100000); do not alter valid training or allow new source authority. Accept existing zeroed/shuffled action controls and `steps=0` for software tests.
- Add deterministic no-model software tests covering each invalid category and valid two-row `steps=0`; confirm rejected input does not initialize a fitted model.
- Run exact-source focused WorldJEPA suite and full software regression, compile, privacy/diff, closed raw SHA256 evidence. No actual native training or Redmi claims.
- Preserve all original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi/full-V13 negative gates; `jepa_weight=0`, World-JEPA remains SHADOW.

Next: audit source-pinned test output and keep separate from registered heldout learning cohorts.
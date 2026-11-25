# Research & Perception — A3 error-gated temporal plasticity shadow (2026-11-25)

## Result

- PR: https://github.com/RedMentos/Aii/pull/2509 (stacked on #2494; draft/experimental status was temporarily changed to ready to start CI).
- Branch: `research-perception/v14-a3-error-gated-plasticity-20261125-run11b`.
- Pre-doc code head: `47de95db5a51541fdc3efee2bfb0ba332a15b544`.
- Code paths: `v13/code/v13/vision_temporal_prediction.py`, `v13/code/v13/vision_temporal_evidence.py`, `v13/code/tests/test_vision_temporal_prediction.py`.
- Actual consumer: the existing consent-scoped `TemporalVisualEvidence` calls the second predictor and exposes its telemetry nested under `a3_temporal_prediction.error_gated_shadow`. A4 reads only the original top-level predictor. No production attention, action, or persistent-weight behavior changes.

## Hypothesis and measured result

A3's default LMS applies a parameter update for every transition. The new optional `ERROR_GATED` shadow updates only when pre-update MAE exceeds `max(1e-8, 0.25 × persistence MAE)`.

LOCAL_LINUX, CPython 3.13.5, isolated predictor mirror:
- `python3 -m py_compile`: PASS
- `python3 -m pytest -q`: PASS, 10 tests
- 2,299 deterministic synthetic observations: ALWAYS 2,299 updates; ERROR_GATED 773 (66.38% fewer)
- ERROR_GATED mean MAE 0.003816 vs persistence 0.012505
- Final 100 old-pattern MAE 0.024976 vs persistence 0.099500
- Quality trade-off against ALWAYS: mean MAE 0.003816 vs 0.003039; final old-pattern MAE 0.024976 vs 0.009499. This is not equal quality; keep shadow-only.
- Eight streams containing both predictors: tracemalloc current 375,824 bytes (~47 KB per pair). Not Android RAM/PSS.

The local harness is an isolated mirror, not the full repository checkout. Full local Aii suite: NOT_RUN / BLOCKED_NO_LOCAL_CHECKOUT.

## Research

Pache & van Rossum, *Mistake Gating Leads to Energy and Memory Efficient Continual Learning*, arXiv:2604.14336v2 (full PDF reviewed; 2026-07-14), *Neural Computation* ahead-of-print 2026-11-05, DOI 10.1162/NECO.a.1602. The paper's actual method is memorized classification-error gating with a Boolean per sample; it reports 50–80% fewer updates but warns pure gating can hurt generalization. Our A3 regression threshold is an exploratory adaptation, not a reproduction. No upstream code was reused because the referenced repo has no LICENSE file.

## CI and integration

- PR #2509 exact-head workflows were IN_PROGRESS at the last poll; no CI PASS is claimed yet.
- Parent #2494 exact focused source-lineage/A3 temporal/frame-ingress workflows were green, but its staged/integrated path still fails at the Core-owned strict source-lifecycle composer rejecting `vision.py`. No Perception pin was weakened.
- No release SHA: NOT_RELEASED.

## Device and updater

Latest authenticated private V13OBS #115 (2026-11-24 09:28:11 UTC): installed `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, pipeline UP_TO_DATE; AI STOPPED_BY_USER, model process STOPPED, native residency UNAVAILABLE. Last user turn 6.295 s total / 2.046 s TTFT / 358 admitted prompt tokens / 7 generated tokens; correctness and semantic use not proven. B1/B2 remain TIME_BUDGET 53.2/54.2 s. Newer b20e9 has 37/37 CI checks but no install receipt. Candidate #2509 is not deployed. A3 real visual input: REDMI_UNVERIFIED.

## Next owner/action

- Core/Integrator: repair/recompose #2494's exact `vision.py` source-lifecycle closure, then rerun staged/integrated/migration/consumer on one exact SHA.
- Research & Perception: after that gate, run source/session-disjoint tests on explicitly consented real visual sequences; compare ALWAYS and ERROR_GATED across static screens, motion, brightness, codec and camera changes; measure parameter deltas, retention, restart and rollback.
- Keep A4 gain 0.15 unchanged; do not switch the default predictor or production weights.
- User action: **keine Aktion nötig**.


## Final branch/readback checkpoint (2026-11-25T19:47:24.064Z)

PR #2509 final documentation/ledger/board head: `47ccf435dcf66350ba6972b36a5df05341715256`. Exact-head runtime deployment and frame-ingress workflows SUCCESS; A3 temporal calibration, source-lineage and staged/integrated workflows IN_PROGRESS at last poll. Do not mark the PR accepted until all jobs and the shared source-lifecycle integration gate are resolved.


### Exact-head CI completion — tested code SHA 6523b8c3c5e0b9b164023e63a190c2012fed07c9 (2026-11-25T19:50:27.191Z)

- A3 temporal calibration / RAW EAR interval integrity: 74/74 PASS on Python 3.13.18 and 3.14.10.
- MediaProjection RAW EAR frame ingress: 55/55 PASS on Python 3.13.18 and 3.14.10.
- Vision source-lineage / forget regressions: 39/39 PASS on Python 3.13.18 and 3.14.10.
- Runtime deployment integrity: PASS.
- Staged runtime: FAIL, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests passed; strict source lifecycle lock rejects `vision.py` at `scripts/source_lifecycle_lock_integration_candidate.py:172` with `unsupported lifecycle source`.
- Integrated regression: FAIL, one failure at the same inherited Core-owned `vision.py` pin. This is not a failure in the new A3 unit/consumer tests; it prevents whole-runtime acceptance.
- PR #2509 returned to DRAFT. It remains stacked on #2494 and NOT_RELEASED. Code-tested SHA is 6523b8; subsequent commits, if any, are documentation/board only.

No user action required. Core/Integrator owns the source-lifecycle rebind; Perception will not weaken the exact pin.

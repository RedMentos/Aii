# Research & Perception Run 82 — A4 delayed-outcome calibration

- **Date:** 2026-11-28
- **Run start:** UNKNOWN
- **Checkpoint:** 2026-11-28T03:13:06Z (exact-head CI completion)
- **Owner:** Research & Perception
- **PR:** https://github.com/RedMentos/Aii/pull/2579 (DRAFT; stacked on #2578)
- **Branch:** research-perception/v14-a4-multihorizon-effect-20261128-run81
- **Code/test head:** c87f326e128f814b756c842550b4630204e5beff
- **Documentation checkpoint:** 99c6261e66286e17e6774e44c47b7fed27f0ed07 (six-file readback verified; this handoff is included in that commit)
- **Release:** NOT_RELEASED
- **Device:** REDMI_UNVERIFIED

## What changed

The A4 multi-horizon update-effect study now separates six training sessions, three calibration sessions and three held-out regimes. It uses three disjoint training replay anchors, two separate calibration anchors and two held-out replay anchors. For each 1/3/8-window head it compares an absolute-residual P90 abstention margin with a negative-score P90 cutoff fitted only on disjoint calibration examples whose delayed outcome is non-positive.

The experiment computes each candidate's worst replay-retention cost once and reuses it across the three horizon labels. The production A4 temporal predictor remains imported as the experiment's candidate consumer. No production gate, Runtime default, model, weight, permission or device state changed.

## Exact evidence

### GitHub Actions — exact code/test head

- A4 update/retention workflow #46101601310: **PASS** on Python 3.13 and 3.14. Each interpreter: py_compile; 10 A4 retention tests; 8 corrected one-step tests; 9 multi-horizon tests; 54 production audio-temporal-predictor pytest tests.
- Frame ingress #46101601316: **PASS**.
- RuntimeDeploy offline integrity #46101601271: **PASS** (CI integrity only; not a deployment).
- Model-lab #46101597792: **PASS**.
- Private-bridge regression #46101597774: **PASS** (not a private phone receipt).
- Duplicate push-triggered A4 run #46101597767 also completed PASS. Docs-only head e52 rerun #46102156355 PASS on Python 3.13/3.14 with the same 10 + 8 + 9 + 54 test counts.

### Measured synthetic calibration

| Horizon | Training examples | Calibration examples | Residual-P90 coverage | Residual-P90 recall | Negative-score-P90 FPR | Negative-score-P90 recall |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 313 | 157 | 90.45% | 0% | 9.60% | 18.75% |
| 3 | 313 | 157 | 90.45% | 0% | 9.26% | 2.04% |
| 8 | 313 | 157 | 90.45% | 0% | 10.00% | 67.16% |

Both joint 1/3/8 gates selected **0/74 smooth**, **0/16 abrupt** and **0/69 abrupt-to-smooth** candidates. Utility and worst-anchor retention deltas versus the synthetic NO_UPDATE reference were both zero. The negative-score threshold improves per-horizon recall relative to the residual margin, but the all-horizon intersection still abstains throughout. This is a negative result; do not lower thresholds simply to manufacture updates.

## Local, device and integration limits

- LOCAL_LINUX: CPython 3.13.5 x86_64 helper-only quantile/residual/negative-score sanity assertions **5/5 PASS**. These are not the exact experiment or production predictor.
- Full local Aii checkout / repository pytest: **BLOCKED / NOT_RUN**. No checkout is mounted; GitHub DNS resolution fails in the local container.
- Shared staged/integrated #46095100443 remains FAIL on Core-owned Recovery composer/arithmetic/observer pins and QA migration PARTIAL-vs-UPDATED assertions. Boss/Integrator must choose #2578/#2579 convergence ancestry.
- Last available private V13OBS #115 is historical (2026-11-24 STOPPED_BY_USER). Read-only requests #1043 HEALTH, #1044 PIPELINE_STATUS and #1045 DIAGNOSTICS returned NO_LIVE_RECEIPT. REDMI_UNVERIFIED; updater UNKNOWN; no UPDATE_REQUEST, CHAT_SEND, shell, microphone action or device operation.
- No release SHA. GitHub push/CI is not deployment.

## Research note

R-196 was upgraded from abstract-only to a full arXiv HTML main-text review of Pache & van Rossum, Mistake Gating Leads to Energy and Memory Efficient Continual Learning (arXiv:2604.14336; peer-reviewed Neural Computation ahead-of-print 2026-11-05). Its memorized-mistake mechanism is classification/sample-ID based, not equivalent to A4's continuous acoustic regression. The official repository inspected at vanrossumlab/mistake-gating26 had no LICENSE file; no code was reused. R-200 and R-201 remain abstract-level only.

## Next executable step

Keep both gates research-only. Test a preregistered two-of-three horizon consensus or uncertainty-weighted aggregation using the same disjoint sessions and replay anchors. Require positive held-out current-task utility and non-worse worst-anchor retention. Any persistent update still requires the exact deployed C0 and source-bound held-out outcomes.

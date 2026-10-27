# WP-Z12c action-support / OOD / calibration — closed synthetic result

2026-10-27 UTC. Review-only PR #751, child of #749, base `bfeee06983a9a3bf7a00fd525c036c234b429fb0`. Prereg `7072861f8e83543656820a02a8f7d748d5f24ff7` was remotely verified **before** evaluator/tests/workflow. No World-JEPA source/model/runtime changes; frozen model Git blob `5ffd56097e66a37e2922e39d1dc0ba86cb28a760`.

## Closed raw evidence
GitHub Actions run **40557772288** SUCCESS, PR event, exact checked-out merge source `e2fa1b42f9f7382e1f7daa2569a19ccaf59e0164`, evaluator blob `3722706f07b025dd4449ef18b6dd7c0f2a4d9c92`, original World-JEPA blob above. **21/21 focused software tests PASS** in 2.647 s. INSTALL/UNIT/MEASURE/COMPILE/PRIVACY/DIFF raw exits all **0**; privacy scan CLEAN. ZIP artifact ID **12756943391**, SHA256 **`a9f16341da017f163f3742019ff76d247e2c55b6cd80f51269d401ac35d43291`**, CRC PASS (16 entries). Raw `RESULT.json` has 193 seen-action and 47 withheld-action rows per seed. Independent raw ZIP verification recomputed per-seed means, medians, bin counts and ECE from per-row records and confirmed the withheld labels; all matched exactly to float tolerance.

**Private durable backup**: original raw ZIP copied to Library `/V13-Checkpoints/2026-10-27/Automation11U-World-Support-Calibration/world-support-40557772288.zip`, re-materialized and byte-compared SHA256 identical. Rejected anyone-writable Drive destination not used. Public repo contains only synthetic code, aggregate metrics and hashes, not private raw data.

## Preregistered measurements
Training actions 0/1/2 only: 761 rows, SHA256 `8a70c57a6f2b5b4dc10fe033abea3a89335b0fc8023f14cbdeb3ae5f75ea82ee`; heldout seen 193 SHA256 `2d8ebecb798da993df692ad8e38e362b248e9b81cdff0645a05545bc8d69618f`; heldout withheld action3 47 SHA256 `95eaaafc88454ff59fbab90f3f7a9daf0d3aec5b455246ab8c316a9f8e303e0b`. Original full-source hashes unchanged. Seeds 3/7/11, ensemble 3, 1000 steps, NumPy 2.2.6.

| Seed | Withheld action3 confidence=0 | Seen median confidence | Shifted +8 state median | OOD <= half | Diagnostic ECE proxy | Spearman(conf, -error) | Seen success vs train q75 |
|---|---|---:|---:|---|---:|---:|---:|
| 3 | 47/47, PASS | 0.632086 | 0.217275 | PASS | 0.179700 | +0.128400 | 0.450777 |
| 7 | 47/47, PASS | 0.651170 | 0.233956 | PASS | 0.125122 | -0.027671 | 0.523316 |
| 11 | 47/47, PASS | 0.660982 | 0.278725 | PASS | 0.152560 | -0.018467 | 0.502591 |

Preregistered **withheld-action gate PASS** and **state-OOD half-confidence gate PASS** on this narrow synthetic source. The observed confidence/error rank correlations are near zero, including two slightly negative seeds; the heuristic confidence **is not shown to be calibrated to actual prediction success**. ECE values are diagnostics only, not a calibrated probability or safety certification. Withheld-action prediction quality is not validated by zero confidence; zero confidence correctly marks unsupported extrapolation.

## Boundaries / next
Synthetic target is model's own EMA latent, not independently grounded real-world outcomes. World-JEPA remains SHADOW and not wired to the V13 runtime. No native LLM, no real environment intervention, no Redmi. LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, BJ1 NO_SIGNAL, STEP2 UTILITY_FAIL, B3 L1 FAIL, `jepa_weight=0`, Age authority 0, whole-system incomplete. No main merge. Independent code review and full suite remain pending; do not promote any canonical gate.

Next substantive work: test calibration against externally validated state transitions, or design bounded SHADOW-only world-state event wiring under existing Age and action gates; separate preregistration required. Separate sibling PR #752 reviews a discovered negative-index scorer defect in prior PR #749; do not mutate original cohort or evidence.

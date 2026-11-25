# Research & Perception Run 12 — A3 hysteresis plasticity shadow

Date: 2026-11-25
PR: #2509 (draft, stacked on #2494)
Code checkpoint before this append: e9731237057fbf9df8805396960a690fae68e76c

## Implementation

- Added ERROR_HYSTERESIS to A3TemporalPredictor.
- Separate persistence-relative open/close thresholds: open at 0.10, close at 0.05.
- Added gate state, transition count and relative-error telemetry.
- Wired a third ephemeral predictor into the existing TemporalVisualEvidence consumer.
- Output is nested as a3_temporal_prediction.error_hysteresis_shadow.
- Existing ALWAYS predictor and A4 novelty path remain unchanged; A4 ignores both nested ablations.
- Stream reset, unavailable/projector-change and consent-revocation reset the third predictor as well.
- No raw frames, images, persistent weights, model swaps or Android actions.

## Research and experiment

Sawada & Tani, arXiv:2608.23000v2 (2026-08-24), is only abstract-reviewed here; full primary text could not be retrieved. The accessible abstract supports online plasticity scaled by a variational-free-energy mismatch signal with no offline pretraining/replay/task-boundary signal. The Pith structured review is secondary and machine-generated. We do not equate A3 MAE with variational free energy and do not claim to reproduce FEGP.

The reproducible script v14/experiments/a3_hysteresis_plasticity_ablation.py uses 20 training seeds and 20 held-out seeds, 1,799 synthetic observations per stream, three generated patterns and A→B→C→A return. Thresholds 0.10 / 0.05 were selected on seeds 0–19 and evaluated on 20–39.

Held-out mean results:
| Policy | Updates | Mean MAE | Final old-pattern MAE |
|---|---:|---:|---:|
| ALWAYS | 1,799 | 0.00600822 | 0.01783551 |
| ERROR_HYSTERESIS | 1,564.35 | 0.00601103 | 0.01788599 |
| Periodic 7/8 updates | 1,575 | 0.00621328 | 0.01925348 |
| Matched average LR 0.26051973 | 1,799 | 0.00627414 | 0.01927936 |
| ERROR_GATED | 1,207.65 | 0.00655297 | 0.02455583 |

Hysteresis used 13.04% fewer updates than ALWAYS, with a very small held-out MAE/retention difference. This is a synthetic candidate trade-off, not evidence of better real perception or energy savings on Android.

Memory: third predictor added 495,240 bytes across 16 warmed streams (~30.95 KB/stream) under CPython 3.13.5 tracemalloc. This is not Redmi RSS/PSS.

## Tests and blockers

- LOCAL_LINUX CPython 3.13.5 / pytest 9.0.2 isolated copy: py_compile PASS; 5/5 focused tests PASS.
- Full local Aii checkout and full project suite: NOT_RUN (no repository checkout mounted; GitHub DNS unavailable).
- Exact PR CI on code head e973123...: A3 temporal calibration PASS; MediaProjection frame ingress PASS; runtime deployment integrity PASS; source-lineage and staged/integrated IN_PROGRESS at last poll. Do not claim the latter passed.
- Parent chain staged/integrated still fails at the Core-owned strict vision.py source-lifecycle composer. No pin was weakened.
- No native camera/MediaProjection test, Android/Termux/Redmi benchmark, native visual encoder, persistent weight update or B3 proof.

## Device, release and next owner

Latest available private V13OBS #115 is historical (2026-11-24 09:28 UTC): auto-update enabled, installed 8d93236, but AI STOPPED_BY_USER and model process STOPPED; no newer authenticated receipt is available. No update request, restart, CHAT_SEND, LOG_PAGE, model/weight/permission change or data mutation was performed.

Release: NOT_RELEASED. Redmi: REDMI_UNVERIFIED. B3: OFF. P0 basic chat and B1/B2 delivery remain open.

Next: Core/Integrator owns the exact vision.py source-lifecycle recompose. After staged/integrated gates are green, Perception can run this comparison on explicitly consented real visual sequences with source/session-disjoint holdouts, static/motion, brightness/codec/camera controls, retention and restart/rollback. Keep the third predictor shadow-only and A4 gain 0.15 unchanged until then.

User action: keine Aktion nötig.


## Run 12 correction — absolute residual floor and matched-update control

The first gate version used only a residual ratio. Review showed that with a zero persistence baseline, an arbitrarily tiny residual could open the gate. The code now requires:
- open: model MAE >= max(1e-8, baseline MAE × 0.10)
- close: model MAE <= max(1e-8, baseline MAE × 0.05)

The negative control verifies that 1e-9 against a zero baseline stays closed, 2e-8 opens, and 1e-9 closes again.

The periodic matched-update control is now 3/4, matching the corrected training update fraction (~0.738). Held-out results (seeds 20–39):
| Policy | Updates | Mean MAE | Final old-pattern MAE |
|---|---:|---:|---:|
| ALWAYS | 1,799 | 0.00600822 | 0.01783551 |
| ERROR_HYSTERESIS | 1,329.35 | 0.00601103 | 0.01788599 |
| Periodic 3/4 updates | 1,350 | 0.00649146 | 0.02110532 |
| Matched average LR 0.22131462 | 1,799 | 0.00656588 | 0.02101027 |
| ERROR_GATED | 1,207.65 | 0.00655297 | 0.02455583 |

This is still synthetic generated data. The difference versus ALWAYS is small and does not establish real visual utility or Android energy savings.

Exact CI for the preceding code head 3dfd657: A3 80/80 on Python 3.13.18 and 3.14.10; frame ingress 55/55 and source-lineage 39/39 on both; runtime deployment integrity PASS; staged/integrated FAIL at the Core-owned strict vision.py lifecycle pin. This correction needs a new exact CI run.


## Run 12 research extension — R-155 Update-Effect Predictor

Full 45-page primary PDF reviewed: Yi Ren, Wenlong Deng, Guanzhe Hong, Clare Lyle, Yarin Gal, arXiv:2609.33620 (2026-09-27), preprint. The paper derives forward-computable token-level CH1/CH2 interaction estimates from logits/token forces, hidden states and shared readout; it also defines task-conditioned readout transmission R_D to diagnose future learnability. It distinguishes high-energy collision from cumulative low-energy erosion and reports OOD-specific readout transmission decay during long-horizon PubMed training.

Critical caveats: first-order/local estimate; identity-path residual approximation; SGD derivation with incomplete AdamW history/decoupled-decay treatment; Transformer shared-readout scope (not MoE/circuit-level); signed CH2 unreliable at cold start until a brief warm start. Top-K vocabulary and selected layers can reduce O(ndL) cost.

The author OSS tree has no LICENSE file, so no code was reused. The paper is not an Android/Redmi measurement. The current #2510 tokenwise tap path does not expose the logits, target token forces, final hidden states, selected layer states and readout needed for CH1/CH2/R_D. Next cross-lane implementation is a source-bound native Update-Effect tap and a tiny-model exact-gradient parity harness; keep production JEPA update selection OFF until holdout/retention/rollback passes.


## Run 12 negative control — unpredictable noise

A five-seed generated white-noise sweep (1,799 observations/seed, 16 tile dimensions, amplitudes 1e-5, 1e-4, 1e-3 and 1e-2) showed 100% post-warmup update fractions for ALWAYS, ERROR_GATED and ERROR_HYSTERESIS. The hysteresis gate opened once and remained open. This is a material limitation: the current residual ratio cannot distinguish unpredictable sensor noise from useful novelty. The 1e-8 floor is only a numerical guard, not a camera noise calibration. The new test locks in this negative result. Do not promote the shadow on live camera/audio streams without source-specific noise-vs-signal calibration and held-out controls.

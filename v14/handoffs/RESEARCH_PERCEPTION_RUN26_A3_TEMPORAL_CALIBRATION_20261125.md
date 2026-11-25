# Research & Perception handoff — Run 26 (2026-11-25)

**Run window:** started 2026-11-25 05:01 Europe/Berlin; completion timestamp UNKNOWN.
**Owner:** Research & Perception.
**Branch:** `research-perception/v14-a3-temporal-calibration-interval-guard-20261125-run26`.
**PR:** [#2486](https://github.com/RedMentos/Aii/pull/2486), DRAFT, stacked on [#2470](https://github.com/RedMentos/Aii/pull/2470).
**Last known branch commit before this handoff file:** `2dfe1dcb017507b680f892ca688171a80aa5edf9`. The handoff-file commit will advance the PR head; use GitHub readback for the final SHA.

## Product changes

1. **RAW EYE visual interval ordering:** `TemporalVisualEvidence` now stores the previous start and end. A new interval is rejected if its start moves backwards, even if its end increases. Equal starts remain valid for cumulative/overlapping windows. Rejected updates do not advance either baseline.
   - Code commit: `092bdaeaae0d4be63c922901a15ad395b2d84533`.
   - Canon path: A5 visual/UI temporal provenance and RAW EYE frame sequencing.
   - Runtime effect: prevents a stale/out-of-order visual interval from being admitted into temporal evidence and affecting later gap/decay calculations.

2. **A3 temporal calibration diagnostic:** `v14/experiments/vision_temporal_calibration.py` uses the current A3 projector callback and source-disjoint fold helper. It calibrates a per-transition diagnostic threshold from training-source feature-noise controls and evaluates held-out stable/change transitions, random frame permutations and exact reversal.
   - Module commit: `86f060da0cde683d84f4cd6409cebc7a5cbb6559`.
   - Calibration test commit: `b1199fe43dff18404d3380555ac631b3b559cec5`.
   - Interval test commit: `f0b78b32ecc0f6f2b0840628be789c4dedcb8639`.
   - Workflow initially created at `4c1fae49ae39d69e690866421c4692fe45a8f117`, Actions-expression correction `1a97d1b98cf024f4ed082dd93d9a01361b8a97e4`.
   - No threshold is persisted or consumed by Runtime. No weights or raw frames are persisted.

## Tests and evidence

- **LOCAL_LINUX isolated harness:** 7/7 PASS on CPython 3.13.5, NumPy 2.3.5, pytest 9.0.2.
  - 4 calibration tests: source-disjoint split, deterministic feature-noise/shuffle controls, invalid-shape/label/noise/zero-projector negative controls, insufficient-source rejection.
  - 3 interval-order tests: backward start rejected while end advances, equal-start cumulative windows accepted, failed end/start ordering leaves the baselines unchanged.
  - Boundary: these tests used a local stub for the existing A3 projector/fold helper and an isolated visual interval state-machine reproduction. They do not constitute an exact full-repository execution.
- **LOCAL_LINUX full Aii checkout:** BLOCKED / NOT_RUN. No checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git HEAD` failed because GitHub DNS resolution is unavailable.
- **Exact-head CI:** at the first readback, the following runs were QUEUED, not PASS:
  - `45546003192` — new A3 temporal calibration / RAW EYE interval workflow.
  - `45546003212` — existing MediaProjection RAW EYE frame ingress.
  - `45546003205` — vision source-lineage / forget regressions.
  - `45546003231` — staged context and integrated regression.
- Parent #2470 focused frame-ingress CI is 54/54 PASS on Python 3.13 and 3.14. Its staged A5 UI lease integration still FAILS because Core's source-lifecycle composer rejects the current `vision.py` source pin (`unsupported lifecycle source: vision.py`), tracked by #2465.
- **RELEASE:** NOT_RELEASED. #2486 is a draft child PR, not an integration/release SHA.

## Real-device and updater boundary

Latest available consented private V13OBS #115 snapshot: 2026-11-24 09:28 UTC. It reports installed release `8d93236c753f0194224c19edc7411d8d7082b1d6`, auto-update enabled, but runtime `STOPPED_BY_USER`, model process STOPPED, and zero valid B1/B2 offers. No newer authenticated device receipt was available at the initial check.

A read-only DIAGNOSTICS relay request was created privately as RedMentos/Aiiii issue #891 with a 600-second expiry. No shell, CHAT_SEND, UPDATE_REQUEST, restart, permission change, model/weight swap, log-page read or user-data access was performed. Until a device reply is read back: **REDMI_UNVERIFIED / current updater state UNVERIFIED**. The historical snapshot's auto-update-enabled flag is not current deployment proof.

## Research

R-139 records the full ThinkJEPA paper and OSS/license review. The paper's dual-temporal dense JEPA + sparse VLM guidance is architecturally relevant, but the public release expects Qwen3-VL-2B-Thinking, V-JEPA2 ViT-L, CUDA 12.8 and two H200 GPUs for the documented 200-epoch run. Its root code license is custom `LicenseRef-ThinkJEPA-Attribution`; upstream model weights retain separate rights. No code or weights were imported. It is RESEARCH_ONLY / NO_REUSE for Redmi.

Synthetic calibration metrics with identity projector:
- held-out feature-noise FPR: 0.05
- held-out stable-transition FPR: 0.00
- held-out changed-transition TPR: 1.00
- shuffled score >= ordered score: 0.6125 of transitions
- exact reversal score error: 0.0

Interpretation: the current symmetric A3 score detects pairwise change, not semantic temporal order. Random permutation can score higher than the original sequence. This supports retaining it as capped A4 novelty only; it is not a JEPA dynamics predictor or proof of temporal understanding. Feature-space noise is not pixel/camera/codec noise.

## Next executable work

1. Read back exact-head CI for #2486 and fix any failures; do not treat queued runs as PASS.
2. Core/Integrator composes the exact #2465 `vision.py` source-lifecycle pin chain and reruns staged/lease/integrated tests.
3. Perception runs the calibration protocol on explicitly consented real visual sequences with source/session-disjoint holdouts, codec/brightness/camera perturbations and stable/no-change controls. Only then consider a calibrated A4 novelty cap.
4. Keep P0 #1904 open: correct basic chat, valid B1/B2 OfferPacket delivery, and trained cross-organ latent exchange remain unproven.
5. No user action is required; do not issue a manual Termux command or change models/weights.

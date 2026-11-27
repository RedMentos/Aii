# Research & Perception handoff — Run 58 (2026-11-27)

## Execution record

- Start: 2026-11-27 04:55:13 Europe/Berlin (provided run start).
- End: UNKNOWN at handoff creation; work continued through the current tool session.
- Product branch: `research-perception/v14-a5-visual-frame-bridge-20261127-run58`.
- Parent integration branch: `core/v14-perception-rebased-runtime-20261127-run5`, head observed at start `2f348c4aaeabacbaaa988ff53d49484507ab9868`.
- Perception PR: [#2550](https://github.com/RedMentos/Aii/pull/2550), draft, stacked on Core PR #2549.
- Code/test checkpoint: `7dd720a2669e46e4965c3766c6e3fcd2849bc89f`.
- Latest docs checkpoint: `96b8449476a77eee0c75894988dfb0d185178d5b`.
- No master blueprint or historical V13 canon bytes were edited.

## Work completed

Added `v13/code/v13/a5_visual_frame_bridge.py`:

1. Reuses the existing `validate_ui_observation` and `UIObservationLease`; accepts only `MEDIA_PROJECTION / SCREEN_FRAME_AVAILABLE` with a live source/session/receipt/generation lease.
2. Decodes the supplied frame in memory and runs existing `vision.features()` RAW-EYE extraction.
3. Optionally uses an already-installed `hashed_bow` student projector. Candidate captions are explicitly `STUDENT_ESTIMATE / REFERENCE_NOT_FACT`; no teacher model is loaded.
4. Emits a visual `PerceptPacket`, invokes the existing A4 attention controller with `file_requests=False`, and sends a bounded `Percept` to `PerceptAdmission`.
5. Exposes packet and derived feature vector only while the same lease is active. Provider revocation and lease exit clear adapter caches; adapter-held feature arrays are best-effort zeroed.
6. No raw screenshot, feature vector, transcript or source blob is persisted. Provisional frames are ignored before decode. Action and learning authority remain false.

Added `v13/code/tests/test_a5_visual_frame_bridge.py` and `.github/workflows/v14-a5-visual-frame-bridge.yml`.

## Exact evidence

- Hosted Linux, Python 3.13: **6/6 PASS**.
- Hosted Linux, Python 3.14: **6/6 PASS**.
- Inherited offline-bridge security workflow: **39/39 PASS**.
- Local Python scratch: **4/4 PASS** for PNG decode, finite compact descriptor, distinct raw/feature hashes, and adapter-style cache clearing. This was not the Aii repository test suite.
- Full Aii checkout is not mounted; network clone is unavailable. Exact repository tests were therefore not run locally.
- Earlier test failure: the initial test assumed the Store had no unrelated blobs. It was corrected to assert that the exact frame SHA is absent from source rows and blob names; current code/test SHA passed on both Python versions.
- Core PR #2549 staged-runtime and integrated-regression checks were still in progress at the last observation. Do not infer their result from this focused A5 gate.

## Product effect and acceptance boundary

Evidence classification: `WIRED_SYNTHETIC`.

The adapter establishes a tested local A5 MediaProjection-frame → RAW-EYE → A4 attention → PerceptAdmission path under a revocable lease. It is not the Android capture provider and is not yet called from the normal Runtime turn. Core must invoke `A5VisualFrameAdapter.context(event_id, grants)` and `features(event_id, grants)` while the same lease remains open, then prove revocation cancels downstream C3 work before lease release.

No real Android API call, OS consent receipt, AccessibilityService, device screenshot, Redmi measurement, native latency/RSS, or B1/B2/C3 visual inference is proven. `REDMI_UNVERIFIED`; `NOT_RELEASED`. No installed model, weight, permission, updater setting or device data changed.

## Research

- Hess et al., arXiv:2608.18803, first posted 2026-08-19 and listed on the official CoLLAs 2026 accepted-papers page: co-observation is a distinct representation-learning factor beyond forgetting and plasticity. In their moderate-scale vision experiments, ~15% replay matched an ensemble retention baseline and ~30% surpassed it; distillation tracked retention but did not restore the same co-observation benefit. The paper does not prove the same effect for small audio cue predictors or Android.
- `TimmHess/Co-ob` is MIT, but its README documents vendored/patched Avalanche and a separate CaSSLE fork; requirements are CUDA/PyTorch-heavy. No code was copied.
- Official Android MediaProjection documentation (updated 2026-11-19): API 21 introduction, API 34 app-window capture, per-session user consent, one-use projection token / virtual-display creation, foreground service type on Android 14+, and mandatory `onStop()` cleanup for stop/lock/process termination. The Python adapter assumes the provider already handles those OS duties.
- A separate scratch LMS replay simulation showed only a small synthetic MAE reduction (~0.0076–0.0081) on three streams; non-speech remained worse than persistence. This is hypothesis-generation, not a repository or real-audio result. A4 replay is not enabled.

## Files updated

- `v13/code/v13/a5_visual_frame_bridge.py`
- `v13/code/tests/test_a5_visual_frame_bridge.py`
- `.github/workflows/v14-a5-visual-frame-bridge.yml`
- `v14/V14_WORK_BOARD.json` (new V14-023 and Perception checkpoint)
- `v14/V14_USER_NEXT_ACTION.md`
- `v14/V14_LIVE_WORKPLAN.md`
- `v14/V14_CANON_COVERAGE_INDEX.md`
- `v14/V14_RESEARCH_LEDGER.md`
- this handoff

## Next executable work

1. Core: wire the adapter into the normal Runtime turn under the same MediaProjection lease; ensure context/features are consumed before lease exit and revocation cancels C3.
2. QA/Android: implement and test the OS provider, API 21+/34+ branches, single-use token, foreground service, rotation/resize, `onStop()`, status-bar stop, lock-screen stop and cancellation.
3. Perception: add source/session-disjoint visual holdouts; continue A4 omission false-positive work; only then prototype bounded, consent-scoped co-observation replay with no raw PCM.
4. Verify private HEALTH / PIPELINE_STATUS / DIAGNOSTICS receipts separately. Until they arrive, updater/install state is unverified for this run.

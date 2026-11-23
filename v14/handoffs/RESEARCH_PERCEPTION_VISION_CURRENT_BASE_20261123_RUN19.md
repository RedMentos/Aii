# Research & Perception — A3 source lineage / RAW EYE current-base handoff

**Date:** 2026-11-23  
**Release-development base:** `gpt6/v13-private-remote-bridge-20261111` @ `fb563d771fe2d493c4ec25abe94280981d24ef5c`  
**Branch:** `research-perception/v14-vision-lifecycle-current-20261123-run19`  
**Base implementation commit:** `f2fef9be34e2147e424a153114226c548cbda359`  
**Temporal extension commits:** `b63377bdbaf42ffa5afc0496e1c428ed3111412d` (module), `9c324c650e7b8d4bcd69db5e99bc83d89d7b9b50` (A4 wiring), `0a6bcd87c6253ede049b84a315b13cd7920f1547` (tests), `25512ff5b16fe3b762926c3ac1caa89346e7f3d0` (revision), `a0d11c715f217f4b6a6d9ec4884c7eea27bddb3e` (end-of-stream cleanup test).  
**Current branch head:** `a0d11c715f217f4b6a6d9ec4884c7eea27bddb3e`  
**Status:** candidate branch only; no merge, release or device deployment.

## Rebase and scope

The former Perception PR #2438 was based on `dfa3945b2bbfdb65d932db74e02f402435494e84`, 18 commits ahead / 72 behind the current release-development HEAD. This branch re-composes its ten code/test/workflow paths directly on `fb563d7`; it does not import the old handoff or overwrite Boss-owned board files.

## Implemented Perception path

- A3 projector parameters are bound to source IDs, source hashes, encoder/preprocessing identity and generation; forgetting or revoking a source invalidates the affected projector state and dependent predictions. This is a bounded ridge/SHADOW projector lifecycle, **not** gradient-trained JEPA/body-weight learning or neural-backbone unlearning.
- A5 UI frame ingress validates a one-shot provider receipt and a live UIObservationLease, validates frame dimensions/format/size, and passes the accepted frame into the existing vision/PerceptPacket path. The caller-owned mutable frame buffer is zeroized on completion/failure.
- The provider entrypoint `consume_projected_frame_from_provider()` is a permissioned consumer boundary. Its tests use caller-supplied frame bytes and a synthetic provider/lease; it does **not** implement Android MediaProjection capture, Android consent UI, a real screen provider or same-turn Runtime→C3 acceptance.
- RAW EYE student/projector margins remain uncalibrated diagnostics; no OCR/object identity truth or action confidence is granted.

## Exact source SHA-256 on the current code head

The following SHA-256 values were computed from the exact GitHub file readback at code head a0d11c715f217f4b6a6d9ec4884c7eea27bddb3e. The SHA-256 routine was checked against the standard "abc" known vector.

- v13/code/v13/vision.py: 0e08fdd20140f3e60f67305c930d3b1b5db273ebaa0e289925136c1378340877
- v13/code/v13/vision_source_lineage.py: bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f
- v13/code/v13/vision_validation.py: 2297f17c4bc60f49b19b5a4b5da1a175a2bc9a32fb18b0801a8274b067b44b8b
- v13/code/v13/vision_ui_frame_ingress.py: 80e4de2bca227bf893abbf994408ae730a1551070a60fcb225b15255a779fb97
- v13/code/v13/vision_temporal_evidence.py: ae2a470c2472306cf58a42baa30af6170f209451ffd19e863c5da426856ddde1

The current Core source-lifecycle builder at the release base still pins vision.py to 758cfc26387bd92da6c1c73d1d53224e76827ba70289c3c9e440f62557c209e5, while the current Perception branch's exact vision.py bytes hash to 0e08fdd20140f3e60f67305c930d3b1b5db273ebaa0e289925136c1378340877. That is the observed fail-closed mismatch behind the staged/integrated error. Core must update its own pin and any dependent guard/recovery/stage/deployer hashes; Perception does not edit those Core-owned files.

## Verification

- **Historical focused CI:** source-lineage/forget/compile 29/29 PASS on Python 3.13 and 3.14; frame-ingress/compile 30/30 PASS on Python 3.13 and 3.14 (previous PR head `049009c`).
- **Historical staged/integrated CI:** FAIL on that same previous head: the Core-owned source lifecycle builder rejected `vision.py` as an unsupported lifecycle source. Cascading result: 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests; migration was PARTIAL. This is not an integrated Runtime pass.
- **Current rebased head:** exact-head CI still needs to run; no pass is claimed yet.
- **LOCAL_LINUX full Aii suite:** BLOCKED / NOT_RUN because no checkout is mounted and GitHub DNS resolution failed for `git ls-remote`. No local compile or pytest result is claimed.
- **REDMI_UNVERIFIED:** no connected authorized phone, Android MediaProjection, Termux or native instrumentation was available. No screen capture or device mutation was performed.
- **Release:** NOT_RELEASED. No UPDATE_REQUEST, manual command, model/weight swap or permission change.


## Added temporal RAW EYE → A4 path

- Added vision_temporal_evidence.py: a pure-Python bounded process-local registry (maximum eight capture sessions) keyed by capture session, brain generation and consent receipt. It stores only the previous 4×4 tile luminance summaries (16 values per tile), never raw frame bytes or text.
- On each subsequent frame it computes per-tile mean absolute luminance deltas, a top-four/global pooled change score, changed-tile IDs and source/time metadata. First frame is WARMUP; out-of-order frames are rejected; a gap above 1500 ms resets the baseline. The 0.08 changed-tile threshold and pooled score are deterministic heuristics, not calibrated probabilities or learned perception.
- vision_ui_frame_ingress.py now attaches numeric deltas and the exact frame source reference to the A5 PerceptPacket and, when a nonzero measured change exists, calls the existing A4 modulate(..., sal={"novelty": change_score}) before A4 perception. It does not assign object identity, OCR truth, action confidence, learning authority or model-weight updates.
- reset_temporal_visual_evidence() erases a capture session's history; consume_projected_frame_scope(..., end_of_stream=True) invokes it on the final frame. The provider must call this reset helper on session revocation/end when it does not use the final-frame scope. Automatic provider-revocation wiring is still pending Core/QA integration.
- Exact current Git blob IDs (SHA-1, not Core guard SHA-256): vision_temporal_evidence.py 433230672f5dae663a8647dbe3c7f31a6ced27d2; vision_ui_frame_ingress.py 0d280f01e2b95123979f81cdccaae90c5e84a012; test_vision_ui_frame_ingress.py dad2a5f39482e02ca8cb4a0048dee7ac3cfc7882. Core must recompute its SHA-256 source pins on this exact branch head; the prior values below are historical and now stale for the modified frame-ingress source.

## New verification state

- LOCAL_LINUX isolated module harness: python3 -m pytest -q /tmp/v14-temporal-visual/test_temporal_visual_evidence.py → 12 PASS. This exercised the pure temporal registry copy (warm-up, stable frames, localized changes, stale ordering, gap reset, receipt/session isolation, bounds and malformed numeric inputs); it is not the full Aii repository suite or the integration test.
- Current exact-head CI on a0d11c7: source-lineage and public privacy workflows completed SUCCESS; RAW EYE frame-ingress and staged/integrated workflows were still IN_PROGRESS at handoff time. No exact-head frame-ingress PASS or integrated PASS is claimed until those runs finish.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN because no repository checkout is mounted and git ls-remote failed due github.com DNS resolution. The integrated frame test has not been executed locally.
- REDMI_UNVERIFIED: no authorized connected Redmi, real MediaProjection provider, Termux or Android native run. No device was contacted or mutated.
- NOT_RELEASED: no update request, manual command, model/weight swap or permission change.


## Required owners

1. **Core:** extend its source-lifecycle allowlist to the exact `vision.py`, `vision_source_lineage.py`, `vision_validation.py` and `vision_ui_frame_ingress.py` hashes on this head. Then refresh recovery/stage/deployer pins bottom-up. Preserve strict fail-closed verification; do not bypass the unsupported-source error.
2. **Core / QA:** recompose the one-shot provider with this consumer on one current-base head; update the vision.py source pin (expected 758cfc..., actual 0e08fdd...), ensure the new temporal module is included in the staged source set, and verify same-turn lease lifetime, end-of-stream/revocation reset, buffer zeroization, process death and no-replay behavior.
3. **QA:** run exact Python 3.13/3.14 focused, staged/integrated, migration, privacy and consent-revocation workflows.
4. **Perception:** after integration, connect the approved provider result to the actual Runtime A5→A4→C3 consumer and validate on authorized Android hardware. Until then the path is synthetic/provider-contract only.

**User action:** none required.

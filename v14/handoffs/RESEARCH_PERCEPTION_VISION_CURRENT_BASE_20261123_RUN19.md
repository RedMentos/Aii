# Research & Perception — A3 source lineage / RAW EYE current-base handoff

**Date:** 2026-11-23  
**Release-development base:** `gpt6/v13-private-remote-bridge-20261111` @ `fb563d771fe2d493c4ec25abe94280981d24ef5c`  
**Branch:** `research-perception/v14-vision-lifecycle-current-20261123-run19`  
**Code commit:** `f2fef9be34e2147e424a153114226c548cbda359`  
**Status:** candidate branch only; no merge, release or device deployment.

## Rebase and scope

The former Perception PR #2438 was based on `dfa3945b2bbfdb65d932db74e02f402435494e84`, 18 commits ahead / 72 behind the current release-development HEAD. This branch re-composes its ten code/test/workflow paths directly on `fb563d7`; it does not import the old handoff or overwrite Boss-owned board files.

## Implemented Perception path

- A3 projector parameters are bound to source IDs, source hashes, encoder/preprocessing identity and generation; forgetting or revoking a source invalidates the affected projector state and dependent predictions. This is a bounded ridge/SHADOW projector lifecycle, **not** gradient-trained JEPA/body-weight learning or neural-backbone unlearning.
- A5 UI frame ingress validates a one-shot provider receipt and a live UIObservationLease, validates frame dimensions/format/size, and passes the accepted frame into the existing vision/PerceptPacket path. The caller-owned mutable frame buffer is zeroized on completion/failure.
- The provider entrypoint `consume_projected_frame_from_provider()` is a permissioned consumer boundary. Its tests use caller-supplied frame bytes and a synthetic provider/lease; it does **not** implement Android MediaProjection capture, Android consent UI, a real screen provider or same-turn Runtime→C3 acceptance.
- RAW EYE student/projector margins remain uncalibrated diagnostics; no OCR/object identity truth or action confidence is granted.

## Exact source SHA-256 from prior focused CI

- `v13/code/v13/vision.py`: `0e08fdd20140f3e60f67305c930d3b1b5db273ebaa0e289925136c1378340877`
- `v13/code/v13/vision_source_lineage.py`: `bb63636c9ae84d345fe1f4e37254de3be87c26990cb320ca058859fd0b51b72f`
- `v13/code/v13/vision_validation.py`: `2297f17c4bc60f49b19b5a4b5da1a175a2bc9a32fb18b0801a8274b067b44b8b`
- `v13/code/v13/vision_ui_frame_ingress.py`: `4dfde9bc4cde8d555054c353c4636af3d5eb55e24330f2f19f73a6704ece6f0a`

These values were printed by the previous PR's Python 3.13/3.14 jobs. Recompute them on this exact rebased head before updating any Core allowlist.

## Verification

- **Historical focused CI:** source-lineage/forget/compile 29/29 PASS on Python 3.13 and 3.14; frame-ingress/compile 30/30 PASS on Python 3.13 and 3.14 (previous PR head `049009c`).
- **Historical staged/integrated CI:** FAIL on that same previous head: the Core-owned source lifecycle builder rejected `vision.py` as an unsupported lifecycle source. Cascading result: 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests; migration was PARTIAL. This is not an integrated Runtime pass.
- **Current rebased head:** exact-head CI still needs to run; no pass is claimed yet.
- **LOCAL_LINUX full Aii suite:** BLOCKED / NOT_RUN because no checkout is mounted and GitHub DNS resolution failed for `git ls-remote`. No local compile or pytest result is claimed.
- **REDMI_UNVERIFIED:** no connected authorized phone, Android MediaProjection, Termux or native instrumentation was available. No screen capture or device mutation was performed.
- **Release:** NOT_RELEASED. No UPDATE_REQUEST, manual command, model/weight swap or permission change.

## Required owners

1. **Core:** extend its source-lifecycle allowlist to the exact `vision.py`, `vision_source_lineage.py`, `vision_validation.py` and `vision_ui_frame_ingress.py` hashes on this head. Then refresh recovery/stage/deployer pins bottom-up. Preserve strict fail-closed verification; do not bypass the unsupported-source error.
2. **Core / QA:** recompose the one-shot provider with this consumer on one current-base head; verify same-turn lease lifetime, revocation, buffer zeroization, process death and no-replay behavior.
3. **QA:** run exact Python 3.13/3.14 focused, staged/integrated, migration, privacy and consent-revocation workflows.
4. **Perception:** after integration, connect the approved provider result to the actual Runtime A5→A4→C3 consumer and validate on authorized Android hardware. Until then the path is synthetic/provider-contract only.

**User action:** none required.

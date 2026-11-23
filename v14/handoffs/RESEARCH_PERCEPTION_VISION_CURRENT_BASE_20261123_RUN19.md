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


## Follow-up implementation — polarity-aware temporal surface and revoke cleanup (2026-11-23)

- Research note R-112: full-text inspection of arXiv:2607.05205v2 (submitted 2026-07-06; v2 2026-09-09), Sections II–III. It describes polarity-separated ON/OFF event time-surfaces with tau=30 ms and a 50 ms temporal window feeding a lightweight fly-optic-lobe motion network and bottom-up attention. Its evaluation uses DAVIS346 event-camera vehicle sequences (four velocities in each day/night condition) on an Apple M4 / 16 GB host; it is not an Android/ARM or phone-screen benchmark. The work is a preprint; peer-review status and primary license were not independently confirmed. No official code repository was found. A secondary index reports CC BY-NC-ND 4.0, so no paper code/text/figures are reused. The V14 adaptation is only a coarse frame-difference ON/OFF diagnostic, not an event-camera implementation.
- vision_temporal_evidence.py now keeps bounded per-tile brightening/darkening surfaces with exponential decay (30 ms tau; 50 ms expiry window), alongside the original absolute frame-difference score. A4 uses max(raw change, decayed activity) as a short-lived novelty signal; no OCR/object/action/learning authority is added.
- vision_ui_frame_ingress.py now exports temporal_visual_revocation_callback(runtime, capture_session_id=...). The Android provider can pass it as revoke_callback to ui_observation_lease. It clears the matching temporal registry before the existing source/cache revocation. The provider must still wire this callback; no Android provider is added here.
- New exact repository tests cover ON/OFF polarity, 30 ms decay, 50 ms expiry, long-gap reset and provider post-lock revocation cleanup. These tests are queued for exact-head CI; local full Aii checkout is unavailable.
- Local isolated prototype test: python3 /tmp/v14_temporal_surface_probe.py -> 3 PASS; python3 -m py_compile /tmp/v14_temporal_surface_probe.py -> PASS. This is a standalone algorithm/lifecycle copy, not the exact repository module or full suite.
- Device: REDMI_UNVERIFIED; the installed runtime remains STOPPED_BY_USER per authenticated DIAGNOSTICS #815. No CHAT_SEND, restart, UPDATE_REQUEST, microphone/screen capture, model/weight change, permission change or user-data mutation.
- Next: Core/QA pass temporal_visual_revocation_callback(runtime, capture_session_id=...) into the actual provider's lease factory, then rerun exact Python 3.13/3.14 staged/integrated/migration/consent tests. Do not request a phone run while the user-controlled runtime is STOPPED.


## Run-20 implementation checkpoint — global/local temporal novelty (2026-11-23)

**Current branch:** research-perception/v14-vision-lifecycle-current-20261123-run19.  
**Parent code head:** b1d19846a400f321b7c737753a88601e879e445d.  
**New commits:** 28494563fb4208413f27e5e9891eee014d174848 (new pure-Python decomposition module), 91b85d9977dcb34eeb89da2a16bbae339e1b6aaa (temporal evidence state), 9bf949a2b63b3e331ed5784e34531aa762204ecc (A4 consumer), 4c3cc26a22000a332a9eb8073ee115303ee6b989 (synthetic regression tests), ff888b11b6023394bc4320ee505a9a8b50a21c75 (numeric assertion correction), 9ebadb055c6e2f6c1b587ff046a3baa9627fc3c6 (workflow compile/path coverage), bd4d8990b6678d653c83f9d43ca1b555a0771112 (R-113 research ledger).

### New executable behavior

- New vision_temporal_adaptation.py decomposes the 256 bounded 4×4-tile luminance samples into a median signed common-mode shift and per-tile residuals. It uses only the Python standard library.
- vision_temporal_evidence.py preserves the prior raw delta and ON/OFF surfaces, while adding a separate local residual surface, global shift score, local change score, local temporal activity and a bounded attention-novelty calculation.
- vision_ui_frame_ingress.py now passes the local-first novelty scalar into the existing A4 modulation consumer and includes global/local diagnostics in the source-bound A4 evidence object. Global-only change retains a 0.15 contribution; this is a BOOT heuristic, not a calibrated threshold.
- Two repository regressions cover global-only brightening versus a same-amplitude one-tile change, and a mixed global+local case. Existing ON/OFF, decay, receipt, session, revoke and PerceptPacket tests remain in the same targeted workflow.
- No image bytes, OCR, text, persistent screenshot data, model weights, permissions or Android provider code were added or changed.

### Tests and environment

- LOCAL_LINUX: isolated helper source compiled with py_compile and 6/6 pytest tests passed in /tmp/v14-perception-check. These tests exercise the exact helper implementation but are not the full repository suite or A5/A4 integration.
- Exact repository Python 3.13/3.14 workflow: queued after the latest push; no PASS is claimed until exact-head workflow readback.
- Full Aii LOCAL_LINUX checkout/suite: NOT_RUN / BLOCKED; no checkout is mounted and prior git ls-remote failed because github.com DNS could not resolve.
- Staged/integrated status from the parent head remains FAIL due the Core-owned source_lifecycle_lock_integration_candidate.py pin: expected vision.py SHA-256 758cfc26387bd92da6c1c73d1d53224e76827ba70289c3c9e440f62557c209e5; Perception branch vision.py SHA-256 0e08fdd20140f3e60f67305c930d3b1b5db273ebaa0e289925136c1378340877. Perception has not edited Core-owned pins.
- REDMI_UNVERIFIED; no connected authorized phone or real MediaProjection provider. No Android capture, microphone, CHAT_SEND, UPDATE_REQUEST, restart or device mutation.
- NOT_RELEASED; GitHub commits are not deployment.

### Research

- R-113 appended to the research ledger. Full Crowder et al. (2008) PMC article read; Ebelin et al. (2024) publication abstract and official MIT reference-repository README/LICENSE reviewed, but ACM full text was inaccessible (403). No external code or dataset imported.
- Main limitation: median common-mode separation assumes fewer than half of the 256 samples contain local change. Scrolling, camera motion and full-screen transitions remain confounded. The 0.15 global weight needs source/session-disjoint real-screen ablations; do not tune it from synthetic fixtures.

### Coordination / next

- Core still owns the fail-closed source-lifecycle hash rebind and dependent recovery/stage/deployer pins. The current #2442 staged/integrated failure remains a blocker, not a Perception success.
- QA should run the exact frame-ingress workflow on this new head and then the full staged/migration/privacy/revocation matrix after Core's pin composition is repaired.
- Perception next: run source/session-disjoint global-vs-local-vs-flicker/scroll/app-transition ablations, then connect the signed provider callback and prove same-turn A5→A4→C3 only after Core/QA integration.
- Boss owns the shared board and V14_USER_NEXT_ACTION.md; this handoff records the facts for that update. User action: none.


## Exact-head CI readback — 18384cd (2026-11-23 15:43 UTC)

- Frame-ingress workflow run 45207964978: Python 3.13 **39 passed** (1.13 s) and Python 3.14 **39 passed** (1.09 s). This includes the new global/local attention controls and existing A5/A4/PerceptPacket/provider-contract regressions.
- Public privacy scan run 45207965607: **CLEAN** for base fb563d771..HEAD.
- Source-lineage/forget run 45207965817: Python 3.13 **29 passed** (3.09 s) and Python 3.14 **29 passed** (2.12 s).
- Staged-runtime run 45207966638: **FAIL**, 19 failed / 234 passed / 10 skipped / 2 errors / 41 subtests. The repeated exception is unsupported lifecycle source: vision.py from source_lifecycle_lock_integration_candidate.py:172. The two migration checks consequently report PARTIAL rather than UPDATED.
- Integrated-regression run 45207966638: **FAIL**, one staged-composition test; same exact unsupported lifecycle source: vision.py root cause. No separate semantic failure was exposed.
- No Perception-owned guard/pin was weakened. The exact code-level source hash mismatch and Core ownership remain as stated above. This is focused CI success plus an integrated blocker, not merge/release acceptance.


## Local helper cost probe — 2026-11-23

On the available LOCAL_LINUX container (x86_64, Python 3.13.5), the exact helper byte sequence (Git blob 694d3b0bacc940ed6fa514415132d838800882ac) was run on 16 tiles × 16 luminance samples:

- 10,000 complete decompose → pool → novelty calls: **0.0806 ms/call** mean wall-clock on this host.
- One-call tracemalloc: **15,008 bytes peak**, 5,936 bytes current at sample time.
- This is a small-host CPU/memory probe only. It does not include Pillow/frame decode, the temporal registry, A4, native model inference or Android scheduling. Do not project the number to ARM/Redmi.


## Latest sanitized private device receipt — V13OBS #115 (2026-11-23 15:44 UTC)

- Private owner-read updated 15:44:16 UTC; pipeline reports auto-update enabled, UP_TO_DATE, last_error NONE, installed/update commit fb563d771fe2d493c4ec25abe94280981d24ef5c. This is the installed base, not this Perception PR.
- App service/dashboard are reported running, but the user-controlled AI runtime state is STOPPED_BY_USER, model process STOPPED, autostart false, and native residency UNAVAILABLE. No restart or remote command was sent.
- Across the five reported turns, C3 emitted 7 tokens in the quickest observed turn (1.87 s prefill-to-first-token); later turns emitted only 2–3 tokens with 33–37 s prefill-to-first-token. B1_DETAIL and B2_GIST each had two native attempts, two failures and zero valid offers. The receipt does not prove semantic use of B1/B2 offers or native latent exchange.
- These are sanitized aggregate diagnostics only; no console excerpt, user text, device path/ID, model file, weight, database or raw log was copied.
- Updater UP_TO_DATE does not establish useful chat behavior or install the current PR. REDMI runtime remains STOPPED_BY_USER; Perception branch NOT_DEPLOYED. Do not send UPDATE_REQUEST or ask for a manual command while the device is stopped and no new release exists.

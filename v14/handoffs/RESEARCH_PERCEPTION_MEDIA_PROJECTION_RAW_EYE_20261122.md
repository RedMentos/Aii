# Research & Perception handoff — MediaProjection RAW EYE frame ingress

Date: 2026-11-22  
Base: `gpt6/v13-private-remote-bridge-20261111` at `aed1d2b826290c95c70356b5d8b864b5ef382be4`  
Branch: `research-perception/v14-media-projection-raw-eye-20261122-run7`  
PR: [#2375](https://github.com/RedMentos/Aii/pull/2375)  
Code commits: `9f8e8038bf5cd55ff8a35a8cb2f063a216df1adb` (A3 student receiver) and `b6aaa826a9f57ad777bb7cafb5713705ffcf6968` (duplicate archive-member rejection); test commit: `ed22ab8ec078687c3865c5d603ae73fcfca676f7`. Current PR head is shown in #2375.

## Product gap and implementation

The existing `a5_ui_admission_bridge.py` has a source/session/receipt-bound `UIObservationLease` and a metadata-only `A5UIRuntimeAdapter.context` consumer. It does not turn an authorized MediaProjection frame into visual percepts. The new `v13/code/v13/vision_ui_frame_ingress.py` adds that missing Perception-side adapter:

1. Requires the exact active `UIObservationLease`, a `MEDIA_PROJECTION / SCREEN_FRAME_AVAILABLE` observation, and a provider-owned `frame_binding_check` callback that accepts the exact SHA-256 and byte length against the current signed frame receipt/session.
2. Accepts one mutable caller-owned PNG/JPEG buffer, caps it at 8 MiB / 4 MP, decodes with the existing `vision.decode`, and overwrites the caller buffer immediately after decode (best effort only).
3. Reuses the existing RAW EYE `vision.background / boxes / tile_features / saliency / region_ref` functions to emit one global plus 16 grid-region feature summaries. These remain handcrafted color/edge/layout heuristics, not semantic object recognition.
4. Creates a source-bound ephemeral `PerceptPacket`, calls A4 attention with `file_requests=False`, runs the existing Percept admission and A5 context envelope, and publishes the final packet into the existing lease-gated `A5UIRuntimeAdapter.context` cache.
5. Provisional frames are never admitted to C3 context. The current user source is never truncated. Raw screenshot bytes and derived packet are not written to Store; no OCR, teacher, student projector, learning authority, action authority or truth authority is added.

The caller must hold the same UI lease through every downstream read and C3 generation. The adapter itself does not open MediaProjection or call C3/normal Runtime dispatch.

## Research / platform source

- Android Developers, [Media projection guide](https://developer.android.com/media/grow/media-projection), accessed 2026-11-22. The guide requires user consent for every session and one use of the MediaProjection token for the virtual display. For Android 14+ targets it requires the mediaProjection foreground-service type/permission. It also requires registering `MediaProjection.Callback.onStop()` and releasing the virtual display/surface when the session ends. The provider must also handle captured-content resize and system/user stop.
- Android Developers, [MediaProjectionManager API reference](https://developer.android.com/reference/android/media/projection/MediaProjectionManager), accessed 2026-11-22. The API documents the consent activity and foreground-service requirements.
- No new OSS implementation or model was copied, downloaded or selected. This adapter reuses existing V14/V13 repository modules and the already-present Pillow/NumPy test dependencies. No model-weight license question is introduced.

## Evidence

- LOCAL_LINUX: CPython 3.13.5 x86_64. `py_compile` passed for the new module and test file.
- LOCAL_LINUX isolated harness: 8/8 PASS. The harness executes the new module against small local stubs for the existing UI lease, vision and packet contracts; it is not the full Aii repository or exact dependency implementation.
- Exact repository push CI: [45065181398](https://github.com/RedMentos/Aii/actions/runs/45065181398) PASS on Python 3.13 and 3.14; both exact-repository test jobs passed. Private-bridge regression [45065181405](https://github.com/RedMentos/Aii/actions/runs/45065181405) PASS. PR-specific rerun [45065185183](https://github.com/RedMentos/Aii/actions/runs/45065185183), staged/integrated regression [45065185185](https://github.com/RedMentos/Aii/actions/runs/45065185185), and privacy scan [45065185198](https://github.com/RedMentos/Aii/actions/runs/45065185198) were QUEUED at the last read.
- Full local Aii checkout / full repository suite: NOT_RUN (repository checkout is not mounted in this worker).
- TERMUX / Android / Redmi: NOT_RUN / REDMI_UNVERIFIED. No MediaProjection provider, APK install, OS consent, device capture, normal Runtime dispatch or C3 turn was exercised.

## Risks and hard limits

- `frame_binding_check` is a required provider-owned callback. `PROVIDER_CALLBACK_ACCEPTED` means only that this callback returned literal `True`; the adapter does not itself verify an OS signature. The companion provider must verify a signed receipt bound to the exact frame digest, session, source and elapsed-realtime interval.
- Overwriting the caller's mutable buffer is best effort. Python/Pillow internal copies are not guaranteed to be securely erased.
- The packet is cached in memory under the UI lease. Provider revocation clears it; simply exiting the lease marks it inactive but does not itself remove the cache entry. Core must call `A5UIRuntimeAdapter.revoke(source_id)` after provider revocation and `A5UIRuntimeAdapter.close()` after provider revocation plus Runtime worker exit, before Store shutdown. The lease must remain held through downstream consumption.
- This is RAW EYE feature extraction, not OCR, object detection, a trained visual projector, or semantic vision. The current A5 UI bridge does not yet call this module from the normal Runtime; Core must wire that call.
- No Android permission, provider, model, weight, learning switch, installed data or device state was changed.

## Next executable integration

1. Core/QA implement the MediaProjection provider on the companion side: per-session consent, one-use token, foreground service, signed frame receipt, resize/stop callback, and an explicit stop path.
2. Core calls `consume_projected_frame` inside the active `UIObservationLease`, then passes its final `A5UIRuntimeAdapter.context` packet / bounded envelope to the actual Runtime consumer while retaining the lease through C3. After provider revocation and worker exit, call `revoke(source_id)` / `close()` to clear ephemeral cache before Store shutdown.
3. QA runs exact staged/integrated and revocation/restart negatives, then an explicitly authorized Android API/lifecycle test. Redmi remains unverified until a real device receipt and measured user-visible result exist.

User action: none. No Termux command or model download is required for this candidate.


## Latest private Redmi acceptance boundary

The latest private V13OBS aggregate snapshot was updated 2026-11-22 20:08:59Z. It reports installed commit `aed1d2b826290c95c70356b5d8b864b5ef382be4`, auto-update enabled, runtime/dashboard `UP_TO_DATE`, and last error `NONE`. That is installation status, not functional acceptance. The last observed turn took 57.74 s with 41.63 s TTFT, 751 prompt tokens and 2 generated tokens; B1/B2 ended `TIME_BUDGET` at 53.2/54.2 s. Native process mapping showed zero mapped processes with child readability unknown; native latent exchange and C3 semantic use were not proven. PR #2375 is not a release and has not been sent to the device. No update request or CHAT_SEND was issued.

## Model research candidate (R-084)

Full-text review of MobileCLIP2 (TMLR August 2025 Featured) and SmolVLM (arXiv preprint 2025-04-07) is recorded in `v14/V14_RESEARCH_LEDGER.md` as R-084. MobileCLIP2-S0 is a compact image/text dual encoder, but official weights are under Apple ML Research Model TOU (code MIT; data CC-BY-NC-ND), and its 1.5 ms image / 3.3 ms text figures are iPhone 12 Pro Max results. SmolVLM2-256M Video Instruct declares Apache-2.0 weights; its card reports 1.38 GB GPU RAM for video inference, while the SmolVLM paper reports 0.8 GB VRAM for single-image inference. Neither result is an Android/Termux benchmark. SmolVLM2 is a candidate for a later serial/on-demand semantic vision experiment, not a replacement or approved download. No weights were downloaded and no model was swapped.

## Run 7 addendum — A3 student receiver connected to the UI frame path

Date: 2026-11-22  
Current branch: research-perception/v14-media-projection-raw-eye-20261122-run7  
Code commits: 9f8e8038bf5cd55ff8a35a8cb2f063a216df1adb, b6aaa826a9f57ad777bb7cafb5713705ffcf6968  
Test commit: ed22ab8ec078687c3865c5d603ae73fcfca676f7  
PR: [#2375](https://github.com/RedMentos/Aii/pull/2375)

The frame adapter now optionally consumes the already-trained local V13 tile student when its Store record is explicitly LAB_SHADOW_ONLY. It verifies a constrained relative path using descriptor-relative O_NOFOLLOW traversal, exact SHA, bounded NPZ size/member set, finite 37→embedding projector tensors, and exact encoder revision. It does not download, train, promote or rewrite the projector. A matching hashed_bow encoder is deterministic; an already-installed EmbeddingEncoder is bounded by a two-second deadline. For the 16 grid tiles it computes a normalized goal-vs-background embedding margin and labels it STUDENT_ESTIMATE. The margin is added to the source-bound segment summaries so it reaches the existing A5 context envelope/C3 packet; it does not change priority, action authority, learning authority or truth authority. Missing or invalid student state leaves the handcrafted RAW EYE path available.

**Local isolated evidence:** CPython harness PASS for secure openat/no-follow load, exact SHA round-trip (maximum projection difference 0), hash-tamper rejection and symlink rejection. A shifted synthetic UI image held out from the training image produced a higher red-panel margin than blue/background tiles. This is synthetic and does not establish real visual semantics, calibration, or device performance.

**Exact repository CI:** the new code/test head ed22ab8ec078687c3865c5d603ae73fcfca676f7 triggered the focused Python 3.13/3.14 compile + pytest workflow, staged/integrated regression and privacy scan. They were QUEUED at the last poll; no exact-head CI PASS is claimed yet. The subsequent code hardening commit b6aaa826a9f57ad777bb7cafb5713705ffcf6968 triggers another exact-head run. Full local Aii suite remains NOT_RUN because the checkout is not mounted.

**Device receipt:** fresh private owner-read PIPELINE_STATUS #617 and DIAGNOSTICS #618 confirm release-development SHA aed1d2b826290c95c70356b5d8b864b5ef382be4 installed, auto-update enabled, runtime/dashboard UP_TO_DATE, last_error NONE. The repeated last turn is 57.739 s / 41.627 s TTFT / 38.945 s prefill / 751 prompt tokens / 2 generated tokens; B1/B2 remain TIME_BUDGET at 53.2/54.2 s; instantaneous mapped native process count is zero with child readability unknown. This is not a new user turn, correctness pass, sustained residency measurement or proof that this PR is installed. No update request or CHAT_SEND was issued.

**Open boundary:** no companion MediaProjection provider, normal Runtime dispatch, Android permission/capture, Termux test or Redmi visual test exists. The student is a closed-form local ridge projector, not JEPA gradient learning or native body-weight adaptation. It is only useful after a prior local :image tiles training run with matching encoder metadata. Its uncalibrated margin must not be treated as confidence or used to trigger actions.

**Research:** R-085 records the full-paper review of StepX-Edge (arXiv:2607.22708, 2026-07-20 preprint). Its UI-aware tiling and progressive connector are relevant design hypotheses, but the 0.9B system was measured on Snapdragon 8 Gen5, uses Qualcomm QAIRT/Genie and has no official code/weight license verified in this run. No model selection or download is proposed.

**Next executable action:** wait for the exact b6aaa826 CI matrix; repair any focused or integrated failure. Then coordinate with Core/QA to wire the provider and normal Runtime consumer without changing their owned files. Run a source-disjoint real UI holdout and no-student baseline only after the provider is available and the user has explicitly granted the corresponding screen-capture session. Redmi remains REDMI_UNVERIFIED.

## Cross-lane mobile MoE research — R-087

The full 28-page MobileMoE paper (arXiv:2605.27358v1, 2026-05-26) and official S-QAT model card/license were reviewed. MobileMoE-S/M/L report 0.68/1.48/2.75 GB INT4 weight memory and 1.49/2.77/4.71 GB peak RSS at 8k on Galaxy S25; 1k S25 TTFT is 2.01/4.32/8.99 s. Their real-prompt RSS is 1.2–2.1× dummy-prompt RSS because expert activation depends on input. The fast path uses a custom fused ExecuTorch MoE operator, while the HF model card requires trust_remote_code=True and warns that the generic Transformers INT4 path materializes BF16 weights on first forward. The model is FAIR Noncommercial Research License v1, requires contact-data sharing to access, and does not establish Redmi/Snapdragon 732G viability. No weights were downloaded. R-087 is RESEARCH_ONLY / NO_MODEL_SWAP; the useful design ideas are moderate sparsity, fine-grained experts, shared expert and real-prompt routing/RSS profiling for distinct B1/B2 bodies.

## QA review addendum — provider capability and FIFO hardening (2026-11-22)

QA review found two issues before provider integration. First, the old frame_binding_check parameter accepted any callable, including lambda returning True. That parameter is removed. consume_projected_frame now requires an exact ProviderFrameVerifier object issued by the internal companion-provider factory. The verifier is one-shot and bound to the exact active UIObservationLease object and generation plus source_id, capture_session_id, consent_receipt_ref, capture method and event kind. It rejects a raw callable, a different lease/session, reuse, false results and exceptions. The trusted Android companion must issue it only after cryptographically verifying the companion-signed frame receipt and exact digest/length. This is a typed injection contract, not a hard security boundary; the Android OS permission and trusted companion process remain mandatory and are not implemented here.

Second, the final projector file open now uses O_NONBLOCK together with O_NOFOLLOW, so a malicious FIFO is opened nonblocking and rejected by fstat rather than hanging before the regular-file check. The focused test file now has 15 tests, including raw-callable and constructor negatives, one-shot/lease/session binding, hash mismatch, symlink and FIFO negatives, and the synthetic A3 receiver.

LOCAL_LINUX isolated harness PASS: exact active-lease capability accepted once, replay/wrong-session/wrong-lease/raw-constructor rejected; FIFO open/fstat returned immediately. Exact repository code/test head 98cedec1d5ddbb6a365803fbf19bb66cffb73d1a has focused MediaProjection workflow 45068436503, privacy scan 45068436491 and staged/integrated regression 45068436684 QUEUED; safe-additive candidate tests are SKIPPED because this is not a release event. No exact repository PASS is claimed. Current PR documentation head is c4d1f7fb94ab8e16c2e9d624b3267a03a8ea2025.

The remaining blocker is the absent Android companion provider: it must enforce the OS grant, verify the signed receipt, issue the capability, own resize/stop/revocation lifecycle, and call the adapter under the same lease. No real signed receipt, Runtime/C3 dispatch, Termux capture or Redmi test has occurred. Keep PR #2375 DRAFT / NOT_RELEASED.



## Run 7 follow-up — exact frame snapshot and fail-closed config (2026-11-22)

**Verified code head:** `6a4e919f176a7d1b96ab6669639c6fd1be4a7de4` on the same Perception branch; PR #2375 remains DRAFT / NOT_RELEASED.

A source review found that `consume_projected_frame` called `_bounded_vision_config` and `_overwrite_caller_buffer` but neither helper existed in the module. This would raise `NameError` on the first actual frame. Both helpers are now implemented: the config is copied from the existing vision defaults, the caller may select only a bounded hash dimension, and the adapter forcibly fixes the 8 MiB / 4 MP / 4×4 tile limits. Mutable compressed buffers are best-effort zeroized.

The same review identified a time-of-check/time-of-use gap: a caller-owned `bytearray` could be modified by another thread after the provider verifier accepted its digest but before Pillow decoded it. The adapter now copies one bounded snapshot, hashes and decodes that exact snapshot, then zeroizes both the snapshot and the caller buffer on success and failure. The provider receipt and emitted `frame_sha256` therefore refer to the pixels actually decoded.

**New regression coverage:** config overrides cannot expand the fixed capture limits; boolean/invalid hash dimensions are rejected; a verifier callback that mutates the caller buffer after digest acceptance cannot change the decoded image; both mutable buffers are zeroized.

**LOCAL_LINUX:** CPython 3.13.5 x86_64 isolated helper reproduction PASS for snapshot/hash/decode ordering and zeroization of both buffers. This is not the full repository module/test suite. Full Aii checkout remains unavailable in the worker; full local pytest/compile is BLOCKED.

**Exact GitHub CI:** head `6a4e919f176a7d1b96ab6669639c6fd1be4a7de4` has three exact-head checks queued: MediaProjection frame-ingress Python 3.13, Python 3.14, and offline-bridge security. No PASS is claimed yet. Earlier run `45068534234` was for the older `e1eec838` head and does not certify this update.

**E2E boundary:** no Android companion MediaProjection provider, OS consent, normal Runtime/C3 dispatch, Termux capture, or Redmi test exists. The new adapter code is still only a Perception-side consumer candidate; `REDMI_UNVERIFIED`. No model, weight, permission, installed data or device state was changed. Next step: wait for exact-head CI, fix any failure, then coordinate Core/QA provider and Runtime wiring.


## Run 7 follow-up — scoped source/cache cleanup for the real downstream consumer (2026-11-22)

**Latest code/test head:** `f87ebac407a19c147da7eb52bc63f10e9eed25d2`; PR #2375 remains DRAFT / NOT_RELEASED.

Added `consume_projected_frame_scope(...)`, a context manager for the actual caller contract: nest it inside the same active `UIObservationLease`, keep the outer lease open while the downstream C3 consumer reads the packet, and let the scope revoke this frame's source/cache after C3 returns. Its `finally` cleanup also runs if the downstream consumer raises. It revokes only the per-frame source/cache; it does not revoke the Android MediaProjection OS session or close a shared Runtime adapter. This gives Core a safer integration seam than relying on a later manual cache-cleanup call.

Added regression coverage for source revocation after successful consumption and after a simulated downstream exception. The focused test file now contains 18 tests. The prior exact-frame snapshot/TOCTOU and fixed capture-limit tests remain.

**LOCAL_LINUX:** CPython 3.13.5 x86_64 isolated helper reproduction PASS for fixed config bounds, invalid hash-dimension rejection, snapshot/hash/decode consistency, Pillow decode, zeroization, and scoped cleanup on success/failure. This is not the full Aii repository test suite.

**Exact GitHub checks:** head `f87ebac407a19c147da7eb52bc63f10e9eed25d2` currently has 8 queued checks (Python 3.13/3.14 focused, staged, integrated, privacy and offline-bridge security) and 1 policy skip (additive validator). No exact-head CI PASS is claimed.

**E2E boundary unchanged:** no Android MediaProjection provider, signed receipt implementation, OS consent, normal Runtime/C3 dispatch, Termux capture, or Redmi visual test exists. Status remains WIRED_SYNTHETIC / REDMI_UNVERIFIED. No model, weight, permission, device data or release changed.


## Exact-head CI poll — 2026-11-22

For code/test head `f87ebac407a19c147da7eb52bc63f10e9eed25d2`, the latest readback is now: `privacy` SUCCESS; `offline-bridge-security` SUCCESS; six checks QUEUED (Python 3.13/3.14 focused, staged runtime, integrated regression and duplicate matrix jobs); `validate-additive` SKIPPED by policy. This is partial CI progress, not an all-green exact-head matrix. The branch head `bc9e420d316d3b0106cf8cf5567388f503d90755` is still the handoff-only successor to the code/test head; no code changed after `f87ebac`.


**Documentation readback:** the Perception branch now points to `d228e7171712c54a97be9fb04bab8264654ec4a0`; this commit changes only this handoff. The code/test head remains `f87ebac407a19c147da7eb52bc63f10e9eed25d2`; the partial CI results above are for that exact code/test head.

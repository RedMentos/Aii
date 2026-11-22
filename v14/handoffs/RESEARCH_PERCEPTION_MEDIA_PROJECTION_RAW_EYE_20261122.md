# Research & Perception handoff — MediaProjection RAW EYE frame ingress

Date: 2026-11-22  
Base: `gpt6/v13-private-remote-bridge-20261111` at `aed1d2b826290c95c70356b5d8b864b5ef382be4`  
Branch: `research-perception/v14-media-projection-raw-eye-20261122-run7`  
PR: [#2375](https://github.com/RedMentos/Aii/pull/2375)  
Current code head: `f1aae4cf55cbf8b1f42b93f9e404c77285d2d0bc`.

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
- The packet is cached in memory under the UI lease and is cleared by the existing UI revocation path. The lease must remain held until downstream consumption finishes.
- This is RAW EYE feature extraction, not OCR, object detection, a trained visual projector, or semantic vision. The current A5 UI bridge does not yet call this module from the normal Runtime; Core must wire that call.
- No Android permission, provider, model, weight, learning switch, installed data or device state was changed.

## Next executable integration

1. Core/QA implement the MediaProjection provider on the companion side: per-session consent, one-use token, foreground service, signed frame receipt, resize/stop callback, and an explicit stop path.
2. Core calls `consume_projected_frame` inside the active `UIObservationLease`, then passes its final `A5UIRuntimeAdapter.context` packet / bounded envelope to the actual Runtime consumer while retaining the lease through C3.
3. QA runs exact staged/integrated and revocation/restart negatives, then an explicitly authorized Android API/lifecycle test. Redmi remains unverified until a real device receipt and measured user-visible result exist.

User action: none. No Termux command or model download is required for this candidate.


## Latest private Redmi acceptance boundary

The latest private V13OBS aggregate snapshot was updated 2026-11-22 20:08:59Z. It reports installed commit `aed1d2b826290c95c70356b5d8b864b5ef382be4`, auto-update enabled, runtime/dashboard `UP_TO_DATE`, and last error `NONE`. That is installation status, not functional acceptance. The last observed turn took 57.74 s with 41.63 s TTFT, 751 prompt tokens and 2 generated tokens; B1/B2 ended `TIME_BUDGET` at 53.2/54.2 s. Native process mapping showed zero mapped processes with child readability unknown; native latent exchange and C3 semantic use were not proven. PR #2375 is not a release and has not been sent to the device. No update request or CHAT_SEND was issued.

## Model research candidate (R-084)

Full-text review of MobileCLIP2 (TMLR August 2025 Featured) and SmolVLM (arXiv preprint 2025-04-07) is recorded in `v14/V14_RESEARCH_LEDGER.md` as R-084. MobileCLIP2-S0 is a compact image/text dual encoder, but official weights are under Apple ML Research Model TOU (code MIT; data CC-BY-NC-ND), and its 1.5 ms image / 3.3 ms text figures are iPhone 12 Pro Max results. SmolVLM2-256M Video Instruct declares Apache-2.0 weights; its card reports 1.38 GB GPU RAM for video inference, while the SmolVLM paper reports 0.8 GB VRAM for single-image inference. Neither result is an Android/Termux benchmark. SmolVLM2 is a candidate for a later serial/on-demand semantic vision experiment, not a replacement or approved download. No weights were downloaded and no model was swapped.

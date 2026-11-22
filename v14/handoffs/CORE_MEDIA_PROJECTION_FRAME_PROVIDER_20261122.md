# Core handoff — one-shot Android MediaProjection frame provider

Date: 2026-11-22  
Owner: Core & Harness  
Package: V14-009 / Android screen-observation provider  
PR: #2379 (draft; stacked on QA PR #2356)  
Branch: core/v14-media-projection-frame-provider-20261122  
Code checkpoint SHA: 19f53e9baa16446d5fc167ce3715765579a1298a\nHandoff commit: b1bdfef7e0d88e330f3f0cc829563d30bd429bba

## Verified scope in this branch

- The native companion exposes a user-visible Capture one screen frame action.
- Every capture begins with Android's MediaProjection consent UI; the app requests the default display only.
- A foreground service captures one frame, releases the projection, and does not run a continuous recorder.
- The JPEG is bounded to 4 MP / 8 MiB and held only in process memory for at most 20 seconds.
- A paired-caller-checked ContentProvider pipe returns the frame once. The companion stop switch, service/process teardown, system revocation, expiry and explicit Discard clear the pending frame.
- The signed P-256 receipt binds the frame hash/length/dimensions, source/session IDs, capture method/scope, API level, monotonic interval and expiry. Action authority, learning authority and raw-frame persistence are explicitly false.
- Termux transport permits only the fixed companion URI and a bounded binary read. Python verifies the pinned key, signature, schema, expiry, replay, byte count and exact SHA-256 before returning a mutable buffer.
- A Runtime-turn lease bridge is authored, with polling for companion-side discard/stop and fail-closed behavior when the A5/RAW EYE consumer is absent. It is not yet usable on this branch because the newer A5 lease adapter and RAW EYE frame-ingress files are in Perception PR #2375.

## Tests and evidence

- Robolectric tests: one-use read, receipt retention only for lease metadata, expiry, wrong-token rejection, clear/zeroization, authority rejection, exact receipt binding.
- Python tests: P-256 signature verification, replay/expiry/tamper/authority negative cases, exact frame hash/length, disabled-companion rejection, URI restriction and bounded binary transport.
- CI: pending/queued at this checkpoint; do not call it PASS until the exact SHA reports success.
- LOCAL_LINUX: repository checkout was not available in this session; no local test is claimed.
- TERMUX/REDMI: no connected authorized device session was used. MediaProjection dialog, actual frame bytes, background lifecycle and device memory remain REDMI_UNVERIFIED.
- Deployment: NOT_RELEASED. No UPDATE_REQUEST, permission change, model/weight change or device mutation was sent.

## Integration dependencies and next executable action

1. QA reviews and integrates companion base PR #2356 first.
2. Perception reviews/integrates PR #2375 and confirms its exact A5UIRuntimeAdapter.lease / ProviderFrameVerifier contract.
3. Rebase this branch onto the combined accepted base; resolve the currently fail-closed lazy imports.
4. In Runtime._turn, for an explicit screen-observation request, call AndroidCompanionFrameProvider.open_current_turn(runtime), consume the frame through vision_ui_frame_ingress.consume_projected_frame, fetch the same-lease A5UIRuntimeAdapter context, pass source-bound context to C3, and hold the lease until C3 finishes.
5. Add a true Runtime integration test that proves C3 consumed the source-bound A5 packet, and a negative test that companion Discard/stop cancels the turn and erases cached UI context.
6. Only after exact CI, Boss integration and explicit on-device consent should QA test this on Redmi. Do not send an update request until that release path is approved.

## Risks / explicit non-claims

- This does not yet provide end-to-end visual reasoning or prove C3 consumed screen context.
- The frame is a full-display snapshot, not an Accessibility tree; app-window capture is not enabled.
- The local frame grant is bounded by the companion's 20-second receipt store and a Runtime lease poller; it is not a persistent OS permission.
- Synthetic/Robolectric/CI evidence is not Android-device proof.

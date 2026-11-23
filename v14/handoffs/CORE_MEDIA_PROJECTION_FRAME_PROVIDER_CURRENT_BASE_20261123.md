# Core & Harness — MediaProjection provider on current capability stack

Date: 2026-11-23
Role: Core & Harness
Branch: `core/v14-media-projection-provider-perception-api-20261123`
Parent implementation branch: `core/v14-media-projection-provider-current-base-20261123`
Stack base branch: `core/v14-capability-registry-mediaprojection-20261123`
Stack base SHA: `429f62ad4e0d1c8561f148a862267a1749f96d38`
Parent provider commit: `7e7f82310eb5e58d2fbc249c28f897eea7a5da27`
Status: DRAFT / exact-head CI pending / NOT_RELEASED

## Connected functionality

- The Android companion advertises `screen_capture` as `READY_WITH_PER_SESSION_OS_CONSENT` only while paired and enabled. The user explicitly starts capture in the companion UI and approves Android's OS dialog for each session.
- The foreground service captures one frame only. Frame bytes are memory-only, capped at 8 MiB with a 20-second elapsed-time TTL, and exposed through a paired-caller-only one-shot ContentProvider pipe.
- Stop/disable, pair rotation, process restart, expiry and explicit discard revoke the frame and active read leases.
- Termux uses the fixed companion provider URI, validates the signed P-256 receipt, nonce/token, frame length and SHA-256, and zeroizes the mutable buffer.
- The Core consumer now calls Perception's public `consume_projected_frame_from_provider(..., verify_fn=...)` entrypoint instead of importing its private verifier factory. This keeps verifier issuance and caller-buffer cleanup inside the Perception receiver's owned API. The outer Core grant also zeroizes on every exit.

## Cross-owner integration

- Perception PR #2375 is at exact head `e21a85a329ea25a2208fcfa64edc216884b55bf1`; its RAW EYE workflow passed on Python 3.13 and 3.14, plus its staged regression and privacy scan. The public provider entrypoint is now the Core/Perception contract.
- Perception-owned source, tests and research files are not edited or copied into this branch.
- QA-owned process-restart and permission tests remain separate. Parent capability-registry PR #2406 is still required to pass its exact-head emulator workflow before integration.

## Evidence and limits

- Previous provider-stack commit `ea074fcf6f19247d5d8019019216dc68f4b38ad2` passed the provider workflow: Android Gradle assemble/unit tests and Python 3.13/3.14 compile + tests; staged context/integrated regression also passed. This follow-up changes the public Perception call contract and adds a consumer-exception zeroization test, so its own exact-head CI must pass.
- Local tests are BLOCKED in this runner: there is no repository checkout and `git ls-remote https://github.com/RedMentos/Aii.git` failed because github.com DNS did not resolve. No local compile/test is claimed.
- Physical Redmi/Termux capture, OS consent, frame delivery and same-turn C3 consumption remain REDMI_UNVERIFIED.
- A signed frame receipt proves only the companion's capture metadata and frame bytes; it does not grant action or learning authority. No model, weight, permission or installed app is changed by this PR.

## Next executable step

Verify exact-head CI on this branch, then coordinate the single integration of Core provider + Perception RAW EYE + the existing C3 turn consumer with Boss. Only after a consented Redmi receipt and actual C3 consumer evidence may the Android frame path advance beyond WIRED_SYNTHETIC/CI.


## Core & Harness run17 — one-shot capture race and Binder revocation boundary — 2026-11-23

- **Exact branch head:** `243eed9bd4aa001c5175c4e60ea84834fba2af6f` on `core/v14-media-projection-provider-perception-api-20261123`; 12 commits ahead / 0 behind stack base `429f62ad4e0d1c8561f148a862267a1749f96d38`. It remains a stale stack relative to release-development `aed1d2b826290c95c70356b5d8b864b5ef382be4` (diverged; 233 ahead / 788 behind). Do not merge or deploy this branch directly; Boss/QA must compose it with the current release and companion acceptance stack.
- **Concrete P1 fixes:** added a monotonic per-service `CaptureSessionGate` (NEW → STARTING → ACTIVE → FRAME_CLAIMED → COMPLETE). Duplicate `ACTION_CAPTURE` is ignored without stopping an active capture; a completed/discarded service instance cannot start another capture. Final frame publication now holds the same `CompanionProvider.ACTION_GATE_LOCK` used by stop/disable and provider reads, re-checks the current enabled state and installed Termux signer, then publishes and completes the session. Failure/stop clears the frame under that same lock. This closes the earlier check-at-entry / publish-after-stop race and the duplicate-intent overwrite race.
- **Binder boundary corrected:** `ParcelFileDescriptor.dup()` models the descriptor copy delivered across Binder. Stop can close the provider's descriptor, stop further writes and zeroize the in-process source array; it cannot recall bytes already buffered or delivered to a duplicated remote descriptor. The updated test asserts this honest boundary and drains only the bounded residual stream. The downstream `UIObservationLease` must remain valid through the entire C3 use; no stronger remote erasure claim is made.
- **LOCAL_LINUX:** dependency-free Java 21 `javac` compile + `CaptureSessionGateSmoke` PASS, 3 deterministic scenarios (one-shot/terminal state, stop wins before publish, stop clears if publish wins first). The exact same smoke runner is now in CI.
- **Exact-head CI on 243eed9:** run 45107573848: Python 3.13 PASS, Python 3.14 PASS, standalone capture-session-gate PASS; Android Gradle/Robolectric still IN_PROGRESS at last poll. Staged-runtime and integrated-regression run 45107573907 still IN_PROGRESS. Previous exact head f8ceb94 had Python/staged tests PASS, but Android Gradle failed because Maven Central returned HTTP 429 for Robolectric's `android-all-instrumented` artifact; that is an infrastructure fetch failure, not a passing Android test. Do not transfer the previous head's status to 243eed9.
- **LOCAL_LINUX full repository:** BLOCKED / NOT_RUN — no Aii checkout is mounted and `git ls-remote` cannot resolve github.com. No local Android SDK/Gradle build.
- **E2E user effect:** the companion's one-shot frame provider is safer against stop/duplicate-capture races, and Termux's source-bound public Perception API contract remains wired in this candidate. Normal Runtime same-turn A5/A4 → B1/B2 → C4/JEF → C3 consumption is not yet accepted. No trained latent transfer, native body learning or production B3.
- **Device / release:** installed release remains `aed1d2b826290c95c70356b5d8b864b5ef382be4` per Boss run16 private PIPELINE_STATUS #664; auto-update was enabled and Runtime/Dashboard UP_TO_DATE for that installed SHA. This PR is NOT_RELEASED / NOT_INSTALLED. No UPDATE_REQUEST, OS consent prompt, model/weight/permission change, shell or device mutation. Redmi capture and C3 use remain REDMI_UNVERIFIED.
- **Parent / cross-owner blockers:** PR #2406's emulator process-restart check previously stopped at an Android System UI ANR; QA owns that test/harness failure. Perception owns the RAW EYE/A3 implementation and QA owns process-death/permission acceptance. This Core stack is not a substitute for their review.
- **Next executable step:** finish exact-head Android + staged/integrated CI; if Robolectric is rate-limited again, rerun after the artifact endpoint recovers and retain the failure as BLOCKED/INFRA rather than claiming PASS. Then coordinate a clean current-release rebase/composition with Boss/QA, keep the capture OFF until process-restart/consent acceptance, and wire the normal same-turn Runtime consumer through C3.
- **User action:** keine Aktion nötig. No model swap, permission change, update request or manual Termux command is justified.


## Core & Harness run18 — checked publication failure + read-only frame status — 2026-11-23

- **Exact branch head:** `e7d50cfaa36eb3ab13bbd33b9857724af8283c6a`; PR #2408 remains DRAFT, stacked on #2406 at `429f62ad4e0d1c8561f148a862267a1749f96d38`. The branch is not a release ancestor and must be composed by Boss/QA rather than deployed directly.
- **Concrete compile fix:** exact-head CI on prior head `e472540386094b83c66fb7d8e3bff0b606ad4eae` failed Android Gradle compilation because `ProjectionFrameStore.publish(...)` throws checked `Exception` and `CompanionProvider.publishScreenFrameIfAuthorized(...)` did not declare it. Both overloads now explicitly propagate the checked failure to the existing capture-service failure/cleanup path. Added `malformedReceiptPropagatesCheckedFailureWithoutPublishingFrame` to verify a malformed receipt cannot publish a frame and the session remains safely finalizable.
- **User-facing read-only status:** added `:android frame-status`. It requires the already pinned companion key, verifies the signed current frame metadata and fixed ContentProvider URI, and returns only bounded metadata. It does not read screenshot bytes, consume the one-use nonce, persist raw capture, or grant action/learning authority. Added positive and unpinned-key negative tests; the positive test also asserts zero frame reads and zero used-nonce rows.
- **Readback:** `android_companion_runtime.py` blob `932d8e24e645cc71e003d8a1529c393997db4353`; `test_android_companion_runtime.py` blob `0da080f4105b92fb999c974d750ec13054ee5e96`; handoff updated on this branch.
- **LOCAL_LINUX:** JDK 21 `javac --release 17` compile + dependency-free CaptureSessionGate smoke: **PASS, 3 deterministic scenarios** (one-shot terminal state, stop wins before publish, stop clears a frame if publish wins first). This is only the isolated Java gate smoke, not Android Gradle or device validation. Full Aii Python/package tests remain **BLOCKED / NOT_RUN** because no checkout is mounted and GitHub DNS resolution fails.
- **Exact-head CI:** provider run `45110548664` and staged/integrated run `45110548708` are **QUEUED** at the time of this handoff; no current-head CI pass is claimed. The previous Android Gradle compile failure is fixed in source but must be verified by this exact-head run.
- **E2E user effect:** the user can now inspect whether a signed one-shot screen frame is available without consuming it. The frame provider remains a capture/transport path only; it is not yet consumed by the normal Runtime same-turn A5/A4 → B1/B2 → C4/JEF → C3 path. No native latent coupling, trained weight update or production B3 is claimed.
- **Android / release:** installed Redmi release remains `aed1d2b826290c95c70356b5d8b864b5ef382be4` in the latest available private evidence; no new private receipt was obtained in this run. Capture, OS consent, frame delivery and same-turn C3 consumption remain **REDMI_UNVERIFIED**. PR #2408 is **NOT_RELEASED / NOT_INSTALLED**. No UPDATE_REQUEST, model/weight/permission change, shell action or device mutation was made.
- **Open risks:** parent #2406's emulator process-restart check previously hit a System UI / com.android.phone ANR; QA owns the emulator retry. The branch still depends on QA's current capability/process-restart acceptance and Perception's public RAW EYE consumer. `:android frame-status` is diagnostic only and must not be mistaken for the missing Runtime/C3 integration.
- **Next executable step:** poll both exact-head workflows; fix any observed failure and rerun. Then coordinate a current-release composition with Boss/QA and implement the same-turn Runtime consumer only on a reviewed compatible stack. Keep screen capture OFF until the actual companion consent and process-restart path is accepted.
- **User action:** keine Aktion nötig.

# Core & Harness — MediaProjection provider on current capability stack

Date: 2026-11-23
Role: Core & Harness
Branch: `core/v14-media-projection-provider-current-base-20261123`
Base branch: `core/v14-capability-registry-mediaprojection-20261123`
Base SHA: `429f62ad4e0d1c8561f148a862267a1749f96d38`
Status at checkpoint creation: DRAFT / CI NOT YET VERIFIED / NOT RELEASED

## Product change

This branch carries the Core-owned one-shot Android MediaProjection provider onto the current capability-registry stack. It does not copy or edit Perception- or QA-owned files.

- The Android companion advertises `screen_capture` as `READY_WITH_PER_SESSION_OS_CONSENT` only while paired and enabled. The manifest declares the MediaProjection foreground-service contract.
- The user starts capture from the companion UI and must accept Android's OS consent dialog for each session. The service captures one frame only; no continuous recording and no screenshot file/SQLite persistence.
- Frame bytes stay in memory, capped at 8 MiB with a 20-second elapsed-time TTL. The provider exposes one paired-caller-only, one-use read pipe. Stop, disable, pair rotation, process restart, expiry and explicit discard revoke the frame and active pipe leases.
- Termux transport is restricted to the fixed companion ContentProvider URI, verifies the signed frame receipt, nonce/token freshness, byte count and SHA-256, and zeroizes the mutable frame buffer after use.
- `AndroidUIFrameGrant.consume()` holds the revocable A5 UI lease while delegating RAW EYE processing to `vision_ui_frame_ingress`. If that Perception consumer is absent, it fails closed. Perception PR #2375 remains a required integration dependency; this branch does not claim a complete RAW EYE→C3 turn.

## Provenance and evidence

- Reused Core provider implementation from PR #2379 at source head `77fd5d63696940f255bb849b58da89c32150b370`; only Core-owned files are included.
- Parent capability contract is PR #2406 at `429f62ad4e0d1c8561f148a862267a1749f96d38` (stacked base; its exact-head CI is checked separately).
- PR #2379's provider workflow passed at its old head; its separate Perception ingress workflow failed on an older `_summary` NameError. The newer Perception PR #2375 contains the corresponding fix, but remains a separate owner PR.
- Local checkout/test attempt is BLOCKED: this runner has no repository checkout and `git ls-remote https://github.com/RedMentos/Aii.git` failed with DNS resolution error for github.com. No local compile/test is claimed.
- New branch CI must run Python 3.13 and 3.14 compile/tests plus Android Gradle assemble/unit tests. Results will be appended after exact-head readback.
- Physical Redmi / Termux capture, OS consent, native frame delivery and user-visible C3 consumption remain REDMI_UNVERIFIED.

## Safety and open integration

No model authority, action authority, learning authority, network access or shell authority is granted by a captured frame. The frame is ephemeral input only. Full RAW EYE/A5/C3 use requires the separate Perception receiver and a later same-turn Runtime integration review. No installed app, permission, model, weight or device data was changed.

## Next executable step

Read back this branch's exact commit, run the new CI workflows, fix any regression on this branch, then coordinate a single integration with Perception PR #2375 and QA's current companion process-restart checks. Do not mark the feature Android-verified or released without a real consented Redmi receipt.

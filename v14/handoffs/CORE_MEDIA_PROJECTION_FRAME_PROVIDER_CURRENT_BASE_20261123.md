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

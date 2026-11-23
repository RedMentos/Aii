# Core & Harness handoff — Android capability registry validation

Date: 2026-11-23
Role: Core & Harness
Branch: core/v14-android-capability-registry-current-qa-20261123
Base branch: qa/v14-companion-final-qa-20261122
Base SHA: 43975b78659a02ce1ba9520ac5dfae10b2556d37
Code checkpoint: ef9ab161ac452c6af39a1d340077c7ea936e46a0
PR: #2394 — https://github.com/RedMentos/Aii/pull/2394
Current branch head before documentation refresh: 7b4bd0e80d889e612884d1f64dae2dcbcb5de754
Status: DRAFT / CI PENDING / NOT_RELEASED / REDMI_UNVERIFIED

## Implemented

- Added v13/code/v13/android_capabilities.py with a strict typed parser for the companion's v14.android-capability-registry/1 snapshot.
- The parser requires the exact top-level and entry schemas, the complete unique eight-capability inventory, bounded text fields and strict boolean types.
- It permits READY_WITH_PER_ACTION_CONSENT only for launch_app, and only when Termux is paired and the companion stop switch is enabled. The launch provider must be PACKAGE_MANAGER_LAUNCH_INTENT, per-action consent must be true, OS permission requirement false, result_observed false and learning_authority false.
- audio_capture, observe_ui, screen_capture, tap, swipe, type_text and back must remain OFF_NOT_IMPLEMENTED with provider NONE. The audio capture entry must continue to declare that an Android OS permission would be required.
- network_enabled, shell_enabled and model_authority must remain false. Missing, unknown, duplicate, malformed, mismatched or authority-escalated registry data fails closed.
- AndroidCompanionController.capabilities now returns a validated snapshot or an explicit fail-closed invalid-registry result. AndroidCompanionController.launch validates the full registry before creating ActionIntent or submitting to the companion.
- Existing ActionIntent/ActionOutcome behavior remains unchanged. Companion receipts remain COMPANION_RECEIPT_ONLY, observed=false, t8_authoritative=false and world_learning_eligible=false. This does not create an Android UI executor, background provider, trusted T8 transition or new OS authority.

## Verification

- LOCAL_LINUX isolated parser contract and negative-control reproduction: PASS on CPython 3.13.5. Covered valid launch inventory, disabled/unpaired stop states, malformed schema, missing/duplicate entries, invalid API type, per-action-consent removal, observation/learning escalation and network/shell/model authority escalation.
- Full Aii local pytest/py_compile: BLOCKED / NOT_RUN. No local Aii checkout is mounted; git ls-remote failed because github.com DNS could not resolve.
- Exact branch CI: PENDING until the successor PR is opened. The workflow is updated to compile android_capabilities.py and run the existing companion runtime suite on Python 3.13 and 3.14.
- Parent QA #2356 at 43975b78659a02ce1ba9520ac5dfae10b2556d37: core companion Gradle/Robolectric and Python consumer workflows PASS; separate android-companion-process-restart UI job FAILS because the emulator displayed “System UI isn't responding”. This is an emulator lifecycle acceptance blocker, not proof of an app/device defect or pass.
- TERMUX/REDMI and APK install: NOT_RUN / REDMI_UNVERIFIED. No device pairing, capability activation, OS permission change, model/weight change, UPDATE_REQUEST, shell or device mutation occurred.

## Coordination

- This branch is a current-QA-base successor to stale Core PR #2376. #2376's merge base is 27aaa29dd13adc49ea1c0b305ccfb878ad203eb0; current QA head is 43975b78659a02ce1ba9520ac5dfae10b2556d37, so the old branch is 6 commits behind and its earlier CI is not relied upon.
- QA-owned Java CapabilityRegistry.java, CompanionProvider.java and emulator lifecycle scripts were not modified.
- V14_USER_NEXT_ACTION.md and V14_WORK_BOARD.json were refreshed from the latest QA Run 10 documentation branch and updated with this Core checkpoint. The master, live workplan, team operating system and research ledger were not rewritten.
- No user decision is required.

## Next exact actions

1. PR #2394 is open against qa/v14-companion-final-qa-20261122. Read back its current head and run the Python 3.13/3.14 companion workflow plus the staged/integrated consumer matrix.
2. Fix any real regression without weakening the strict schema or OFF gates.
3. Obtain independent Boss/QA review. Do not merge to the release branch while the parent process-restart UI acceptance is red.
4. Only after the parent lifecycle gate and integration are accepted should QA consider a separate bounded APK/emulator/Redmi action test. Keep every capability except explicitly consented launch_app OFF until its own provider and OS permission flow are implemented and verified.

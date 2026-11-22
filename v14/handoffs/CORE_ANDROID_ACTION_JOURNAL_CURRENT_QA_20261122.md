# Core handoff — Android ActionIntent / ActionOutcome journal on current QA base

Date: 2026-11-22
Role: Core & Harness
Branch: `core/v14-android-action-journal-current-qa-20261122`
Base: QA companion PR #2356 exact head `27aaa29dd13adc49ea1c0b305ccfb878ad203eb0`
Previous stale Core PR: #2373 (older base `615418973a7adf4d31495414965105efbecafc97`).

## Connected product behavior

- C5 `:android launch <package> --confirm` creates the typed source-bound ActionIntent before broker approval and companion submission.
- If ActionIntent persistence fails, the local proposal is cancelled and no companion dispatch is submitted.
- `:android history [1..50]` reads only the current session and joins intents/outcomes by exact action ID, event, brain generation and source provenance. It does not return package text or private arguments.
- Signed companion receipts remain `COMPANION_RECEIPT_ONLY`: observed=false, T8=false, World-learning=false.
- If a process stops after receipt claim but before Store persistence, restart recovery retries only the read-only outcome receipt query and never re-dispatches the app launch.
- If Store persistence succeeded but broker finalization failed, recovery validates the exact stored intent/outcome, event/source/session, action ID, digest, receipt schema, signature scheme and non-authoritative flags, then finalizes locally without a remote retry.
- Tampered stored digest, duplicate/mismatched intent/outcome, cross-session rows or authority escalation fail closed.

## Exact verification

- Code head before this handoff: `a41dc838ba3ef6f8787d35907f671df8d62577af`; current-base comparison: 7 commits ahead, 0 behind QA head `27aaa29dd13adc49ea1c0b305ccfb878ad203eb0`.
- Core companion outcome adapter workflow `45078455239`: SUCCESS; Python 3.13 = 58 passed, Python 3.14 = 58 passed.
- V13 staged/integrated workflow `45078455175`: SUCCESS; integrated regression = 415 passed, 3 skipped, 58 subtests; staged Runtime = 240 passed, 10 skipped, 47 subtests, plus staged context and arithmetic/broker groups.
- Parent QA #2356 exact head `27aaa29dd13adc49ea1c0b305ccfb878ad203eb0`: staged/integrated `45077740421` SUCCESS; Android outcome `45077740494` SUCCESS; Core outcome `45077740377` SUCCESS; Android companion `45077740470` FAILURE in process-restart emulator/UIAutomator acceptance after System UI became unresponsive. This is not an app/device pass.
- LOCAL_LINUX: CPython 3.13.5 exists, but no Aii checkout is mounted and `git ls-remote` fails with DNS `Could not resolve host: github.com`; full local repo tests NOT_RUN / BLOCKED.
- TERMUX/REDMI: REDMI_UNVERIFIED. No APK install, pairing, app launch, permission change, model/weight change, UPDATE_REQUEST or device mutation occurred.

## Scope boundary

This is a real Python Runtime/SQLite → signed companion receipt → source-bound ActionOutcome persistence/history candidate, not proof that the Android emulator process-death gate passed or that a physical Redmi performed an action. Companion receipt does not prove foreground observation or T8 learning. No shell, Accessibility, MediaProjection, microphone or arbitrary UI authority is added.

## Next action

Open/review this current-base Core PR against QA #2356. Do not merge into the release branch while the parent Android process-restart workflow is red. QA must resolve the emulator/System-UI failure and retain the prior failure evidence; then Boss can integrate the current-base Core journal and perform a separate approved bounded device acceptance.
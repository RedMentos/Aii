# Core & Harness — Android ActionOutcome process-death integration

**Date:** 2026-11-24  
**Branch:** `core/v14-android-action-journal-instrumented-restart-20261124-run1`  
**Base:** Core PR #2450 head `523c04eb1e96d0e01e1cdda0c9832632360de044`  
**QA source:** PR #2427 head `ae56dd1e54b3b78161f226d7735ed919879ea6cf`  
**State:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.

## Reproduced blocker

The exact #2450 emulator job installed the APK successfully, then the host UIAutomator driver failed to find the STOPPED label. At failure, `pidof` still returned PID 1968 and MainActivity remained top-resumed, while hierarchy dump timed out. The log showed WindowManager/SystemUI contention but no app crash. This is a failed emulator test, not proof that the companion state machine itself crashed.

## Integrated fix candidate

Ported the exact QA-owned Espresso/ActivityScenario process-death harness from #2427 onto the Core ActionIntent/ActionOutcome stack. The QA and Core `MainActivity.java` blob hashes match, so the harness targets the same UI contract without changing app behavior.

- Uses the real MainActivity view tree and actual Enable/Stop button listener.
- Verifies persisted OFF after Stop, externally force-stops the app, then starts a fresh ActivityScenario and verifies provider startup remains OFF.
- Uses allowlisted app-private PID/start-time markers to prove a new process; host `pidof` treats only the exact empty exit-1 shape as absence and fails closed on adb transport errors.
- Adds AndroidX instrumentation dependencies and runs both AndroidTest APKs in the emulator workflow.
- Replaces the failing UIAutomator restart acceptance command with the QA Espresso process-death driver; retains old UIAutomator helpers as diagnostics, not as passing evidence.
- Re-runs Core Python ActionIntent/ActionOutcome tests on the combined branch.

No capability, app permission, remote execution, or user-data behavior was broadened.

## Evidence

- Parent Core #2450 exact head: 11/12 checks SUCCESS, the sole failure was `android-companion-process-restart`.
- QA #2427 source head: 5/5 checks SUCCESS on its own branch, including its Android emulator workflow. The source branch is separate; this port requires its own exact combined run.
- LOCAL_LINUX full Aii checkout: BLOCKED / NOT_RUN (no checkout mounted; GitHub DNS resolution failed).
- Local Android SDK/emulator: NOT_AVAILABLE. No local Android build or device test claimed.
- Exact combined branch CI: not yet read back at this handoff.
- Redmi: REDMI_UNVERIFIED. No private relay, CHAT_SEND, UPDATE_REQUEST, shell, restart or device action was performed.

## Next

1. Run the exact Android emulator process-death job and the Core ActionOutcome Python matrix on this combined branch.
2. Fix any combined-stack failure without weakening visible Stop, persisted OFF, process-death or no-redispatch assertions.
3. After exact CI passes, request independent QA review and rebase onto the newest compatible companion base; do not merge the old #2450 branch directly into release.
4. Only an authorized installed APK plus a fresh owner-verified device receipt can promote Android device status.

**User action required: NONE.** No manual Termux command or permission change is needed for this repository-side candidate.

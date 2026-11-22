# QA & Android — companion process-death acceptance

Date: 2026-11-22  
Lane: QA & Android / V14-017, V14-019  
PR: #2356 (OPEN, not GitHub draft / NOT_RELEASED)  
Base: `core/v14-android-companion-native-20261121`

## Defect and acceptance gap

The companion's existing Robolectric tests exercise the process-start reset method and the stop gate, but they do not kill and recreate an actual Android application process. The stop durability review also requires proving that the user-visible OFF state is persisted, not merely held in a static in-process boolean.

## Candidate implementation

- Added `android-companion/scripts/test_process_restart.py`, executed from the GitHub host so the test harness survives termination of the app under test.
- The script launches the debug APK, checks the visible STOPPED state and persisted preference, enables/stops/re-enables through the real UI, and checks each synchronous SharedPreferences value.
- It then runs `am force-stop`, waits until `pidof com.redmentos.v14.companion` is empty, relaunches MainActivity, and verifies both the visible state and persisted preference are OFF.
- Added a separate API-35 Google APIs emulator job to `.github/workflows/v14-android-companion.yml`. The CI-only `ReactiveCircus/android-emulator-runner` action is pinned to immutable commit `a421e43855164a8197daf9d8d40fe71c6996bb0d` (tag v2; Apache-2.0), verified from the upstream tag and LICENSE.
- The probe does not pair Termux, submit a launch request, invoke an external app, request OS permissions, or enable any unimplemented capability.

## Verification

- LOCAL_LINUX / Python 3.13.5: test-script syntax compilation PASS.
- LOCAL_FULL_REPOSITORY: BLOCKED — this environment has no Aii checkout, Gradle, Android SDK or adb.
- Prior exact PR head `6643acba196e2b7191c7e637edfcf62f61139b18`: Android Gradle/Robolectric, Python 3.13/3.14 outcome tests and staged/integrated checks were green.
- Code-bearing head `bb7b2921d5c9174f28dacf5a569f577fafd4e7bf`; subsequent commits on this PR branch only add/update this handoff. The Android companion and emulator jobs are queued on the code-bearing head; no result is claimed yet.
- Even a green emulator test is not a Redmi Note 10 Pro installation/reboot result.

## Device boundary

- Private PIPELINE_STATUS #591: installed runtime/dashboard revision `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`, auto-update enabled, no last error.
- Later HEALTH #593: runtime `UNAVAILABLE`, 836 MiB available RAM, 1535 MiB free disk.
- Later LEARNING_STATUS #594: learning `UNAVAILABLE` (receipt status OK); no active learning-loop proof.
- Earlier DIAGNOSTICS #592 showed a native process census and a previous turn (57.74 s total, 41.63 s TTFT, 38.95 s prefill, 2 generated tokens). This is not a new chat acceptance and does not supersede the later HEALTH availability result.
- No CHAT_SEND, UPDATE_REQUEST, stop/restart, APK installation, permission change or model/data mutation was performed.
- Redmi companion lifecycle, Android app control and current chat RPC usability remain `REDMI_UNVERIFIED` / unresolved.

## Next action

Wait for the exact-head emulator/Gradle CI. If green, request independent Core review and integrate only through the shared companion stack. Do not claim physical Redmi verification or start the 20-turn chat benchmark while HEALTH reports runtime unavailable and available RAM is below 1 GiB.

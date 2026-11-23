# QA & Android — Run 10 checkpoint (2026-11-23)

**Execution:** started 2026-11-23 00:15:43 Europe/Berlin; completion timestamp not recorded.  
**Release branch readback:** `gpt6/v13-private-remote-bridge-20261111` = `aed1d2b826290c95c70356b5d8b864b5ef382be4`.  
**Device evidence:** private V13OBS #115, updated 2026-11-22 23:19:27 UTC. This is a read-only status receipt, not a new turn or device action.

## Installed Redmi status — exact evidence boundary

- Existing updater: enabled; runtime and dashboard `UP_TO_DATE`; `last_error=NONE`; reported installed commit exactly matches release branch head `aed1d2b`.
- Runtime/service/dashboard: `RUNNING`; managed sessions: 8; last session exit: `UNVERIFIED`.
- Latest stored turn: `FINAL`, 57.739 s total, 41.627 s TTFT, 38.945 s C3 prefill, 751 prompt tokens, 2 generated tokens. Correctness and semantic use remain UNKNOWN; no transcript was read or copied.
- B1/B2: B1 4/4 native attempts failed, B2 2/2 failed; zero valid offers and zero offers included in final C3 reports. Latest B1/B2 failures are `TIME_BUDGET` at 53.2/54.2 s. Native latent exchange is not proven.
- Instant native-process map: 0 mapped processes, readability UNKNOWN. This is not evidence of free RAM or model residency.
- Official Age 0; lab request 10 / effective implemented stage 5; physical feature execution false; learning commit authority still requires separate SHADOW mode.
- No model, weight, permission, setting, chat, SQLite or user-data mutation was performed. No UPDATE_REQUEST or manual Termux command was sent.

## QA code and exact-head evidence

1. **Android companion lifecycle QA — PR #2356**, branch `qa/v14-companion-final-qa-20261122`, head `231d88846835a2c5d6b59c591a5d696ed64a1f21`.
   - Previous emulator failure was an explicit Android System UI ANR after emulator graphics errors (`ColorBuffer` / texture bind); the test safely selected only the visible `Wait` action and refused `Close app`. It did not establish a companion-app crash.
   - Updated head uses emulator `-gpu software`, allows at most two visible safe `Wait` taps, still never selects `Close app`, and fails closed if the overlay persists or no visible Wait exists.
   - Exact-head checks at last read: 5/8 SUCCESS; `android-companion` build/test and `android-companion-process-restart` were still IN_PROGRESS; integrated-regression and Python 3.14 companion-outcome were QUEUED. No APK installation on Redmi.

2. **Fair-budget QA assertion correction — PR #2389**, head `9f414dfdf071d0d898ece06960e45c6216bd7680`, stacked on Boss PR #2370.
   - Boss exact head `ebe1bec4...` had two staged/consumer failures because tests hard-coded the source profile's 26.0 s C3 reserve while the staged candidate intentionally uses a 45% pre-answer window (16.5 s on the 30 s fixture) and adds `MIN_ROLE_SLICE_S`.
   - Tests now recognize only the two explicit source/staged profiles and fail closed on an unknown profile. No production runtime or builder pin was changed.
   - Exact-head CI: staged-runtime PASS (261 passed, 10 skipped, 48 subtests); integrated-regression PASS (424 passed, 3 skipped, 58 subtests); offline-bridge-security PASS. 3/3 SUCCESS. Awaiting Boss review/integration; not released.

3. **Perception frame ingress — PR #2386**, head `4390cfe7ef2a7a4723d8d54ad35be4d67e2c3155`, stacked on QA PR #2384.
   - Exact-head CI 5/5 SUCCESS (frame-ingress Python 3.13/3.14, staged-runtime, integrated-regression, offline security).
   - It fixes the context-manager decorator placement and retains caller-buffer zeroization on verifier failure. Parent #2384 remains red until this child is integrated and its own exact-head matrix reruns.
   - Synthetic Python adapter only; no MediaProjection capture, APK install or Redmi proof.

4. **Temporal JEPA — PR #2372**, current head `bc0d18c9d8f451b7bc0ababf7dde782cc25caf11`.
   - Adds a Store-backed NumPy temporal encoder/predictor + EMA target, optimizer/checkpoint persistence, source/session-disjoint windows, retention/utility gates, rollback/retry, and a numeric B1/B2 readout consumer.
   - Tests assert actual numeric encoder/predictor/EMA deltas and optimizer persistence in synthetic Store/T8 data. This is real small-model weight movement in the synthetic environment, not native GGUF body-weight learning or learned cross-organ latent transfer.
   - Exact-head matrix: 3 SUCCESS, 8 QUEUED at last read. QA source-lifecycle PR #2383 remains stale/red; do not rebase it until #2372's parent matrix is green, then recompute the full downstream builder chain bottom-up.

5. **Boss fair-budget candidate — PR #2370**, head `ebe1bec4df6033e619cf145eb9899572dcb5849b`.
   - 25 SUCCESS, 3 FAIL at last read: staged-runtime and consumer Python 3.13/3.14 all hit the reserve-profile assertion now addressed by #2389; staged audio/arithmetic was still in progress.
   - #2389 is a test-only stacked correction; Boss must integrate it and rerun the final exact-head matrix.

## Acceptance and next executable work

- **No release candidate is accepted by this QA run.** The installed release remains `aed1d2b`; PRs #2356/#2389/#2386/#2372/#2370 are not deployed.
- Complete #2356's emulator process-restart and companion build jobs; inspect their exact logs. If the emulator still ANRs after two safe waits, keep the lifecycle test BLOCKED rather than relaxing it.
- After #2372 exact parent CI is green, rebase QA #2383 onto that exact parent and recompute every lifecycle/feedback/context/training/Termux/stage/deployer pin bottom-up; rerun Python 3.13/3.14, optimizer, staged/integrated, Lab-Age and migration.
- Boss/Integrator owns shared Work Board and release merge. QA has not merged another agent's PR and has not sent device commands.
- Whole-Canon gaps remain: correct low-latency chat; successful B1+B2 offers consumed through C4/C3; trained B3 latent coupling; native body-weight learning/retention/rollback; full voice; permissioned Android observation/control; process-death/reboot/runtime-only rollback; and clause-level code/consumer/test/environment coverage.

**User action:** none. Do not rerun Termux, request an update, download models, or change permissions/weights. Any future Redmi lifecycle/learning acceptance requires a separate explicit bounded-device-test authorization after a stable exact-CI candidate.

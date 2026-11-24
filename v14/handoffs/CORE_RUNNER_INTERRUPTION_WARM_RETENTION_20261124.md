# Core — native runner interruption and warm retention

**Date:** 2026-11-24  
**Branch:** `core/v14-native-prefill-receipt-20261124-run1`  
**Checkpoint SHA:** `92c29725a687c2fa7995f92f828790115ee7e520`  
**PR:** #2464 (draft; not release-integrated)

## Hypothesis and change

The current `LlamaRunner.generate()` unloaded the native server on every non-FINAL turn. Both generation watchdogs also killed the process immediately when the turn deadline elapsed. This discarded the model and its warm KV context even when closing the HTTP request had already returned the server to idle.

The new path is deliberately fail-closed:

1. A deadline watchdog closes the in-flight HTTP connection first; it does not leave the watcher running.
2. Only the outer `generate()` lifecycle may attempt warm retention, and only for `DEADLINE` (never user cancellation or native error).
3. It checks the authenticated, loopback-only llama-server `GET /slots` response for a non-empty list in which every `is_processing` field is exactly boolean false.
4. It also requires the same live child process and unchanged loaded lifecycle stamp before and after the probe.
5. Missing, malformed, busy, timed-out, or unauthenticated slot status causes immediate process unload. The response body is never logged or persisted because it may contain prompt text.

The probe is bounded to 350 ms. A timeout that leaves the server busy therefore still unloads rather than risking a runaway request.

## Evidence and tests

- Added `test_runner_interruption_retention.py`: idle-retain positive case; busy, unavailable, malformed, and changed-lifecycle negative controls; user-cancel and native-error immediate-unload controls; verifies prompt text from the slots response is not copied to metrics.
- Added workflow `v14-core-runner-interruption-retention.yml` for Python 3.13 and 3.14.
- Updated the native receiver source pin, recovery builder blob pin, integrated stager hash, and RuntimeDeploy stager hash; exact GitHub file readbacks match.
- Exact-head workflows for SHA `92c29725` are queued/in progress, including the new warm-retention workflow. No PASS claim until completed.
- LOCAL_LINUX project test: **BLOCKED / NOT_RUN**. The execution container has Python 3.13.5, but no Aii checkout; `git clone` failed with DNS resolution for github.com. CI is the only current project-test path.
- Redmi: **REDMI_UNVERIFIED**. No connected authorized handset was available to this run.

## Research basis

The upstream llama.cpp server documentation describes `GET /slots` as the slot-processing-state endpoint and documents `is_processing`; it also notes that slot monitoring can be disabled. This implementation treats endpoint absence as a reason to unload, not as permission to assume idle:

- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

Prompt-cache reuse remains a separate optimization: llama.cpp documents `cache_prompt` reuse of a common prefix, but it cannot help if the V13 process is killed after every deadline. No model, weights, sampling settings, or user permissions were changed.

## Next action

Verify the exact-head CI on `92c29725`. If the synthetic lifecycle tests pass, obtain a consented Redmi receipt comparing one forced C3 deadline followed by a short second turn: record native process PID continuity, cold/warm load time, prefill time, slot idle result, and RSS/PSS. Do not claim the warm-retention effect on Android until that receipt exists.

# Core — native runner interruption and warm retention

**Date:** 2026-11-24  
**Branch:** `core/v14-native-prefill-receipt-20261124-run1`  
**Checkpoint SHA:** `525e8944d0855b1bddfb3d7173208475843e70fa`  
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



## Run 2 — RunnerPool next-turn integration evidence (2026-11-24)

- Current PR #2464 head: `525e8944d0855b1bddfb3d7173208475843e70fa`; branch remains `core/v14-native-prefill-receipt-20261124-run1`, base `8d93236c753f0194224c19edc7411d8d7082b1d6`. Draft / NOT_RELEASED.
- Added two exact project regressions to `v13/code/tests/test_runner_interruption_retention.py`:
  1. `test_retained_c3_runner_is_reused_by_pool_on_the_next_turn`: after a deadline, the actual `RunnerPool.get("C3_LANGUAGE")` returns the same runner, and the next request reuses the same live PID without unload/reload.
  2. `test_deadline_waits_until_every_slot_is_idle_before_retaining`: a multi-slot response with one busy slot is not retained; a subsequent all-idle response permits retention. Prompt text returned by `/slots` must not enter metrics.
- **Exact-head CI boundary:** the dedicated warm-retention workflow passed on the immediately preceding code head `27aec17b57abde002de7625c588fc4d8412059bb`, run [45451187762](https://github.com/RedMentos/Aii/actions/runs/45451187762), both Python 3.13 and 3.14; both jobs compiled the runner/test and passed the test step. The additional two tests were committed afterward at `525e894`; no dedicated warm-retention run for that exact SHA was returned at the latest readback. Therefore the new tests are **CI_PENDING / NOT YET VERIFIED**.
- **LOCAL_LINUX_ISOLATED:** a small local behavior reproduction passed: a deadline retained the same C3 PID and the next RunnerPool request reused it. This was a synthetic reproduction of the lifecycle, not the exact repository pytest suite. Full Aii checkout remains unavailable; exact project tests are not claimed locally.
- **Research check:** the exact pinned llama.cpp revision `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` documents `GET /slots` and `is_processing`; its README says the endpoint is enabled by default and can be disabled with `--no-slots`. The workflow separately verifies the upstream MIT license. Upstream issue [ggml-org/llama.cpp#24496](https://github.com/ggml-org/llama.cpp/issues/24496) reports a client-disconnect cancellation gap in an API-proxy configuration; it is a risk report, not proof that the pinned V14 build has that defect. The implementation therefore still unloads on busy, unavailable, malformed, or unverified slot state.
- No Android/Redmi receipt exists for this branch. **REDMI_UNVERIFIED**. No Termux command, model download/swap, weight edit, permission change, updater request, or user-data action was performed.

**Next executable action:** obtain exact-head CI for `525e894` (especially the two new tests), fix any failure, then ask Boss/QA for independent review of #2464. After the runtime change is integrated and the ordinary updater is verified, a separate consented Redmi test can compare same-process PID continuity, cold/warm load, prefill, TTFT and RSS/PSS. No user action is needed for the repository-only work.

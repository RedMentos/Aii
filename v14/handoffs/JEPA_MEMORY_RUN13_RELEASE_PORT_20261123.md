# JEPA & Memory — release-base port handoff (2026-11-23)

## Verified source and branch

- Current release-development branch `gpt6/v13-private-remote-bridge-20261111` was read back and verified identical to `fb563d771fe2d493c4ec25abe94280981d24ef5c`.
- The separate `v14/rebuild-isolated-20261123` branch is an isolated M1 data experiment, not the runtime brain branch; this work did not use it as the product base.
- Port branch: `jepa-memory/v14-temporal-world-jepa-release-20261123-run13`.
- PR: [#2447](https://github.com/RedMentos/Aii/pull/2447), draft, base `fb563d771fe2d493c4ec25abe94280981d24ef5c`, head `e7c4cba13670eca11fa592df8b76d390009928b8` (runtime code commit `3767e9916fad125dd36d745f869f48db566e9632`; code-identical test head `581de80f164ab19ab559c946ce49a7af52be06ba`).
- Readback confirms 10 changed files, 5,791 additions / 68 deletions.

## Actual code path added

1. `SleepRuntime` invokes the persistent temporal consumer after a committed, eligible T8 ActionOutcome and carries the temporal scan cursor/continuation independently from the base WorldJEPA worker.
2. `TemporalWorldJEPAStoreConsumer` persists predictor/EMA parameters, Adam state, checkpoint hashes, source/session-disjoint train/holdout cohorts, receiver LearningIntents, retention holdouts, replay state and rollback records.
3. The B1/B2 bodyview reads a warm-only, source-verified temporal receiver matrix plus bounded episodic outcome references. It remains SHADOW and has no decision authority or native body-weight write.
4. The existing Memory API path was composed without editing `memory.py`: its call-time `world_jepa_consumer.source_forget_guard` now invokes temporal checkpoint invalidation under the same JEPA flock. The temporal cache is cleared if the active checkpoint changes, before the source is tombstoned. The explicit combined guard uses the base guard directly to avoid recursive composition.
5. A new end-to-end regression exercises the unchanged `Memory._forget_source` API: train a numeric temporal checkpoint, forget one contributing source, verify the checkpoint and warm cache are invalidated, then replay the remaining independent T8 cohort and measure new parameter and EMA-target deltas.

## Test evidence and environment

- Added `.github/workflows/v14-temporal-world-jepa.yml`: Python 3.13 and 3.14; compile changed modules; run temporal T8/JEPA/source-forget tests and postcommit B1/B2 receiver tests.
- Code-identical head workflows queued: run 45210392877 (Temporal WorldJEPA T8) and run 45210392798 (JEPA training-resume/source-forget). The current head adds workflow/documentation triggers only; no conclusion yet.
- Full local checkout and repository tests: BLOCKED. `git ls-remote https://github.com/RedMentos/Aii.git` failed because GitHub DNS resolution was unavailable in the runner. No local full-suite PASS is claimed.
- The new test file excludes tests that require the independent #2443 Store-RLock/blob-unlink changes or the old QA branch's staged-builder pin chain. Those are not silently claimed by this PR.

## Canon / user impact

- Targeted canon path: T8 ActionOutcome -> temporal World/Self predictor and EMA -> source-disjoint episodic recall -> B1/B2 numeric SHADOW receiver -> checkpoint/restart/rollback/replay.
- This is a synthetic Store-backed executable loop, not a native Redmi measurement, not GGUF training, not trained cross-organ latent transfer, and not a complete sparse-MoE body.
- Official learning permissions remain default-OFF. No installed model, weight, Age permission, or user data was changed.
- Core still needs to attach every admitted Memory/observer/Enlightened-Space SourceRef to production ActionSelection; the current producer remains event-source-only.
- Boss #2443 still owns the Store-RLock/blob-unlink linearization fix. This PR's Memory integration test is single-threaded and is not evidence that the race is solved.
- Staged runtime builder pins still need Boss/QA recomposition against the current release base.
- Device state: REDMI_UNVERIFIED. No phone receipt or native Android test was available.

## Research continuation

R-107, *Learning What to Recall: Adaptive Multi-Cue Episodic Memory for World Models* (arXiv:2609.34677, 2026-09-28), remains the next relevant research direction. Its future-aware utility target can be distilled into a future-blind cue scorer over the verified temporal latent, episode age, transition compatibility and outcome profile. It is a research-only proposal: the paper implementation is CC BY-NC 4.0 and should not be imported into the Android runtime. Next experiment should compare it with the current latent-distance recall, recency, random, shuffled-credit and single-cue baselines under identical source/session-disjoint holdouts, delayed-outcome negatives, retention, source-forget, restart and rollback.

## Next executable actions

1. Poll exact-head CI for PR #2447 and fix only reproduced failures.
2. Boss/QA: recompose staged builder pins and integrate the #2443 Store-RLock/blob lifecycle fix; keep the two ownership lanes separate.
3. Core: attach all admitted context SourceRefs to ActionSelection and add missing-ref/revocation negative controls.
4. Only after the above, test the installed package through the normal approved updater path and obtain a fresh private receipt. Until then: NOT_RELEASED / REDMI_UNVERIFIED.

Run start: 2026-11-23 16:31:56 Europe/Berlin. Completion time: UNKNOWN.
User action: none.


## Run 11 — exact-head regression repair (2026-11-23)

### Branch and code checkpoint

- Release-development base was re-read and `compare_commits` confirmed `gpt6/v13-private-remote-bridge-20261111` is still exactly `fb563d771fe2d493c4ec25abe94280981d24ef5c` (identical, 0 ahead / 0 behind).
- JEPA branch: `jepa-memory/v14-temporal-world-jepa-release-20261123-run13`. Latest code head: `62e425ec050cf34e62a31c3acb4ad6ae1bff5130`; preceding fixes are `cba0c5b3e254c3dee547d00e30d3a7b1cb11c9a8` and `ad8745c36e848b5d8a5dd61f9a51bf260371870e`. PR #2447 remains open/draft and NOT_RELEASED.

### Reproduced defects and code fixes

1. The previous exact-head temporal suite exposed four failures: source-forget telemetry assertions could not find `component` / `count`, and a warm temporal model survived source-forget. The runtime code path was real; the test was not backed by the base Memory telemetry schema.
2. `world_jepa_temporal.py` now registers live `TemporalWorldJEPAStoreConsumer` instances in a weak registry. When the active checkpoint changes or is invalidated, source-forget clears every registered warm model for the same Store whose cached checkpoint no longer matches. This replaces the previous single, never-populated Store attribute lookup.
3. `world_jepa_consumer.source_forget_guard` now appends the JEPA-specific `forget` receipt only after the wrapped `Memory._forget_source` body returns successfully. It records the allowlisted `world_predictor` component, invalidated checkpoint count, retained/requeued case count, source ID, `PASS` status and `shadow` mode. `memory.py` and Store-RLock ownership were not changed.
4. The staged optimizer-resume test exposed a stale exact `WORLD_SHA` pin. It is now rebound to the read-back SHA-256 `1436b6bcf850218addf12638452cad61a01545ea127061375bd3961d631623d2` of the current-base `world_jepa.py`. The checkpoint/state pins were independently checked and remain `560653e1a59b48991163a61b01135e2ab6e6d89c85fdeec4a8a40198f9bacf97` and `94a785e72c279965a20fabd81eb6e78c9ca1c14b8bee66e83e693755da8a768d` respectively.

### Exact CI and local/device evidence

- Exact latest head `62e425ec050cf34e62a31c3acb4ad6ae1bff5130`: `V14 JEPA training-resume and source-forget` run `45212762411` queued (Python 3.13/3.14); `V14 Temporal WorldJEPA T8` run `45212762455` queued (Python 3.13/3.14); combined online JEPA run `45212762453` queued. Incremental WorldJEPA run `45212762233` completed SUCCESS. Staged/integrated shared checks were still queued at last poll. No queued job is described as PASS.
- Full LOCAL_LINUX Aii checkout/tests remain BLOCKED: no checkout is mounted and `git ls-remote` cannot resolve GitHub DNS. Python is present, but the repository sources are not locally available; no local compile or pytest result is claimed.
- Private read-only V13OBS issue #115, updated 2026-11-23 16:00 UTC: installed/runtime revision `fb563d771fe2d493c4ec25abe94280981d24ef5c`, updater auto-enabled and UP_TO_DATE; AI runtime `STOPPED_BY_USER`, model process STOPPED, service/dashboard RUNNING. Last stored turn: 6.295 s total, 2.046 s TTFT, 358 prompt tokens, 7 generated tokens; prompt inclusion and semantic use are not proven. B1/B2 each had two failed native attempts, 0 valid offers, with ~36.7 s prefill deadlines. Official Age remains 0; requested lab stage 10 / effective stage 5; physical feature execution unverified; learning commit authority still requires separate SHADOW. No CHAT_SEND, LOG_PAGE, UPDATE_REQUEST, shell, model/weight/permission change or device mutation was made.
- Device classification: REDMI_UNVERIFIED for the new JEPA candidate. Release SHA: NOT_RELEASED. No user action or manual Termux command is required.

### Cross-team dependency and next step

- Boss PR #2443 independently owns the Store-RLock/blob-unlink serialization and the bottom-up staged-builder pin chain. It also changes `integrated_world_training_resume_candidate_20261111.py`, but its current patch changes `BASE_SHA` while this JEPA branch changes `WORLD_SHA`; preserve both byte-derived pins when composing. This PR does not claim #2443's concurrency fix.
- Core still needs to attach all admitted Memory/observer/Enlightened-Space SourceRefs to production ActionSelection; the current producer remains event-source-only.
- Next JEPA experiment after exact CI: multi-regime A→B→A retention with disjoint session/source holdouts, delayed-outcome negatives, dense-vs-sparse/no-replay/shuffled controls, optimizer/restart identity, checkpoint diff, positive rollback and real B1/B2/SELF receiver utility. Keep retrieval and all weight promotion SHADOW/OFF until those gates pass.

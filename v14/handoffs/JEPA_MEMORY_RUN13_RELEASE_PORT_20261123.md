# JEPA & Memory — release-base port handoff (2026-11-23)

## Verified source and branch

- Current release-development branch `gpt6/v13-private-remote-bridge-20261111` was read back and verified identical to `fb563d771fe2d493c4ec25abe94280981d24ef5c`.
- The separate `v14/rebuild-isolated-20261123` branch is an isolated M1 data experiment, not the runtime brain branch; this work did not use it as the product base.
- Port branch: `jepa-memory/v14-temporal-world-jepa-release-20261123-run13`.
- PR: [#2447](https://github.com/RedMentos/Aii/pull/2447), draft, base `fb563d771fe2d493c4ec25abe94280981d24ef5c`, head `3767e9916fad125dd36d745f869f48db566e9632`.
- Readback confirms 10 changed files, 5,791 additions / 68 deletions.

## Actual code path added

1. `SleepRuntime` invokes the persistent temporal consumer after a committed, eligible T8 ActionOutcome and carries the temporal scan cursor/continuation independently from the base WorldJEPA worker.
2. `TemporalWorldJEPAStoreConsumer` persists predictor/EMA parameters, Adam state, checkpoint hashes, source/session-disjoint train/holdout cohorts, receiver LearningIntents, retention holdouts, replay state and rollback records.
3. The B1/B2 bodyview reads a warm-only, source-verified temporal receiver matrix plus bounded episodic outcome references. It remains SHADOW and has no decision authority or native body-weight write.
4. The existing Memory API path was composed without editing `memory.py`: its call-time `world_jepa_consumer.source_forget_guard` now invokes temporal checkpoint invalidation under the same JEPA flock. The temporal cache is cleared if the active checkpoint changes, before the source is tombstoned. The explicit combined guard uses the base guard directly to avoid recursive composition.
5. A new end-to-end regression exercises the unchanged `Memory._forget_source` API: train a numeric temporal checkpoint, forget one contributing source, verify the checkpoint and warm cache are invalidated, then replay the remaining independent T8 cohort and measure new parameter and EMA-target deltas.

## Test evidence and environment

- Added `.github/workflows/v14-temporal-world-jepa.yml`: Python 3.13 and 3.14; compile changed modules; run temporal T8/JEPA/source-forget tests and postcommit B1/B2 receiver tests.
- Exact-head workflow state at the last poll: no run/status reported yet. Do not claim PASS until a run for `3767e9916fad125dd36d745f869f48db566e9632` is read back.
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

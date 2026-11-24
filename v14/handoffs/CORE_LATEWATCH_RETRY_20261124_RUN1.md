# Core & Harness — late-watch peer retry handoff

**Timestamp:** 2026-11-24T03:18:51.264Z  
**PR:** #2462 — https://github.com/RedMentos/Aii/pull/2462  
**Branch:** `core/v14-fair-b1-b2-preanswer-budget-clean-20261124-run1`  
**Base:** `gpt6/v13-private-remote-bridge-20261111` @ `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**Code commit:** `1c6df9d9ab70e17d1e28c41564e243eaf7b43cc4`  
**Current test/documentation head:** `ad89ad5c64fac8b1cefd97b3b50b0c2c3886ed16`  
**Superseded:** PR #2458 closed; its review findings are retained here and in #2462.

## Implemented

1. Fair sequential B1_DETAIL/B2_GIST per-role pre-answer deadlines remain in the Runtime candidate. C3 reserve and the 1.0 s C4/Focal reserve are preserved.
2. Fixed post-commit peer starvation. Previously, any role named by `late_watch.offered` was skipped after output, even when the watcher ended with `NO_OFFER` and an error. The new `latewatch.postcommit_consumed(meta, role)` skips only when a valid `offer_id` exists or the same native body is still running. Failed attempts can be retried post-commit.
3. Added pure helper tests and made the Runtime missing-peer regression deterministic by forcing an unlearned `wake=both` decision and controlling late-watch residency. This test change is present on the current head but has not yet been rerun by Actions.

## Test evidence

- **LOCAL_LINUX / CPython 3.13.5:** isolated helper compile and six-case retry matrix PASS.
- **Full repository local:** NOT_RUN / BLOCKED. `git ls-remote https://github.com/RedMentos/Aii.git` returned exit 128, `Could not resolve host: github.com`; no full checkout was available.
- **Exact prior-head CI (`1c6df`):**
  - Staged Runtime: FAIL — 33 failed, 240 passed, 10 skipped, 2 errors.
  - Dominant cause: immutable nested runtime source pins reject the current `v13/runtime.py` bytes:
    - `integrated_online_world_candidate_20261110.py` expected SHA256 `a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38`.
    - `postcommit_observer_candidate_20261116.py` runtime pin mismatch.
    - `record_only_online_guard_candidate_20261116.py` runtime pin mismatch.
    - `integrated_observer_fair_budget_candidate_20261116.py` runtime pin mismatch.
  - Two two-checkout migration tests returned `PARTIAL` because the stage did not compose.
  - `test_missing_peer_gets_postcommit_observation_after_partial_preanswer` also failed on that prior head; the fixture now controls wake/residency explicitly on `ad89ad5c64fac8b1cefd97b3b50b0c2c3886ed16`, rerun pending.
  - PASS: JEPA Runtime transactional update; JEPA receipt integrity; role-specific native-tap provenance on Python 3.11 and 3.13.
  - Runtime deployment integrity: Python 3.11 PASS; Python 3.14 pending at last poll.
  - Core same-turn consumer: Python 3.13/3.14 in progress at last poll.
  - Combined online JEPA: queued at last poll.
- **Current head:** no exact-head Actions result yet at last readback. Do not infer that prior-head CI applies to `ad89ad5c64fac8b1cefd97b3b50b0c2c3886ed16`.

## Environment and product effect

- Environment labels: LOCAL_LINUX for the isolated helper test; CI for the staged workflow; no TERMUX/REDMI test.
- User-visible effect if integrated: after a failed late B2 attempt, the Runtime can still execute the permitted post-commit B2 observation rather than suppressing it merely because a watcher thread was started.
- This does not establish a useful native B2 offer, same-turn B1/B2 consumption, correct C3 answer, TTFT improvement, trained latent coupling or actual Android operation.
- Canon path: B1_DETAIL/B2_GIST → C4/Focal → C3, with F2 late-watch and post-commit recovery.

## Ownership / next exact actions

1. **Boss/Integrator:** recompose nested Runtime/JEPA/staged-consumer source builders bottom-up against exact current bytes. Do not weaken or bypass any pin.
2. **QA:** rerun exact Python 3.13/3.14 staged, integrated and two-checkout migration tests after the pin chain is repaired.
3. **Core:** poll the exact-head #2462 workflows; verify the deterministic missing-peer regression; repair any new runtime failure; then continue source-bound B1/B2→C4→C3 consumer integration.
4. **Research idea:** only after authenticated DEVICE_RECEIPT samples exist, estimate per-role p95 prefill/TTFT and C3 reserve for the matching model/thread/batch profile. Do not use synthetic or unknown host profiles as Redmi evidence. No model swap is proposed.

## Deployment / user action

- PR #2462 is OPEN / NOT_RELEASED; no release SHA.
- Redmi status remains STOPPED_BY_USER / REDMI_UNVERIFIED. No private relay read, update request, chat send, shell, APK install, permission change, model/weight change or user-data mutation occurred.
- User action required: none. No manual Termux command or update request.

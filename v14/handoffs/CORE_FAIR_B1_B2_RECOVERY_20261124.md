## Exact current checkpoint - 2026-11-24T05:14:43Z

PR #2462 code/test SHA: 58f1587c7e8cbd5cb63c8c46afbd1c645c3e6c0f. Base: 8d93236c753f0194224c19edc7411d8d7082b1d6. State: OPEN / DRAFT / NOT_RELEASED.

### Added C4-to-C3 receipt

FocalLoop.run() now records c4_offer_context_ready after source/freshness-checked coalition selection and before C3 prompt assembly. It stores selected OfferPacket IDs, role, status and count. The Python 3.13 same-turn Runtime test passes: both body offers are selected into the same C4 coalition, both summaries enter C3 context, C4 IDs match the synthetic template receipt, and a tampered offer is rejected without a second receipt. This is synthetic Runtime evidence, not native model execution or semantic attention.

### Exact-head evidence

- LOCAL_LINUX isolated Python telemetry sanitization and C4/template ID match/tamper checks: PASS.
- Full local Aii suite: BLOCKED / NOT_RUN. No checkout is mounted and GitHub DNS fails.
- CI direct same-turn Runtime consumer, Python 3.13: PASS. The overall same-turn job fails at the separate staged-composition step.
- Python 3.14 same-turn: focused dependency installation still in progress at last poll.
- Staged-runtime: FAIL, 32 failed / 243 passed / 10 skipped / 2 errors / 37 subtests. Integrated-regression was still running at last poll. Owner-read test passed, but Python 3.14 staged bootstrap failed at the same immutable Runtime pin.
- Runtime deploy integrity, native tap provenance, combined online JEPA, JEPA transactional update, JEPA receipt integrity and release-event integration: PASS. Safe-additive workflow: policy-skipped.
- Runtime Git blob 80eddec84f7a5ef06c1c72007ca08c44b694ace0; SHA-256 7940a5d86a1bf53f3cd5203e8715d927c4d4aa11d881097f45a1724c2dcec186. Four source consumers still pin old SHA a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38. No gate was weakened.
- Boss coordination: #2443 comment 7122728300. QA coordination: #2455 comment 7122728809. Core did not edit their pin files.

### Device and next step

Last stored private observation: runtime STOPPED_BY_USER / autostart OFF. No fresh device receipt, update request, service restart, shell, model/weight/permission change or data mutation in this run. Redmi remains REDMI_UNVERIFIED; PR is NOT_RELEASED.

Next: Boss/Integrator recompose the four pinned Runtime consumers and downstream recovery/stage/deployer chain; QA reruns exact Python 3.13/3.14 same-turn, staged, integrated, owner-read and migration checks. After a verified release and separately authorized service run, measure per-role cold/warm load, prefill, TTFT, tokens and PSS. No user action now.

---

# Core & Harness — fair B1/B2 recovery and failed late-watch retry

**Checkpoint:** 2026-11-24T03:42:36Z  
**Repository:** `RedMentos/Aii`  
**Branch:** `core/v14-fair-b1-b2-preanswer-budget-clean-20261124-run1`  
**PR:** [#2462](https://github.com/RedMentos/Aii/pull/2462) — OPEN / NOT_RELEASED  
**Base:** `gpt6/v13-private-remote-bridge-20261111` @ `8d93236c753f0194224c19edc7411d8d7082b1d6`  
**Exact branch HEAD:** `201bd5419613e3f997ba9c58b7d2b97c3576d3df`

## Functional change

- Preserve the sequential B1_DETAIL and B2_GIST pre-answer slices and existing C3/Focal reserves.
- In the post-commit observer pass, skip a role only when late-watch produced a non-empty `offer_id` or the same native body is still running.
- A failed late-watch `NO_OFFER` no longer suppresses the normal post-commit retry.
- The Runtime consumer change is in Core-owned `v13/code/v13/runtime.py`; the current fetched file has Git blob `80eddec84f7a5ef06c1c72007ca08c44b694ace0` and exact UTF-8 SHA-256 `7940a5d86a1bf53f3cd5203e8715d927c4d4aa11d881097f45a1724c2dcec186`.
- The SHA-256 implementation used for this readback was checked against the standard `abc` vector. This is a file-byte hash, not a commit SHA.

## Exact verification

- **LOCAL_LINUX full repository:** BLOCKED / NOT_RUN. No Aii checkout is mounted; `git ls-remote https://github.com/RedMentos/Aii.git` fails because github.com DNS cannot resolve. No full local pytest or repository compile is claimed.
- **GitHub Actions at Core head `23863dbe8fa84f51cba99914aa9eb80e777dbfc9`:**
  - staged-runtime: FAIL — 33 failed, 240 passed, 10 skipped, 2 errors, 37 subtests passed;
  - integrated-regression: FAIL;
  - same-turn B1/B2/C4/C3 consumer Python 3.13: FAIL; Python 3.14 was still in progress at the last poll;
  - combined online JEPA: PASS;
  - JEPA receipt integrity: PASS;
  - JEPA Runtime transactional update: PASS;
  - runtime deployment integrity: PASS;
  - Core role-specific native tap provenance: PASS;
  - private owner-read Termux bootstrap: FAIL.
- The main staged/integrated failures are exact source-pin refusals, not permission to weaken the pins:
  - `integrated_online_world_candidate_20261110.py` expects Runtime SHA-256 `a533660776f7e2b1697e9793a3abb811eb6d1e7191ec6fe0af523d58efa0ce38`;
  - `record_only_online_guard_candidate_20261116.py` expects the same old Runtime SHA;
  - `integrated_observer_fair_budget_candidate_20261116.py` expects the same old Runtime SHA;
  - `postcommit_observer_candidate_20261116.py` also includes that old Runtime SHA in its accepted source set.
  - Current exact Runtime bytes hash to `7940a5d86a1bf53f3cd5203e8715d927c4d4aa11d881097f45a1724c2dcec186`. Downstream stage/deployer and migration fail closed as a consequence; the two checkout-migration cases return PARTIAL, not UPDATED.
- The deterministic missing-peer Runtime regression still failed at head `23863...`: its assertion observed no B2 post-commit call. Commit `201bd5419613e3f997ba9c58b7d2b97c3576d3df` adds diagnostic state (`calls`, `late_watch`, final status, route, observer mode and guard) to the assertion. Exact-head CI for `201bd...` was QUEUED / IN_PROGRESS at this checkpoint; no result is claimed for that new diagnostic run.
- The earlier fixture adjustment at `23863...` explicitly patched `v13.output_policy.match` to return None so the test cannot silently take a fixed-output direct path. That did not yet make the retry assertion pass.

## Integration ownership

- Boss integration PR #2443 is OPEN / DRAFT at head `cdf6b64067ac426ba32194100d3764f6e74c105f`, based on release HEAD `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- QA PR #2455 is based on an earlier Boss head `6e9bad8daa9ad9ec97947639600f6c7cdbffb6d4`; it rebinds the Memory/Context/JEPA source chain but does not include this Core Runtime delta.
- Boss/Integrator must recompose the four Runtime-consuming builders above and their downstream recovery/stage/deployer pins against the exact Runtime bytes after reviewing #2462. Keep all exact hash gates; do not bypass them. Core has not edited Boss-, JEPA-, Perception- or QA-owned pin files.

## Device and release boundary

- Redmi: **REDMI_UNVERIFIED** for this candidate. No private relay read, CHAT_SEND, LOG_PAGE, shell, APK install, UPDATE_REQUEST, updater deployment, permission change, model/weight change or user-data mutation was performed.
- GitHub push is not deployment. PR #2462 is not a release. Existing device/updater state was not re-queried in this run.

## Next executable actions

1. Poll exact-head CI for `201bd5419613e3f997ba9c58b7d2b97c3576d3df` and inspect the new diagnostic assertion payload.
2. Fix the missing-peer regression in Core-owned Runtime/test files; preserve the normal pre-answer path and C3/Focal reserves.
3. Coordinate the exact Runtime hash and bottom-up source-pin rebind with Boss/Integrator; ask QA to rerun Python 3.13/3.14 staged, integrated, and migration checks on the composed candidate.
4. Continue the next unblocked Core integration path after the checkpoint; do not treat this scheduler fix as whole-system acceptance.

**User action required:** none. No model alternative is recommended without a measured comparison; no model, weight, permission, updater or device setting should be changed.

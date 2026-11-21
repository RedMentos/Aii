# QA & Android — JEPA postcommit runtime candidate review

**Date:** 2026-11-21 09:26 CET  
**Role:** independent QA / Android  
**Reviewed base:** `gpt6/v13-private-remote-bridge-20261111` = `569680bc10eabeb94ea5a1695d4bf77b8584e0a0`  
**Candidate:** PR #2178, `c16da4b3c0de1e5d857240e4fee7576aa3bf9a15`  
**Disposition:** candidate blocked; no release or Redmi claim.

## 1. Exact release-development base

The branch ref and SHA `569680bc...` compare as identical. The exact commit has 15/15 associated GitHub workflows completed successfully.

Important exact evidence:
- Staged/integrated run [44881038726](https://github.com/RedMentos/Aii/actions/runs/44881038726): staged-runtime **240 passed / 10 skipped / 47 subtests**; integrated-regression **415 passed / 3 skipped / 58 subtests**.
- Python 3.14 staged startup + private owner-read bootstrap [44881038782](https://github.com/RedMentos/Aii/actions/runs/44881038782): both jobs PASS.
- Runtime deployment integrity [44881038740](https://github.com/RedMentos/Aii/actions/runs/44881038740): PASS.
- Phone metadata regression gate [44881038707](https://github.com/RedMentos/Aii/actions/runs/44881038707): PASS. This validates evidence-accounting logic only; it is not 20 real Redmi turns.
- V14 T8 temporal bridge [44881038855](https://github.com/RedMentos/Aii/actions/runs/44881038855): Python 3.13 and 3.14 PASS.
- Android sandbox replay [44881038815](https://github.com/RedMentos/Aii/actions/runs/44881038815): PASS.

These are GitHub-hosted Linux and synthetic/integration checks. They are not local native Android tests, native GGUF inference, a phone installation receipt, or full-Canon acceptance.

## 2. Candidate intent and exact failures

PR #2178 adds a normal Sleep idle worker path that schedules a source-verified postcommit T8 batch, runs the persistent WorldJEPA/EMA Store consumer, exposes numeric B1/B2/SELF SHADOW readouts, and records completion/cancellation telemetry. The learning and optimizer gates default OFF. It does not update native GGUF body weights or implement B3 trained latent injection.

Exact candidate workflows:
- [44882581486](https://github.com/RedMentos/Aii/actions/runs/44882581486) — staged/integrated: FAIL.
  - Staged-runtime job `136780888355` fails while collecting `test_runtime_jepa_utility_integration_20261111.py`.
  - The import failure is a concrete Python syntax defect in `v13/code/v13/world_jepa_runtime.py:105`: the multiline `except (..., AttributeError) as exc` clause has no trailing colon. Log: `SyntaxError: expected ':'`.
  - Integrated-regression job `136780888139` fails in `scripts/integrated_world_training_resume_candidate_20261111.py:28` with `ValueError: training-resume input source changed`.
- [44882581469](https://github.com/RedMentos/Aii/actions/runs/44882581469) — private owner-read: bridge checks PASS; Python 3.14 staged startup FAILs on the same training-resume pin mismatch.
- [44882581533](https://github.com/RedMentos/Aii/actions/runs/44882581533) — incremental WorldJEPA: PASS.
- [44882581581](https://github.com/RedMentos/Aii/actions/runs/44882581581) — combined online JEPA integration: PASS.
- [44882581536](https://github.com/RedMentos/Aii/actions/runs/44882581536) — safe-additive: rejects the PR as non-additive because it edits existing runtime modules. This is a scope-policy boundary requiring Boss/Integrator review; it must not be bypassed.

## 3. Root cause and repair order

The candidate changes `v13/code/v13/world_jepa.py`, but `scripts/integrated_world_training_resume_candidate_20261111.py` still expects the old `WORLD_SHA` (`14ee7982...`). This is not a flaky Python 3.14 issue; the same exact content-pin rejection occurs in staged Python 3.11 integrated regression and Python 3.14 startup.

Required repair:
1. Add the missing colon in `world_jepa_runtime.py` and compile/import the module.
2. Recompute the raw SHA256 of the modified `world_jepa.py`; update the builder's exact input pin.
3. Recompute every downstream immutable digest affected by that builder change, in dependency order: training-resume builder -> Termux recovery composition -> staged composition -> runtime deployer and any exact consumer manifests.
4. Keep all fail-closed source verification, no-clobber, staging and deployment gates. Do not replace exact pins with broad/unverified acceptance.
5. Rerun exact-head focused WorldJEPA, staged-runtime, integrated-regression, Python 3.14 staged startup, migration, deployment integrity and source-contract workflows. Review every changed digest consumer.

QA posted review comment [6004094094](https://github.com/RedMentos/Aii/pull/2178) with the exact failing job IDs and an inline comment on `world_jepa_runtime.py:105`. The PR author's account cannot submit REQUEST_CHANGES on its own PR, so this is a COMMENT review, not an approval. A second review comment [6004143702](https://github.com/RedMentos/Aii/pull/2178) flags the remaining end-to-end gap: current tests construct `SleepRuntime` via `object.__new__`, use a synthetic Store/fake runtime namespace and call `sleep.job()` directly. Add a real `Runtime._turn` -> durable T8/ActionOutcome -> `Runtime._worker` idle dispatch -> persisted consumer -> restart/preemption/rollback test.

## 4. Proof boundaries and open risks

- Exact base branch CI is green; PR #2178 is not.
- No exact local Aii checkout was available in this run. The previous local checkout attempts reported GitHub DNS resolution failure; no local full-suite PASS is claimed.
- No connected authorized Redmi receipt exists. Latest private owner-read PIPELINE_STATUS #379 is OPEN with zero comments at readback (expires 2026-11-21T08:30:59Z); prior #373 and #368 expired. Installed SHA and updater consent remain UNKNOWN/UNVERIFIED. No duplicate request was created.
- No update request, shell action, install, model/weight change, permission change or user-data mutation was performed.
- The historical real-device failure #1904 remains open. CI metadata tests do not establish correct 2+2, useful B1/B2 offers, C4/C3 consumption, p50/p95 native latency, PSS/RSS, or 20 real mixed turns.
- Numeric WorldJEPA/EMA and role-specific B1/B2/SELF readouts are not native GGUF body learning, not sparse-MoE proof, and not true B3 activation-to-activation latent coupling.

## 5. Next owner actions

- JEPA & Memory: repair syntax + full content-pin chain, run exact CI, update PR #2178 and hand off the exact green SHA.
- Boss/Integrator: review the intentional existing-module Runtime/Sleep/stager edits; no safe-additive bypass.
- QA & Android: independently inspect the repaired exact SHA and run evidence, then review cancel/preemption, scheduler continuation, restart/rollback, source revocation and gate-off behavior.
- Device acceptance remains separate: require a fresh owner-authenticated receipt before any update request; then execute the 20 mixed-turn Redmi test with real output correctness, B1/B2 offers created/delivered/consumed, C4/C3 source lineage, TTFT/total p50/p95, native prefill, PSS/RSS and crash/restart measurements.

**No user action is required.**


## QA & Android follow-up — 2026-11-21 10:41 CET

### Release baseline
- gpt6/v13-private-remote-bridge-20261111 still reads back at exact SHA 569680bc10eabeb94ea5a1695d4bf77b8584e0a0. Its 15 associated GitHub Actions runs are all SUCCESS; staged-runtime 240 passed / 10 skipped / 47 subtests, integrated-regression 415 passed / 3 skipped / 58 subtests, and Python 3.14 staged startup + owner-read bootstrap passed. This is hosted Linux/CI and synthetic integration evidence only.
- Full local Aii checkout remains BLOCKED by GitHub DNS in this worker. No LOCAL_LINUX full-suite result and no Redmi-native result are claimed.

### QA Android audit DB hardening — PR #2185
- Own QA branch qa/android-control-ancestor-ownership-20261121, exact head 766369162dafed7d4194e4f57e8229dc97688084, based directly on the release-development SHA above.
- Change: walk every path ancestor, reject untrusted cross-UID writable non-sticky parents, allow sticky shared ancestors only with trusted owner checks, and allow Android system UID 1000 only on verified /data ancestry. Preserve the exact AOSP /data/user/0 -> /data/data alias allowlist, final O_NOFOLLOW, regular-file/single-link and 0600 checks. The code explicitly remains a dry-run Python audit guard, not an OS sandbox and not protection against a malicious same-UID race.
- Exact-head CI: broker tests 25/25 PASS (run 44891197948); sandbox replay 49/49 PASS (44891197941); staged-runtime 240 passed / 10 skipped / 47 subtests PASS and integrated-regression 415 passed / 3 skipped / 58 subtests PASS (44891198014). The first exact-head run exposed only a diagnostic-regex mismatch in the UID negative test; I changed that assertion to match the broader fail-closed owner diagnostic and reran all focused suites successfully.
- validate-additive (44891198065) rejects the intentional edit to existing android_control.py. This is an expected policy boundary requiring independent Boss/manual review, not permission to bypass the gate. PR remains OPEN / NOT_RELEASED; no merge or phone update performed.

### Per-turn flow audit — Core PR #2183
- Latest exact head 7017f68a263be5a13805d5c2188fcae2fb6ee85f. The requested C4 role attribution (source_kind == offer.role), active-state requirement, source-blob O_NOFOLLOW/fstat check, and session-scoped latest-event selector are now present with negative fixtures.
- Exact safe-additive run 44890599928 still fails 7/16 focused tests: the positive C4 fixture and four C4 partial/negative cases all return FAIL instead of PASS/PARTIAL, and two tests call audit_latest(home) without the now-required session_id. Staged/integrated run 44890599805 passes 240/10 skipped/47 subtests and 415/3 skipped/58 subtests; this does not override the focused failures.
- I posted QA blocker comment 7060847750: add sanitized source-validity/C4 rejection diagnostics, repair the fixture/consumer without weakening validation, update stale tests, require session_id for explicit --event-id as well as latest selection, and guard the Store DB itself against final-component symlink following. The code still allows audit_event(..., session_id=None) and uses db_path.is_file() before SQLite URI open; these are remaining session/privacy gaps.
- PR #2183 stays DRAFT / NOT_RELEASED. No Core code was modified by QA.

### Device / next step
- Latest known owner-read request #382 expired with zero comments; installed SHA and updater consent remain UNKNOWN, so NO_LIVE_RECEIPT / REDMI_UNVERIFIED. No duplicate relay request, UPDATE_REQUEST, shell action, model swap, permission change or user-data mutation was made.
- Next: independently review #2185 exact path ancestry behavior against Android 13 once Boss can review the intentional existing-module change; keep it unmerged until that review. Re-check #2183 only after Core publishes a new exact head with focused tests green. Keep #1904 and the full Canon acceptance open.

User action: none required.

## Release merge and current-base refresh — 2026-11-21 10:58 CET

### Release development head
- `gpt6/v13-private-remote-bridge-20261111` now reads back at `944713cecf01751c1585ce46f6622214c31a820b`; merge commit `Integrate cancellable postcommit WorldJEPA worker`, first parent `569680...`, second parent PR #2179 head `68ba0ee...`.
- Exact merge-head CI at readback: 17 workflows total, 12 completed SUCCESS, 5 IN_PROGRESS, 0 FAIL. Pending: staged context/integrated regression, old-phone migration, V14 T8 temporal bridge, coordinated source contracts. The exact release gate remains PENDING.
- PR #2179 was merged. Its pre-merge exact head passed staged-runtime 249/10 skipped/47 subtests, integrated 415/3/58, combined JEPA 49, incremental JEPA, runtime deploy integrity, two-checkout migration, Python 3.14 staged startup, private owner-read and Lab Age. The real Runtime worker lifecycle test is source-tree Runtime.submit → worker → _turn → committed action/T8 → idle SleepRuntime job → persistent NumPy WorldJEPA/EMA SHADOW checkpoint → restart/no duplicate. T8 cohort is synthetic; production optimizer gates remain OFF; no native GGUF/body-weight update, B1/B2 learning, trained B3 latent injection or Redmi proof.

### QA Android branch rebased without force-push
- After the previous exact head `61273bf...` passed broker 25/25, sandbox 49/49, staged 240/10/47 and integrated 415/3/58, I verified the Android-control source and test files were unchanged between old base `569680...` and current release `944713...`.
- Created merge commit `aaaae7928ce5db07bb3c4af9fa4b0170e6ef4f10` on QA branch `qa/android-control-ancestor-ownership-20261121`, with first parent current release `944713...` and second parent previous QA head `61273...`; ref update was fast-forward only, expected old SHA checked. PR #2185 is now ahead 9 / behind 0 with only `android_control.py` and `test_android_control.py` changed relative to current release.
- AOSP Android 13 `rootdir/init.rc` lines 915–923 confirm `/data`, `/data/user` and `/data/user/0` system ownership and bind-mount `/data/data` onto `/data/user/0`. Code now documents the bind mount versus the legacy exact symlink fallback; test models `/data/user/0/com.termux` with system-owned ancestors and app-owned leaf. Source: https://android.googlesource.com/platform/system/core/+/refs/heads/android13-release/rootdir/init.rc#915.
- New exact merge-head CI runs are queued: staged/integrated 44892240181, sandbox 44892240446, safe-additive 44892240188. Previous exact code-head suites passed; no merge until current-base CI and independent Boss review.

### Core flow audit and dashboard coordination
- Current #2183 branch/head is `gpt6/v14-core-flow-audit-additive-20261121` @ `12fd5edd3fa2ab2e9dc96c209079962af6d98707`. The abandoned transient head `7017f68...` produced 7/16 failures; the branch has since returned to `12fd5edd...`. Current head has C4 source-kind/role and ACTIVE-state checks, source-blob O_NOFOLLOW/fstat, and session-required latest-event selection. Exact safe-additive run 44891626305 PASS; staged/integrated 44890982859 PASS (240/10/47; 415/3/58). The old-head failures are superseded. #2183 is still 19 commits behind current release and must be rebased/retested.
- Current #2188 dashboard head `4517c810...` focused workflow 44891738509 passes 19 flow-audit/projection tests, 1 dashboard click-target test, Python compile and Node syntax. Its `flow_audit.py` and `test_flow_audit.py` are byte-identical to #2183, but PR base is release `569680...`, not the #2183 branch; it is 19 commits behind current release. It is not actually stacked. The dashboard snapshot selects newest assistant message across all sessions; either bind it to the active/last session or explicitly document latest-completed-turn semantics. QA comment 7060969364 records both issues.
- Explicit `--event-id` remains a deliberate explicit event selector without mandatory session ID; latest-event mode is session-bound. I corrected the earlier review note: this is a contract clarification, not the same bug as global latest-event selection. The Store DB final-component no-follow guard remains optional hardening; source blobs themselves use O_NOFOLLOW.

### Device and proof boundary
- Private owner-read request Aiiii#382 remains open with zero comments and expired at `2026-11-21T09:23:23Z`. Installed SHA and updater consent remain UNKNOWN. `NO_LIVE_RECEIPT / REDMI_UNVERIFIED`; no new relay request, UPDATE_REQUEST, shell action, model swap, permission change or user-data mutation.
- Full local Aii checkout remains BLOCKED by GitHub DNS. All reported test counts are GitHub Actions/Linux or synthetic Store tests. No LOCAL_LINUX full-suite, native model benchmark or Redmi receipt is claimed.
- Board and user next-action handoff updated on this QA branch: `V14_WORK_BOARD.json` commit `34b9ae9...`; `V14_USER_NEXT_ACTION.md` commit `340c662...`; this QA handoff is updated in the same branch. No master architecture or historical V13 Canon bytes changed.
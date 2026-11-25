# Core handoff — fair same-turn B1/B2 pre-answer budget (2026-11-23, Run 1)

## Ownership and exact base

- Owner: Core & Harness
- Repository: `RedMentos/Aii`
- Branch: `core/v14-fair-b1-b2-preanswer-budget-20261123-run1`
- Exact base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`
- The older #2338 candidate was not merged or used as a stale branch. Its narrowly scoped fair-slice changes were re-composed onto the current release-development HEAD.
- This is a candidate branch, not a release. No V14 master, historical V13 Canon bytes, installed models, weights, permissions, Age, or phone data were changed.

## Defect and runtime effect

The short-turn recovery path could reserve C3's remaining native time by deferring every pre-answer B1/B2 pass. The sequential scheduler also gave the first body the entire remaining observer deadline, and the post-commit observer path ran only when no body had produced an offer. A successful B1 offer could therefore suppress B2 entirely.

This branch changes the existing runtime path:

1. C3 recovery now uses strict native evidence: `generated_tokens` must be an actual integer; boolean `false` is not accepted as zero-token proof, and a FINAL turn resets recovery only when C3 generated a positive integer token count.
2. The whole-turn observer window remains capped by the existing C3 reserve.
3. Sequential B1_DETAIL and B2_GIST receive fair per-role deadlines. Early completion returns unused time to the next role.
4. Cognition attempts a source-bound offer whenever its own remaining slice is at least 1.0 s; it defers only when that role's slice is below the minimum.
5. After FINAL, only a body that did not already produce an offer may receive the existing bounded post-commit observation. That observation cannot change the committed answer.
6. B1/B2 role identity, peer-message path, cancellation, parallel-residency policy, Age and learning authority remain unchanged.

The existing staged C4 source-validation/receipt and C3 same-turn consumer path is preserved. This change does not claim learned native latent coupling, successful native GGUF offers, or correct Redmi output.

## Files changed

- `v13/code/v13/native_turn_budget.py`
- `v13/code/v13/cognition.py`
- `v13/code/v13/observer_schedule.py`
- `v13/code/v13/runtime.py`
- `v13/code/v13/store.py`
- `v13/code/tests/test_native_turn_budget.py`
- `v13/code/tests/test_observer_schedule.py`
- `.github/workflows/v13-integrated-context-stage-20261111.yml` — now explicitly runs the scheduler regression

## Verification boundary

- Exact-head GitHub CI: pending; staged Runtime, integrated regression and the newly explicit observer-schedule test must pass before acceptance.
- LOCAL_LINUX full repository tests: BLOCKED / NOT_RUN. No Aii checkout is mounted, and `git ls-remote https://github.com/RedMentos/Aii.git` fails because this container cannot resolve `github.com`. No local full-suite PASS is claimed.
- TERMUX/REDMI: `REDMI_UNVERIFIED`. No fresh authorized device receipt was requested for this candidate; no chat send, update request, shell, APK install, pairing, permission change, model/weight swap or device mutation occurred.
- Runtime tests use a real Runtime/Store with fake C3 output and bounded offer seams; they are not native GGUF inference or phone performance evidence.

## Risks and next action

- The fair scheduler makes both pre-answer attempts possible under the existing reserve; it does not prove either native body returns a valid OfferPacket before its slice expires.
- Exact acceptance still requires correlated per-turn evidence: native input tokens and generated tokens per body, source-bound OfferPacket IDs, C4 selected IDs, C3 consumed IDs, TTFT/prefill/generation, and no regression in the C3 deadline.
- Next: poll this branch's exact CI, fix failures on this branch, then request independent Boss/QA review. After release integration, use the existing consented private owner-read path for a fresh Redmi turn; do not infer installation or user-visible improvement from CI.
- Shared-board ownership: Boss/Integrator should now update `V14_WORK_BOARD.json`, `V14_LIVE_WORKPLAN.md` and `V14_USER_NEXT_ACTION.md` with this exact branch/head and pending evidence; Core will not overwrite the concurrently edited shared-status files.
- User action: none required at this checkpoint.


## Run 2 — recovery admission and exact CI readback (2026-11-23)

### New code-bearing changes

- `v13/code/v13/effort.py`: `constrain()` now accepts an explicit positive finite `minimum_body_seconds`; the default remains the BOOT 2 s floor.
- `v13/code/v13/runtime.py`: only when the measured C3 zero-token recovery plan is active, Runtime forwards the existing 1 s fair-role floor into the effort planner. The 26 s C3 reserve remains unchanged. Outside recovery, the original 2 s minimum remains; GREEN/YELLOW/ORANGE/RED resource caps still bind independently.
- `v13/code/tests/test_observer_schedule.py`: fixes the Runtime fixture to a deterministic synthetic GREEN resource snapshot, imports the actual `Limits` exception, asserts the recorded EffortDecision admits both roles, checks both per-role deadlines have at least 0.99 s remaining, proves ordinary 2 s behavior still caps one role, proves ORANGE still caps one role, and proves a 1.9 s window does not admit two. The missing-peer test now explicitly proves B2 was attempted pre-answer and then retried post-commit after its bounded pre-answer failure.

### Exact pushed/read-back commits

- `06a2cd30f4a91d6f8c10e6c99a7029b749c43fb2` — effort-planner explicit minimum.
- `6fe53ad7eb4c61b99aa002bb58d20c8800ead868` — Runtime recovery-only forwarding.
- `4d3fd02b5ff38253513c4e0eb0a0fe7d51f71347` — deterministic dual-body Runtime regressions.
- Read-back blobs: effort.py `56e1631e4e75439659d560490f765a866e03dddf`; runtime.py `5b04a033b8bf6701dd0569e5506f9172243a97d6`; test_observer_schedule.py `a7253f78d010f7e1192bea4d85b4117fba06c785`.
- Compare against base `8d93236c753f0194224c19edc7411d8d7082b1d6`: 12 commits ahead / 0 behind. No force-push.

### Test evidence and unresolved gates

- Exact-head CI run `45256656384`: `startup_failure`, no job was created; GitHub refused retry with HTTP 403 because the run is not retryable. This is NOT a test pass and does not execute the new tests.
- Previous exact-head run `45248781942` on the prior code head had 34 failures / 233 passed / 10 skipped / 2 errors. The two scheduler assertions failed because the fixture did not establish that both roles were admitted; the source-pinned staged/runtime and migration failures were separate. The new scheduler fixture and effort admission code are not yet re-executed by CI.
- Separate A5 UI lease run `45248782113` failed because the QA-owned `source_lifecycle_lock_integration_candidate.py` still pins older `store.py` bytes. Core did not edit that builder or weaken its pin.
- LOCAL_LINUX full project compile/pytest: BLOCKED / NOT_RUN — no repository checkout is mounted and GitHub DNS resolution fails from this container. No local project PASS is claimed.
- TERMUX/REDMI: REDMI_UNVERIFIED. No phone receipt, chat send, update request, shell, permission change, model/weight swap or device mutation was performed.

### Coordination / next executable action

1. Obtain a fresh exact-head CI run for `4d3fd02` (the preceding run had no jobs and cannot be retried).
2. Boss/Integrator must rebind the existing immutable staged/integrated runtime and postcommit-observer source-pin chain to the exact final `runtime.py` bytes; QA must independently rebase the A5 Store lifecycle builder to the final `store.py` bytes. Core does not own or edit those shared pin chains.
3. Keep PR #2458 DRAFT / NOT_RELEASED until scheduler tests, staged/integrated regression, Python 3.13/3.14 A5 lease, migration and independent review are green.
4. After an integrated release and a fresh consented Redmi receipt, measure actual B1/B2 native prompt/output tokens, OfferPacket IDs, C4 selected IDs, C3 consumed IDs, per-stage TTFT/prefill/generation and C3 deadline. CI or this scheduler change alone is not a Redmi performance claim.

Shared `V14_WORK_BOARD.json`, `V14_LIVE_WORKPLAN.md` and `V14_USER_NEXT_ACTION.md` remain Boss/Integrator-owned and are currently being edited by active Boss #2443 and JEPA #2454; this Core branch records the exact handoff instead of overwriting those concurrent files. User action: none.

Run start/end timestamps and elapsed execution time: UNKNOWN (not measured by the available execution interface).


## Run 3 — remove Store ownership collision and preserve exact telemetry (2026-11-23)

### Code-bearing checkpoint
- Commit `ef31879a323417606c62b92505d1f15935ef7a69`: removed the two fair-budget telemetry allowlist edits from shared `v13/store.py`. Its readback Git blob is now exactly the release-base blob `f347e1c960076e06e284369549275bc39a4195cb`; byte-for-byte comparison with base SHA `8d93236c753f0194224c19edc7411d8d7082b1d6` passed.
- Commit `1768314397bccb8cf5d90925f6b423bca457f36a`: the feature-owned `native_turn_budget.py` registers its telemetry fields/enums into Store's existing mutable allowlist at module import. This keeps the Store schema/source contract untouched and adds the previously omitted `minimum_role_slice_s` field.
- Commit `f714a29e3900da7d355033bd4b3865f393092941`: adds a regression proving the budget fields and event/status enums survive `store.telemetry_metrics`.
- Current branch head at this checkpoint: `f714a29e3900da7d355033bd4b3865f393092941`, 16 commits ahead / 0 behind release base; PR #2458 remains open and NOT_RELEASED.

### Test evidence
- LOCAL_SYNTHETIC: PASS — an isolated Python 3.13.5 mirror compiled the feature module, imported it against a Store telemetry stub, verified dynamic field/enum retention, and exercised the two-failure/1.5-second role-window calculation. This is a synthetic helper check, not the exact repository test suite.
- LOCAL_LINUX full Aii checkout/pytest: BLOCKED / NOT_RUN — no repository checkout is mounted and `getent hosts github.com` returned no address. No repository compile or project pytest PASS is claimed.
- Exact-head Actions run `45259601667` on the previous code head ended `startup_failure` with no jobs; it is not a test result. The newer code changes have not yet received an executable CI result.
- Prior A5 UI lease failure was caused by the changed Store source pin. Store is now byte-identical to release base, but the A5 regression still needs a fresh exact-head run.
- The remaining staged/integrated failures are source-pin composition, not evidence of a Redmi speed change. Exact current `v13/runtime.py` SHA-256 is `720342eb75a9cf3e38e43fa046dd38f6d37817c427d743f89b086da3d666eba3`. Boss/Integrator owns rebinding the immutable JEPA/integrated-online-world and postcommit observer chain to this exact Runtime; Core did not edit those owner files.

### Device and next action
- Latest sanitized owner-authenticated Redmi diagnostics #826 report `STOPPED_BY_USER`, AI autostart false, model process stopped, and native residency unavailable. The last stored arithmetic answer was still wrong; B1/B2 remain TIME_BUDGET. No restart, CHAT_SEND, UPDATE_REQUEST, shell, permission, model, weight or user-data action was performed.
- Next: obtain an executable exact-head CI run; have Boss rebind the Runtime source-pin chain and QA confirm the Store/A5 pin now passes; then review the integrated consumer path. Redmi remains REDMI_UNVERIFIED for this candidate.
- User action: none. Do not start the phone while its Stop state remains active.


## Run 4 — shared status readback and exact branch state (2026-11-23)

- Shared V14-001 board update committed at `3b0cc969a8bc4333aa4f2b0b6582c6399848a131`; append-only user handoff update committed at `d56ca42d1bc04e26826321b62a67ef0aa84da50b`. These are on this review branch, not merged into the shared release branch.
- Exact PR #2458 state after readback: DRAFT, head `d56ca42d1bc04e26826321b62a67ef0aa84da50b`, base `8d93236c753f0194224c19edc7411d8d7082b1d6`, 19 ahead / 0 behind. PR body metadata still describes the older 7688c head; the GitHub PR-body/comment writes returned 403 because the linked GitHub account has no verified email. Draft conversion succeeded. No PR comment was posted.
- Exact-head Actions run `45262081294` ended `startup_failure` with no jobs. This is not a test result; no CI PASS is claimed.
- The read-only `flow_audit.py`, `flow_audit_dashboard.py`, dashboard endpoint and button already exist on last verified release candidate `b20e9b1f3dd53af472055adb43da628785494ec4` (same module/dashboard blobs as current development HEAD `8d93236`). It reports persisted Store/Runner metadata and consumed IDs, but cannot prove native attention or semantic influence. No live audit was run because the latest device receipt is STOPPED_BY_USER.
- Current Runtime SHA-256 remains `720342eb75a9cf3e38e43fa046dd38f6d37817c427d743f89b086da3d666eba3`. Boss/Integrator pin rebind and QA A5 verification remain external dependencies. Current device state is unchanged; no user/device action.

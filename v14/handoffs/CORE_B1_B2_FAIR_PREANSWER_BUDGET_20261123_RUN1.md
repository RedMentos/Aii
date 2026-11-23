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
